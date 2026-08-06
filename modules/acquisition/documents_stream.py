"""
CLI entry point for Module 1: Document Acquisition & Ingestion Engine.
Supports --mode continuous (real-time polling) and --mode backfill (historical date range).
Enforces explicit pre-initialization of MongoDB indices and Kafka topics.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from confluent_kafka.admin import AdminClient, NewTopic

# Local imports
from modules.acquisition.config import config
from modules.acquisition.connectors.fireant import FireAntConnector
from modules.acquisition.models.document import Document, RawDocument
from modules.acquisition.preprocessing.documents_preprocessing import (
    DocumentCleaner,
    DocumentDeduplicator,
    DocumentValidator,
)
from modules.acquisition.publishers.kafka_publisher import KafkaPublisher
from modules.acquisition.repository.mongodb import MongoRepository
from modules.acquisition.services.documents_service import AcquisitionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("module1_documents_stream")


def bootstrap_infrastructure(
    raw_repo: MongoRepository[RawDocument],
    doc_repo: MongoRepository[Document],
    kafka_broker: str,
    topic_name: str,
    num_partitions: int = 3,
    replication_factor: int = 1,
) -> None:
    """Pre-initializes database indices and Kafka topics before starting any scraping loops."""
    logger.info("🛠️ Bootstrapping Module 1 infrastructure layers...")

    try:
        # ✨ Fixed: Add sparse=True so null/missing fingerprints don't throw duplicate key errors
        raw_repo.collection.create_index(
            [("fingerprint", 1)],
            unique=True,
            sparse=True,
            name="idx_unique_raw_fingerprint",
        )
        doc_repo.collection.create_index(
            [("fingerprint", 1)],
            unique=True,
            sparse=True,
            name="idx_unique_doc_fingerprint",
        )
        doc_repo.collection.create_index(
            [("document_type", 1), ("published_at", -1)], name="idx_type_published"
        )
        logger.info(
            "✅ MongoDB indices verified on 'raw_documents' and 'documents' collections."
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"⚠️ Notice during MongoDB index verification: {e!s}")

    # 2. Pre-create Kafka topic using AdminClient
    try:
        admin_client = AdminClient({"bootstrap.servers": kafka_broker})
        existing_topics = admin_client.list_topics(timeout=5.0).topics

        if topic_name not in existing_topics:
            logger.info(
                f"Topic '{topic_name}' not found. Pre-creating with {num_partitions} partitions..."
            )
            new_topic = NewTopic(
                topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
            )
            futures = admin_client.create_topics([new_topic])
            for topic, future in futures.items():
                try:
                    future.result()
                    logger.info(f"✅ Kafka topic '{topic}' successfully created.")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"❌ Failed to create topic '{topic}': {e!s}")
        else:
            logger.info(f"✅ Kafka topic '{topic_name}' already exists.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"⚠️ Could not verify Kafka topics via AdminClient: {e!s}")


def parse_datetime(date_str: str) -> datetime:
    """Parses ISO string or YYYY-MM-DD into a UTC datetime object."""
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Invalid date format: '{date_str}'. Use ISO format (e.g., 2026-01-01T00:00:00Z) or YYYY-MM-DD."
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Module 1: Document Acquisition & Ingestion Engine"
    )
    parser.add_argument(
        "--mode",
        choices=["continuous", "backfill"],
        default="continuous",
        help="Execution mode: 'continuous' for polling, 'backfill' for historical date range",
    )
    parser.add_argument(
        "--start-date",
        type=parse_datetime,
        help="Start date for backfill mode (YYYY-MM-DD or ISO string)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_datetime,
        help="End date for backfill mode (default: current UTC time)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Polling interval in seconds for continuous mode (default: 300s)",
    )
    parser.add_argument(
        "--mongo-uri", default=config.mongo_uri, help="MongoDB connection string"
    )
    parser.add_argument(
        "--kafka-broker",
        default=config.kafka_broker,
        help="Kafka bootstrap servers endpoint",
    )
    parser.add_argument(
        "--kafka-topic",
        default="financial-news",
        help="Kafka target topic for processed document stream",
    )
    parser.add_argument(
        "--fireant-token",
        default=config.fire_ant_bearer,
        help="Fireant API Bearer Token",
    )

    args = parser.parse_args()

    if args.mode == "backfill" and not args.start_date:
        logger.error("❌ '--start-date' is required when running in backfill mode!")
        sys.exit(1)

    end_date = args.end_date or datetime.now(timezone.utc)

    logger.info("=================================================")
    logger.info(" 🚀 Financial AI Platform - Acquisition Engine   ")
    logger.info("=================================================")

    # 1. Instantiate Repositories & Publishers
    raw_repo = MongoRepository[RawDocument](
        uri=args.mongo_uri,
        database="financial_ai",
        collection="raw_documents",
        model_class=RawDocument,
    )
    doc_repo = MongoRepository[Document](
        uri=args.mongo_uri,
        database="financial_ai",
        collection="documents",
        model_class=Document,
    )
    publisher = KafkaPublisher[Document](
        bootstrap_servers=args.kafka_broker, client_id="acquisition-publisher"
    )

    # 2. Bootstrap Infrastructure BEFORE starting pipelines
    bootstrap_infrastructure(
        raw_repo=raw_repo,
        doc_repo=doc_repo,
        kafka_broker=args.kafka_broker,
        topic_name=args.kafka_topic,
    )

    # 3. Instantiate Preprocessors and Service
    connector = FireAntConnector(bearer_token=args.fireant_token)
    service = AcquisitionService(
        connector=connector,
        raw_repository=raw_repo,
        document_repository=doc_repo,
        cleaner=DocumentCleaner(),
        validator=DocumentValidator(),
        deduplicator=DocumentDeduplicator(),
        publisher=publisher,
        kafka_topic=args.kafka_topic,
    )

    # 4. Execute Pipeline
    try:
        if args.mode == "continuous":
            logger.info(f"🔄 Starting Continuous Mode (Interval: {args.interval}s)...")
            service.run_continuous(interval_seconds=args.interval)
        else:
            logger.info(
                f"⏳ Starting Backfill Mode ({args.start_date} -> {end_date})..."
            )
            report = service.run_backfill(start_date=args.start_date, end_date=end_date)
            logger.info(
                f"🎉 Backfill Completed | Fetched: {report.fetched} | Stored: {report.stored} | "
                f"Streamed to Kafka: {report.published} | Duration: {report.duration:.2f}s"
            )
    except KeyboardInterrupt:
        logger.info("🛑 Process interrupted by user.")
    finally:
        logger.info("Cleaning up database and Kafka connections...")
        raw_repo.close()
        doc_repo.close()
        publisher.close()
        logger.info("✅ Acquisition Module shutdown complete.")


if __name__ == "__main__":
    main()

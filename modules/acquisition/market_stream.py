"""
CLI Entry Point for Module 1: Vietnamese Market Data Acquisition Stream.
Supports historical OHLCV backfill and continuous real-time market polling.
Enforces explicit pre-initialization of databases, indexes, and Kafka topics.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from confluent_kafka.admin import AdminClient, NewTopic

from modules.acquisition.config import config
from modules.acquisition.connectors.vnstock_connector import (
    DEFAULT_WATCHLIST,
    VnstockConnector,
)
from modules.acquisition.models.market import MarketQuote
from modules.acquisition.publishers.kafka_publisher import KafkaPublisher
from modules.acquisition.repository.mongodb import MongoRepository
from modules.acquisition.services.market_service import MarketAcquisitionService

# Configure structured console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("module1_market_stream")


def bootstrap_infrastructure(
    mongo_repo: MongoRepository[MarketQuote],
    kafka_broker: str,
    topic_name: str,
    num_partitions: int = 3,
    replication_factor: int = 1,
) -> None:
    """
    Explicitly pre-initializes databases, indexes, and Kafka topics before starting any loops.
    Prevents race conditions and default-partition anti-patterns during first publishes.
    """
    logger.info("🛠️ Bootstrapping infrastructure layers...")

    # 1. Ensure MongoDB unique compound index on (symbol, timestamp) to guarantee deduplication at DB level
    try:
        mongo_repo.collection.create_index(
            [("symbol", 1), ("timestamp", -1)],
            unique=True,
            name="idx_unique_symbol_timestamp",
        )
        logger.info(
            f"✅ MongoDB compound index 'idx_unique_symbol_timestamp' verified on '{mongo_repo.collection.name}'."
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"⚠️ Notice during MongoDB index creation: {e!s}")

    # 2. Pre-create Kafka topic using AdminClient if it does not already exist
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

            # Wait for creation to complete
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


def parse_date(date_str: str) -> datetime:
    """Parses CLI YYYY-MM-DD date strings into timezone-aware UTC datetimes."""
    try:
        return datetime.fromisoformat(f"{date_str}T00:00:00").replace(
            tzinfo=timezone.utc
        )
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Use YYYY-MM-DD."
        ) from e


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Module 1: VN30 Numeric Market Data Stream & Backfill Engine"
    )
    parser.add_argument(
        "--mode",
        choices=["continuous", "backfill"],
        default="continuous",
        help="Execution mode: 'continuous' for polling loop, 'backfill' for historical pull",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_WATCHLIST,
        help="Space-separated list of stock tickers to track (Defaults to all 30 VN30 symbols)",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=None,
        help="Backfill start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=None,
        help="Backfill end date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Polling interval in seconds for continuous mode (default: 3600s / 1 hour)",
    )
    parser.add_argument(
        "--resolution", default="1D", help="Timeframe resolution (e.g., '1D', '1H')"
    )
    parser.add_argument(
        "--kafka-broker", default=config.kafka_broker, help="Kafka broker endpoint"
    )
    parser.add_argument(
        "--output-topic",
        default="market-ohlcv",
        help="Target Kafka topic for published market quotes",
    )
    parser.add_argument(
        "--mongo-uri", default=config.mongo_uri, help="MongoDB connection URI"
    )

    args = parser.parse_args()

    # Validate backfill requirements
    if args.mode == "backfill" and (not args.start_date or not args.end_date):
        logger.error(
            "❌ Both --start-date and --end-date are required when running in --mode backfill!"
        )
        sys.exit(1)

    logger.info(
        f"🚀 Initializing Module 1 Market Stream tracking {len(args.symbols)} symbols..."
    )
    logger.debug(f"Watchlist: {args.symbols}")

    # 1. Instantiate Storage and Streaming Adapters
    market_repo = MongoRepository[MarketQuote](
        uri=args.mongo_uri,
        database="financial_ai",
        collection="silver_market_quotes",
        model_class=MarketQuote,
    )

    publisher = KafkaPublisher[MarketQuote](
        bootstrap_servers=args.kafka_broker,
        client_id="module1-market-publisher",
    )

    # 2. Execute Infrastructure Bootstrapping BEFORE starting application loops
    bootstrap_infrastructure(
        mongo_repo=market_repo,
        kafka_broker=args.kafka_broker,
        topic_name=args.output_topic,
    )

    # 3. Instantiate Data Provider Connector & Orchestrator Service
    connector = VnstockConnector(watchlist=args.symbols, resolution=args.resolution)

    # Verify provider accessibility
    if not connector.health_check():
        logger.warning(
            "⚠️ Data provider health check failed! Ensure internet connectivity and valid vnstock configuration."
        )

    service = MarketAcquisitionService(
        connector=connector,
        repository=market_repo,
        publisher=publisher,
        kafka_topic=args.output_topic,
    )

    # 4. Route Execution Mode
    try:
        if args.mode == "backfill":
            logger.info(
                f"⏳ Executing historical backfill from {args.start_date.date()} to {args.end_date.date()}..."
            )
            report = service.run_backfill(
                start_date=args.start_date, end_date=args.end_date
            )
            logger.info(
                f"🎉 Backfill complete in {report.duration_seconds}s | "
                f"Fetched: {report.fetched} | Valid: {report.valid} | Stored: {report.stored} | Published: {report.published}"
            )
        else:
            logger.info(
                f"🔄 Starting continuous real-time market acquisition loop (Polling every {args.interval}s)..."
            )
            service.run_continuous(interval_seconds=args.interval)
    except KeyboardInterrupt:
        logger.info("🛑 Market acquisition stream stopped cleanly by user.")
    finally:
        logger.info("Closing infrastructure connections...")
        publisher.close()
        market_repo.close()
        logger.info("✅ All connections closed.")


if __name__ == "__main__":
    main()

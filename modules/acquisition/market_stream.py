import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

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
    logger.info("🛠️ Bootstrapping infrastructure layers...")

    try:
        mongo_repo.collection.create_index(
            [("symbol", 1), ("timestamp", -1)],
            unique=True,
            name="idx_unique_symbol_timestamp",
        )
        logger.info(f"✅ MongoDB compound index 'idx_unique_symbol_timestamp' verified.")
    except Exception as e:
        logger.warning(f"⚠️ Notice during MongoDB index creation: {e!s}")

    try:
        admin_client = AdminClient({"bootstrap.servers": kafka_broker})
        existing_topics = admin_client.list_topics(timeout=5.0).topics

        if topic_name not in existing_topics:
            logger.info(f"Topic '{topic_name}' not found. Pre-creating...")
            new_topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
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


def parse_date(date_str: str) -> datetime:
    try:
        return datetime.fromisoformat(f"{date_str}T00:00:00").replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.") from e


def main() -> None:
    parser = argparse.ArgumentParser(description="Module 1: VN30 Numeric Market Data Stream & Backfill Engine")
    parser.add_argument("--mode", choices=["continuous", "backfill"], default="continuous")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_WATCHLIST)
    parser.add_argument("--start-date", type=parse_date, default=None)
    parser.add_argument("--end-date", type=parse_date, default=None)
    parser.add_argument("--interval", type=int, default=3600)
    parser.add_argument("--resolution", default="1D")
    parser.add_argument("--kafka-broker", default=config.kafka_broker)
    parser.add_argument("--output-topic", default="market-ohlcv")
    parser.add_argument("--mongo-uri", default=config.mongo_uri)

    args = parser.parse_args()

    if args.mode == "backfill" and (not args.start_date or not args.end_date):
        logger.error("❌ Both --start-date and --end-date are required when running in --mode backfill!")
        sys.exit(1)

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

    bootstrap_infrastructure(market_repo, args.kafka_broker, args.output_topic)

    connector = VnstockConnector(watchlist=args.symbols, resolution=args.resolution)

    service = MarketAcquisitionService(
        connector=connector,
        repository=market_repo,
        publisher=publisher,
        kafka_topic=args.output_topic,
    )

    # ==========================================================
    # AUTO-BOOTSTRAP LOGIC
    # ==========================================================
    if args.mode == "continuous" and market_repo.count() == 0:
        logger.info("⚠️ Database is empty! Auto-running 30-day market backfill before continuous mode...")
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)
        service.run_backfill(start_date=start_date, end_date=end_date)
        logger.info("✅ Auto-bootstrap complete. Transitioning to continuous mode...")

    try:
        if args.mode == "backfill":
            report = service.run_backfill(start_date=args.start_date, end_date=args.end_date)
            logger.info(f"🎉 Backfill complete in {report.duration_seconds}s")
        else:
            logger.info(f"🔄 Starting continuous real-time market acquisition loop...")
            service.run_continuous(interval_seconds=args.interval)
    except KeyboardInterrupt:
        logger.info("🛑 Market acquisition stream stopped cleanly by user.")
    finally:
        publisher.close()
        market_repo.close()


if __name__ == "__main__":
    main()
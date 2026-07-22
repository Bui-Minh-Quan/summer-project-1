import os
import sys
import argparse
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from connectors.fireant import FireAntConnector
from repository.mongodb import MongoRepository
from publishers.kafka_publisher import KafkaDocumentPublisher
from services.acquisition_service import AcquisitionService

from preprocessing.cleaner import DocumentCleaner
from preprocessing.validator import DocumentValidator
from preprocessing.deduplicator import DocumentDeduplicator

from config import config


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
)
logger = logging.getLogger("main")


def main():
    load_dotenv()

    MONGO_URI = config.mongo_uri
    FIREANT_BEARER = config.fire_ant_bearer
    KAFKA_BROKER = config.kafka_broker
    DATABASE = "financial_ai"

    
    # CLI Argument Parsing
    parser = argparse.ArgumentParser(description="Financial AI Platform - Data Acquisition Engine")
    parser.add_argument("--mode", choices=["continuous", "backfill"], default="continuous", help="Execution mode")
    parser.add_argument("--days", type=int, default=3, help="Number of historical days to backfill (if mode=backfill)")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between scraping cycles (if mode=continuous)")
    args = parser.parse_args()

    print("=" * 65)
    print(" 🚀 Financial AI Platform - Acquisition Module (With Kafka)")
    print("=" * 65)

    connector = FireAntConnector(bearer_token=config.fire_ant_bearer)
    if not connector.health_check():
        logger.error("❌ FireAnt API is unreachable. Aborting.")
        sys.exit(1)
    logger.info("✅ FireAnt API Connection Established.")

    raw_repo = MongoRepository(uri=config.mongo_uri, database=DATABASE, collection="raw_documents")
    doc_repo = MongoRepository(uri=config.mongo_uri, database=DATABASE, collection="documents")
    publisher = KafkaDocumentPublisher(bootstrap_servers=config.kafka_broker)

    # Instantiate Orchestrator
    service = AcquisitionService(
        connector=connector,
        raw_repository=raw_repo,
        document_repository=doc_repo,
        cleaner=DocumentCleaner(),         
        validator=DocumentValidator(),      
        deduplicator=DocumentDeduplicator(),
        publisher=publisher
    )

    try:
        if args.mode == "backfill":
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=args.days)
            
            report = service.run_backfill(start_date, end_date)

            print("\n" + "=" * 40)
            print(" 📊 BACKFILL EXECUTION REPORT")
            print("=" * 40)
            print(f"Fetched Raw Payloads  : {report.fetched}")
            print(f"Saved to Bronze Lake  : {report.raw_saved}")
            print(f"Mapped Canonical      : {report.mapped}")
            print(f"Cleaned               : {report.cleaned}")
            print(f"Failed Validation     : {report.invalid}")
            print(f"Duplicates Ignored    : {report.duplicates}")
            print(f"Stored in Silver DB   : {report.stored}")
            print(f"Published to Kafka    : {report.published}")
            print(f"Total Duration        : {report.duration:.2f} seconds")
            print("=" * 40 + "\n")

        elif args.mode == "continuous":
            service.run_continuous(interval_seconds=args.interval)

    finally:
        logger.info("Closing connections...")
        raw_repo.close()
        doc_repo.close()
        publisher.close()
        logger.info("✅ Shutdown complete.")

if __name__ == "__main__":
    main()
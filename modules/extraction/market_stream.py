"""
CLI Entry Point for Module 2 Feature Engineering Pipeline.
Listens concurrently to 'market-ohlcv' (Stream 1) and 'financial-news' (Stream 2).
"""

import asyncio
import logging
import sys
from typing import Any

from config import config
from consumers.kafka_consumer import MarketDataKafkaConsumer, PostFeatureKafkaConsumer
from models.features import MarketSentimentFeatureVector
from publishers.kafka_publisher import KafkaPublisher  # NEW IMPORT
from repository.mongodb import MongoRepository
from services.feature_service import FeatureEngineeringService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("module2_feature_pipeline")


async def main() -> None:
    logger.info("🚀 Starting Module 2 Feature Engineering Pipeline...")

    feature_repo = MongoRepository[MarketSentimentFeatureVector](
        uri=config.mongo_uri,
        database="financial_ai",
        collection="gold_market_features",
        model_class=MarketSentimentFeatureVector,
    )
    feature_repo.collection.create_index([("symbol", 1), ("timestamp", -1)], unique=True)

    silver_market_repo = MongoRepository[Any](
        uri=config.mongo_uri,
        database="financial_ai",
        collection="silver_market_quotes",
    )

    # Instantiate the publisher for the frontend stream
    publisher = KafkaPublisher[MarketSentimentFeatureVector](
        bootstrap_servers=config.kafka_broker,
        client_id="module2-feature-publisher"
    )

    # Pass the publisher to the service
    feature_service = FeatureEngineeringService(
        feature_repo=feature_repo, 
        silver_market_repo=silver_market_repo,
        publisher=publisher,
        output_topic="gold-market-features"
    )

    market_consumer = MarketDataKafkaConsumer(
        feature_service=feature_service,
        bootstrap_servers=config.kafka_broker,
        topic="market-ohlcv",
    )

    post_consumer = PostFeatureKafkaConsumer(
        feature_service=feature_service,
        bootstrap_servers=config.kafka_broker,
        topic="financial-news",
    )

    logger.info("🔄 Launching concurrent Kafka listeners for Market Bars and Social Posts...")
    try:
        await asyncio.gather(
            market_consumer.start(),
            post_consumer.start(),
        )
    except KeyboardInterrupt:
        logger.info("🛑 Feature Pipeline stopped cleanly by user.")
    finally:
        feature_repo.close()
        silver_market_repo.close()
        publisher.close() 
        logger.info("✅ All repository and publisher connections closed.")


if __name__ == "__main__":
    asyncio.run(main())
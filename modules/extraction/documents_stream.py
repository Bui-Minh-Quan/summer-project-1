"""
CLI entry point for Module 2: Structured Knowledge Graph Extraction Engine (Target-Anchored TRR).
Supports both --mode continuous (Kafka streaming) and --mode backfill (MongoDB batching).
Enforces explicit pre-initialization of MongoDB indices and Kafka topics.
"""

import argparse
import asyncio
import logging
import sys
from typing import Any

from confluent_kafka.admin import AdminClient, NewTopic
from consumers.kafka_consumer import DocumentKafkaConsumer

from modules.extraction.cache.cache import LLMExtractionCache
from modules.extraction.config import config
from modules.extraction.llm.vllm_clients import VLLMClient
from modules.extraction.models.extraction import ExtractionResult
from modules.extraction.prompts.templates import VN30_ALIAS_MAP
from modules.extraction.publishers.kafka_publisher import KafkaPublisher
from modules.extraction.repository.mongodb import MongoRepository
from modules.extraction.services.extraction_service import ExtractionService
from modules.extraction.services.proxy_service import NewsOnlyServiceProxy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("module2_documents_stream")


def bootstrap_infrastructure(
    extraction_repo: MongoRepository[ExtractionResult],
    kafka_broker: str,
    output_topic: str,
    num_partitions: int = 3,
    replication_factor: int = 1,
) -> None:
    """Pre-initializes MongoDB indices and verifies/creates Kafka output topics."""
    logger.info("🛠️ Bootstrapping Module 2 extraction infrastructure...")

    # 1. MongoDB indices for fast graph querying and idempotency checks
    try:
        extraction_repo.collection.create_index([("document_id", 1)], unique=True, name="idx_unique_staged_doc_id")
        extraction_repo.collection.create_index([("relations.subject.name", 1)])
        extraction_repo.collection.create_index([("relations.object.name", 1)])
        logger.info("✅ MongoDB indices verified on 'staged_graph_knowledge' collection.")
    except Exception as e: # noqa: BLE001
        logger.warning(f"⚠️ Notice during MongoDB index verification: {e!s}")

    # 2. Pre-create Kafka output topic via AdminClient
    try:
        admin_client = AdminClient({"bootstrap.servers": kafka_broker})
        existing_topics = admin_client.list_topics(timeout=5.0).topics

        if output_topic not in existing_topics:
            logger.info(f"Topic '{output_topic}' not found. Pre-creating with {num_partitions} partitions...")
            new_topic = NewTopic(output_topic, num_partitions=num_partitions, replication_factor=replication_factor)
            futures = admin_client.create_topics([new_topic])
            for topic, future in futures.items():
                try:
                    future.result()
                    logger.info(f"✅ Kafka topic '{topic}' successfully created.")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"❌ Failed to create topic '{topic}': {e!s}")
        else:
            logger.info(f"✅ Kafka topic '{output_topic}' already exists.")
    except Exception as e:  # noqa: BLE001
        logger.error(f"⚠️ Could not verify Kafka topics via AdminClient: {e!s}")


async def run_continuous_mode(
    service: ExtractionService,
    kafka_broker: str,
    input_topic: str,
    target_symbols: list[str] | None = None,
) -> None:
    """Runs continuous real-time extraction listening to Kafka, filtering strictly for news."""
    proxy_service = NewsOnlyServiceProxy(service, default_symbols=target_symbols)
    consumer = DocumentKafkaConsumer(
        extraction_service=proxy_service,
        bootstrap_servers=kafka_broker,
        topic=input_topic,
    )
    logger.info(f"🔄 Starting Continuous Mode worker on topic '{input_topic}' (Filtering for document_type='news')...")
    await consumer.start()


async def run_backfill_mode(
    service: ExtractionService,
    mongo_uri: str,
    source_db: str,
    source_collection: str,
    batch_size: int,
    start_date: str | None = None,
    end_date: str | None = None,
    date_field: str = "published_at",
    target_symbols: list[str] | None = None,
) -> None:
    """Queries historical news articles from MongoDB filtered by document_type='news' and date range."""
    logger.info(f"⏳ Starting Backfill Mode (Batch size: {batch_size}, Source: {source_db}.{source_collection})...")
    source_repo = MongoRepository[Any](uri=mongo_uri, database=source_db, collection=source_collection)

    query: dict[str, Any] = {"document_type": "news"}
    if start_date or end_date:
        date_filter: dict[str, str] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query[date_field] = date_filter

    logger.info(f"Querying MongoDB with filter: {query}")
    total_docs = source_repo.collection.count_documents(query)
    logger.info(f"Found {total_docs} historical news documents matching criteria.")

    if total_docs == 0:
        logger.warning("No documents found! Check your --start-date, --end-date, or --date-field arguments.")
        source_repo.close()
        return

    cursor = source_repo.collection.find(query)
    batch: list[dict[str, Any]] = []

    for doc in cursor:
        doc.pop("_id", None)
        if target_symbols is not None:
            doc["symbols"] = target_symbols

        batch.append(doc)
        if len(batch) >= batch_size:
            await service.process_batch(batch)
            batch.clear()

    if batch:
        await service.process_batch(batch)

    source_repo.close()
    logger.info("🎉 Historical news backfill completed successfully!")


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Module 2: Structured Knowledge Graph Extraction Engine")
    parser.add_argument("--mode", choices=["continuous", "backfill"], default="continuous", help="Execution mode")
    parser.add_argument("--prompt-version", default="v1.0", help="Prompt template version (e.g., v1.0)")
    parser.add_argument("--max-passes", type=int, default=2, help="Number of iterative TRR extraction passes per document")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for historical backfill mode")
    parser.add_argument("--target-symbols", nargs="+", default=None, help="Space-separated list of target stock tickers")
    parser.add_argument("--start-date", default=None, help="Backfill start date filter (YYYY-MM-DD or ISO string)")
    parser.add_argument("--end-date", default=None, help="Backfill end date filter (YYYY-MM-DD or ISO string)")
    parser.add_argument("--date-field", default="published_at", help="MongoDB timestamp field name for date filtering")
    parser.add_argument("--vllm-url", default=config.vllm_url, help="vLLM server endpoint")
    parser.add_argument("--redis-url", default=config.redis_url, help="Redis cache endpoint")
    parser.add_argument("--mongo-uri", default=config.mongo_uri, help="MongoDB connection URI")
    parser.add_argument("--kafka-broker", default=config.kafka_broker, help="Kafka broker endpoint")
    parser.add_argument("--input-topic", default="financial-news", help="Kafka input topic from Module 1")
    parser.add_argument("--output-topic", default="extracted-knowledge-topic", help="Kafka output topic for downstream graph")

    args = parser.parse_args()

    # 1. Validate Target Symbols
    valid_target_symbols: list[str] | None = None
    if args.target_symbols:
        valid_target_symbols = [s.strip().upper() for s in args.target_symbols if s.strip().upper() in VN30_ALIAS_MAP]
        if not valid_target_symbols:
            logger.warning("None of the provided --target-symbols match the VN30 list! Proceeding with NO target override.")
            valid_target_symbols = None
        else:
            logger.info(f"Validated Target Portfolio symbols: {valid_target_symbols}")

    # 2. Instantiate Infrastructure Adapters
    llm_client = VLLMClient(base_url=args.vllm_url)
    cache = LLMExtractionCache(redis_url=args.redis_url)
    await cache.connect()

    extraction_repo = MongoRepository[ExtractionResult](
        uri=args.mongo_uri,
        database="financial_ai",
        collection="staged_graph_knowledge",
        model_class=ExtractionResult,
        index_fields=["document_id", "relations.subject.name", "relations.object.name"],
    )
    publisher = KafkaPublisher[ExtractionResult](bootstrap_servers=args.kafka_broker, client_id="module2-extraction-publisher")

    # 3. Bootstrap Infrastructure BEFORE execution
    bootstrap_infrastructure(extraction_repo=extraction_repo, kafka_broker=args.kafka_broker, output_topic=args.output_topic)

    # 4. Verify vLLM Health Status
    if not await llm_client.health_check():
        logger.error("❌ Failed to connect to vLLM server on port 8000. Ensure your Docker container is running!")
        sys.exit(1)

    logger.info(f"✅ vLLM server is healthy. Running extraction pipeline with max_passes={args.max_passes}.")

    # 5. Instantiate Orchestrator Service
    service = ExtractionService(
        llm_client=llm_client,
        cache=cache,
        repository=extraction_repo,
        publisher=publisher,
        prompt_version=args.prompt_version,
        output_kafka_topic=args.output_topic,
        max_passes=args.max_passes,
    )

    # 6. Route Execution Mode
    try:
        if args.mode == "continuous":
            await run_continuous_mode(
                service=service, kafka_broker=args.kafka_broker, input_topic=args.input_topic, target_symbols=valid_target_symbols
            )
        else:
            await run_backfill_mode(
                service=service,
                mongo_uri=args.mongo_uri,
                source_db="financial_ai",
                source_collection="documents",
                batch_size=args.batch_size,
                start_date=args.start_date,
                end_date=args.end_date,
                date_field=args.date_field,
                target_symbols=valid_target_symbols,
            )
    finally:
        logger.info("Initiating graceful shutdown of infrastructure clients...")
        await llm_client.close()
        await cache.close()
        publisher.close()
        extraction_repo.close()
        logger.info("✅ All connections closed cleanly.")


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("🛑 Module 2 process stopped by user.")


if __name__ == "__main__":
    main()
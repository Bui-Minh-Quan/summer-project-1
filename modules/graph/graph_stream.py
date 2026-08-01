"""
CLI entry point for Module 3: Graph Building Engine.
Supports continuous Kafka streaming and historical MongoDB backfill modes.
"""

import argparse
import asyncio
import logging
import sys
from typing import Any

from config import config
from consumers.kafka_consumer import ExtractionKafkaConsumer
from pymongo import MongoClient
from repository.neo4j_repo import Neo4jRepository
from services.graph_service import GraphService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("module3_graph_stream")


async def run_continuous_mode(
    service: GraphService,
    kafka_broker: str,
    topic: str,
) -> None:
    """Runs continuous real-time graph hydration listening to Kafka."""
    consumer = ExtractionKafkaConsumer(
        graph_service=service,
        bootstrap_servers=kafka_broker,
        topic=topic,
    )
    logger.info(f"🔄 Starting Continuous Mode worker on topic '{topic}'...")
    await consumer.start()


async def run_backfill_mode(
    service: GraphService,
    mongo_uri: str,
    database: str,
    collection: str,
    batch_size: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Queries historical extraction results from MongoDB and batches them into Neo4j."""
    logger.info(
        f"⏳ Starting Backfill Mode (Batch size: {batch_size}, Source: {database}.{collection})..."
    )
    
    # Initialize synchronous PyMongo client for backfill reading
    mongo_client: MongoClient[dict[str, Any]] = MongoClient(mongo_uri)
    db = mongo_client[database]
    coll = db[collection]

    query: dict[str, Any] = {}
    if start_date or end_date:
        date_filter: dict[str, str] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        # Assumes published_at is stored at the root of ExtractionResult
        query["published_at"] = date_filter

    logger.info(f"Querying MongoDB with filter: {query}")
    total_docs = coll.count_documents(query)
    logger.info(f"Found {total_docs} extracted documents matching criteria.")

    if total_docs == 0:
        logger.warning("No documents found! Check your database or date filters.")
        mongo_client.close()
        return

    cursor = coll.find(query)
    batch: list[dict[str, Any]] = []
    total_processed = 0

    for doc in cursor:
        doc.pop("_id", None)
        batch.append(doc)
        
        if len(batch) >= batch_size:
            await service.process_batch(batch)
            total_processed += len(batch)
            logger.info(f"Progress: {total_processed}/{total_docs} documents processed.")
            batch.clear()

    # Process remaining documents in the final batch
    if batch:
        await service.process_batch(batch)
        total_processed += len(batch)
        logger.info(f"Progress: {total_processed}/{total_docs} documents processed.")

    mongo_client.close()
    logger.info("🎉 Historical graph backfill completed successfully!")


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Module 3: Graph Building Engine")
    parser.add_argument(
        "--mode", 
        choices=["continuous", "backfill"], 
        default="continuous", 
        help="Execution mode"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=config.batch_size, 
        help="Batch size for historical backfill mode"
    )
    parser.add_argument(
        "--start-date", 
        default=None, 
        help="Backfill start date filter (ISO string, e.g., 2025-01-01T00:00:00Z)"
    )
    parser.add_argument(
        "--end-date", 
        default=None, 
        help="Backfill end date filter (ISO string)"
    )
    
    args = parser.parse_args()

    logger.info("=================================================")
    logger.info(" 🚀 Financial AI Platform - Graph Engine (Mod 3) ")
    logger.info("=================================================")

    # 1. Initialize Infrastructure (Neo4j)
    neo4j_repo = Neo4jRepository(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    await neo4j_repo.connect()
    
    # 2. Enforce DB Constraints (Idempotency limits)
    await neo4j_repo.ensure_constraints()

    # 3. Instantiate Orchestrator Service
    service = GraphService(
        repo=neo4j_repo,
        confidence_threshold=config.confidence_threshold
    )

    # 4. Route Execution Mode
    try:
        if args.mode == "continuous":
            await run_continuous_mode(
                service=service, 
                kafka_broker=config.kafka_broker, 
                topic="extracted-knowledge-topic"
            )
        else:
            await run_backfill_mode(
                service=service,
                mongo_uri=config.mongo_uri,
                database="financial_ai",
                collection="staged_graph_knowledge",
                batch_size=args.batch_size,
                start_date=args.start_date,
                end_date=args.end_date,
            )
    finally:
        logger.info("Initiating graceful shutdown of Graph infrastructure...")
        await neo4j_repo.close()
        logger.info("✅ All connections closed cleanly.")


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("🛑 Module 3 Graph Engine stopped by user.")


if __name__ == "__main__":
    main()
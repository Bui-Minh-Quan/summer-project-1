"""
Kafka Consumer for Module 3: Graph Building Engine.
Consumes Extracted Knowledge payloads from Module 2 and triggers Neo4j graph hydration.
"""

import asyncio
import json
import logging
from typing import Any

from confluent_kafka import Consumer, KafkaError

logger = logging.getLogger(__name__)


class ExtractionKafkaConsumer:
    """Asynchronous consumer for real-time ExtractionResult processing via Neo4j."""

    def __init__(
        self,
        graph_service: Any,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "module3-graph-building-v1",
        topic: str = "extracted-knowledge-topic",
    ) -> None:
        self.graph_service = graph_service
        self.topic = topic
        self.conf = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
        self.consumer: Consumer | None = None

    async def start(self) -> None:
        """Starts the continuous async loop consuming ExtractionResult events from Kafka."""
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe([self.topic])
        logger.info(
            f"Subscribed to Kafka topic '{self.topic}'. Listening for extracted knowledge..."
        )

        try:
            while True:
                # Poll Kafka broker in a non-blocking thread
                msg = await asyncio.to_thread(self.consumer.poll, 0.1)
                if msg is None:
                    await asyncio.sleep(0.05)
                    continue

                # Narrow KafkaError using local variable
                err = msg.error()
                if err is not None:
                    if err.code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka extraction consumer error: {err}")
                    continue

                try:
                    raw_bytes = msg.value()
                    if not raw_bytes:
                        continue

                    payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
                    
                    # Delegate processing to the GraphService orchestrator
                    await self.graph_service.process_extraction_result(payload)

                except Exception as e:  # noqa: BLE001
                    logger.error(
                        f"Failed to process extraction result at offset {msg.offset()}: {e!s}"
                    )

        except asyncio.CancelledError:
            logger.info("Extraction consumer loop cancelled.")
        finally:
            if self.consumer:
                self.consumer.close()
                logger.info("Closed extraction Kafka consumer connection.")
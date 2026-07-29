"""
Generic Kafka publisher implementation using confluent_kafka.
Supports streaming Documents, MarketQuotes, or any Pydantic domain model.
"""

import logging
from typing import Any, Generic, TypeVar

from confluent_kafka import KafkaError, Producer
from pydantic import BaseModel

logger = logging.getLogger("kafka_publisher")
T = TypeVar("T", bound=BaseModel)


class KafkaPublisher(Generic[T]):
    """Generic Kafka producer capable of publishing any Pydantic domain model."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "acquisition-publisher",
    ) -> None:
        self.conf = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": client_id,
            "acks": "all",
            "retries": 3,
            "linger.ms": 10,
        }
        self.producer = Producer(self.conf)

    def _delivery_callback(self, err: KafkaError | None, msg: Any) -> None:
        """Asynchronous callback triggered when the broker acknowledges a message."""
        if err is not None:
            key_str = msg.key().decode("utf-8") if msg.key() else "UNKNOWN_KEY"
            logger.error(f"❌ Failed to deliver message [{key_str}]: {err}")
        else:
            key_str = msg.key().decode("utf-8") if msg.key() else "NO_KEY"
            logger.debug(
                f"📤 Published [{key_str}] to {msg.topic()} [Partition {msg.partition()}] at offset {msg.offset()}"
            )

    def publish(self, topic: str, entity: T, key: str | None = None) -> bool:
        """
        Serialize a Pydantic entity to JSON and produce it to the target topic.
        If 'key' is not provided, dynamically extracts '.id', '.symbol', or '.ticker'.
        """
        try:
            # 1. Pydantic v2 JSON serialization
            payload_bytes = entity.model_dump_json().encode("utf-8")

            # 2. Smart primary key extraction for Kafka partitioning
            if key:
                key_str = key
            else:
                key_str = str(
                    getattr(entity, "id", None)
                    or getattr(entity, "symbol", None)
                    or getattr(entity, "ticker", "DEFAULT_KEY")
                )
            key_bytes = key_str.encode("utf-8")

            # 3. Asynchronous produce call
            self.producer.produce(
                topic=topic,
                key=key_bytes,
                value=payload_bytes,
                callback=self._delivery_callback,
            )

            # 4. Trigger network I/O events without blocking the main loop
            self.producer.poll(0)
            return True

        except Exception as e:  # noqa: BLE001
            entity_id = getattr(entity, "id", getattr(entity, "symbol", "unknown"))
            logger.error(f"Exception publishing entity [{entity_id}] to Kafka: {e}")
            return False

    def publish_batch(self, topic: str, entities: list[T]) -> int:
        """Publishes a list of entities and flushes the buffer."""
        if not entities:
            return 0

        success_count = 0
        for entity in entities:
            if self.publish(topic, entity):
                success_count += 1

        # Wait for all asynchronous messages in the buffer to be sent
        unflushed = self.producer.flush(timeout=10.0)
        published_count = len(entities) - unflushed
        return published_count

    def close(self) -> None:
        """Ensure all remaining messages are sent before shutting down."""
        logger.info("Flushing remaining Kafka messages...")
        self.producer.flush(timeout=5.0)


# =====================================================================
# BACKWARD COMPATIBILITY ALIAS
# Prevents breaking legacy fixtures or tests that import KafkaDocumentPublisher
# =====================================================================
# KafkaDocumentPublisher = KafkaPublisher[Document]

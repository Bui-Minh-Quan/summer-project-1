"""
Generic Kafka publisher implementation using confluent_kafka.
"""

import logging
from typing import Any, Generic, TypeVar

from confluent_kafka import KafkaError, Producer
from publishers.base import BasePublisher
from pydantic import BaseModel

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class KafkaPublisher(BasePublisher[T], Generic[T]):
    """Generic Kafka producer capable of streaming any Pydantic domain model."""

    def __init__(self, bootstrap_servers: str = "127.0.0.1:9092", client_id: str = "module2-extraction-producer") -> None:
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": client_id,
            "acks": "all",
            "retries": 3,
            "enable.idempotence": True
        })

    def _delivery_report(self, err: KafkaError | None, msg: Any) -> None:
        """Internal callback executed when a message is acknowledged by the Kafka broker."""
        if err is not None:
            logger.error(f"Message delivery failed for topic {msg.topic()}: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    def publish(self, topic: str, entity: T, key: str | None = None) -> bool:
        """Publish a single Pydantic entity to Kafka."""
        try:
            payload = entity.model_dump_json()
            msg_key = key or getattr(entity, "id", None)
            
            self.producer.produce(
                topic=topic,
                value=payload.encode("utf-8"),
                key=str(msg_key).encode("utf-8") if msg_key else None,
                on_delivery=self._delivery_report
            )
            self.producer.poll(0)
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to publish to Kafka topic '{topic}': {e}")
            return False

    def publish_batch(self, topic: str, entities: list[T]) -> int:
        """Publish multiple entities in a high-throughput loop."""
        if not entities:
            return 0

        success_count = 0
        for entity in entities:
            if self.publish(topic, entity):
                success_count += 1
                
        self.flush(timeout=10.0)
        return success_count

    def flush(self, timeout: float = 10.0) -> int:
        """Flush pending network messages without closing the connection."""
        return self.producer.flush(timeout)

    def close(self) -> None:
        """Flush remaining messages and close the producer."""
        logger.info("Flushing remaining Kafka messages before shutdown...")
        self.producer.flush()
import logging 
import json 
from typing import Optional 
from confluent_kafka import Producer, KafkaError 
from models.document import Document

logger = logging.getLogger("kafka_publisher")

class KafkaDocumentPublisher:
    # Publish canonical document objects to kafka topics for 
    # downstream AI consumption
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.conf = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": "acquisition-publisher",
            "acks": "all",
            "retries": 3,
            "linger.ms": 10
        }
        
        self.producer = Producer(self.conf)
    
    def _delivery_callback(self, err: Optional[KafkaError], msg):
        # Asynchronous callback triggered when broker
        # acknowledges a message
        if err is not None:
            logger.error(f"❌ Failed to deliver document {msg.key().decode('utf-8')}: {err}")
        else:
            logger.debug(f"📤 Published doc {msg.key().decode('utf-8')} to {msg.topic()} [Partition {msg.partition()}]")
        
    
    def publish(self, topic: str, document:Document) -> None:
        # Serialize a Pydantic document to JSON and produce it to 
        # the target topic
        try:
            # Pydantic v2 JSON serialization
            payload_bytes = document.model_dump_json().encode("utf-8")
            key_bytes = document.id.encode("utf-8")

            # Asynchronous produce call
            self.producer.produce(
                topic=topic,
                key=key_bytes,
                value=payload_bytes,
                callback=self._delivery_callback
            )

            # Trigger network I/O events without blocking the main loop
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Exception publishing document {document.id} to Kafka: {e}")
    
    def publish_batch(self, topic: str, documents: list[Document]) -> int:
        # Publishes a list of documents and flushes the buffer
        if not documents:
            return 0
        
        for doc in documents:
            self.publish(topic, doc)
        
        # Wait for all asynchronous messages in the buffer to be sent
        unflushed = self.producer.flush(timeout=10.0)
        published_count = len(documents) - unflushed
        return published_count
    

    def close(self):
        # Ensure all remaining messages are sent before shutting down
        logger.info("Flushing remaining Kafka messages")
        self.producer.flush(timeout=5.0)

            

"""
Consolidated Kafka Consumer Adapters for Module 2.
"""

import asyncio
import json
import logging
from typing import Any

from confluent_kafka import Consumer, KafkaError
from models.features import MarketQuoteInput

logger = logging.getLogger(__name__)


class DocumentKafkaConsumer:
    """Asynchronous consumer for real-time news/post extraction via vLLM."""

    def __init__(
        self,
        extraction_service: Any,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "module2-extraction-v1",
        topic: str = "financial-news",
    ) -> None:
        self.extraction_service = extraction_service
        self.topic = topic
        self.conf = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
        self.consumer: Consumer | None = None

    async def start(self) -> None:
        """Starts the continuous async loop consuming documents from Kafka."""
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe([self.topic])
        logger.info(f"Subscribed to Kafka topic '{self.topic}'. Listening for live documents...")

        try:
            while True:
                msg = await asyncio.to_thread(self.consumer.poll, 0.1)
                if msg is None:
                    await asyncio.sleep(0.05)
                    continue

                # ✨ Line 51 Fix: Narrow KafkaError using local variable
                err = msg.error()
                if err is not None:
                    if err.code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka consumer error: {err}")
                    continue

                try:
                    raw_bytes = msg.value()
                    if not raw_bytes:
                        continue

                    payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
                    doc_id = str(payload.get("id") or payload.get("fingerprint") or payload.get("_id") or "")
                    title = payload.get("title") or ""
                    content = payload.get("content") or ""

                    if doc_id and content:
                        await self.extraction_service.process_document(
                            document_id=doc_id,
                            title=title,
                            content=content,
                            symbols=payload.get("symbols"),
                            document_type=payload.get("document_type") or payload.get("type"),
                        )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to process Kafka document offset {msg.offset()}: {e}")

        except asyncio.CancelledError:
            logger.info("Document consumer loop cancelled.")
        finally:
            if self.consumer:
                self.consumer.close()


class MarketDataKafkaConsumer:
    """Asynchronous consumer for real-time market OHLCV bars."""

    def __init__(
        self,
        feature_service: Any,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "module2-feature-market-v1",
        topic: str = "market-ohlcv",
    ) -> None:
        self.feature_service = feature_service
        self.topic = topic
        self.conf = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
        self.consumer: Consumer | None = None

    async def start(self) -> None:
        """Starts the continuous async loop consuming market quotes from Kafka."""
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe([self.topic])
        logger.info(f"Subscribed to Kafka topic '{self.topic}'. Listening for market quotes...")

        try:
            while True:
                msg = await asyncio.to_thread(self.consumer.poll, 0.1)
                if msg is None:
                    await asyncio.sleep(0.05)
                    continue

                # ✨ Line 117 Fix: Narrow KafkaError using local variable
                err = msg.error()
                if err is not None:
                    if err.code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka market consumer error: {err}")
                    continue

                try:
                    raw_bytes = msg.value()
                    if not raw_bytes:
                        continue
                    payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
                    quote_input = MarketQuoteInput.model_validate(payload)
                    await self.feature_service.process_market_quote(quote_input)
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to process market quote offset {msg.offset()}: {e}")

        except asyncio.CancelledError:
            logger.info("Market consumer loop cancelled.")
        finally:
            if self.consumer:
                self.consumer.close()


class PostFeatureKafkaConsumer:
    """Asynchronous consumer for social media posts to update daily sentiment features."""

    def __init__(
        self,
        feature_service: Any,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "module2-feature-posts-v1",
        topic: str = "financial-news",
    ) -> None:
        self.feature_service = feature_service
        self.topic = topic
        self.conf = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
        self.consumer: Consumer | None = None

    async def start(self) -> None:
        """Starts the continuous async loop consuming social posts from Kafka."""
        self.consumer = Consumer(self.conf)
        self.consumer.subscribe([self.topic])
        logger.info(f"Subscribed to Kafka topic '{self.topic}'. Listening for social posts feature update...")

        try:
            while True:
                msg = await asyncio.to_thread(self.consumer.poll, 0.1)
                if msg is None:
                    await asyncio.sleep(0.05)
                    continue

                # ✨ Line 172 Fix: Narrow KafkaError using local variable
                err = msg.error()
                if err is not None:
                    if err.code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka post feature consumer error: {err}")
                    continue

                try:
                    raw_bytes = msg.value()
                    if not raw_bytes:
                        continue
                    payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
                    await self.feature_service.process_social_post(payload)
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to process post feature offset {msg.offset()}: {e}")

        except asyncio.CancelledError:
            logger.info("Post feature consumer loop cancelled.")
        finally:
            if self.consumer:
                self.consumer.close()
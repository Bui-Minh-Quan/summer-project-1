import logging
import time
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel

from modules.acquisition.models.document import Document, DocumentType, RawDocument
from modules.acquisition.preprocessing.documents_preprocessing import (
    DocumentCleaner,
    DocumentDeduplicator,
    DocumentValidator,
)
from modules.acquisition.publishers.kafka_publisher import KafkaPublisher
from modules.acquisition.repository.mongodb import MongoRepository

logger = logging.getLogger("acquisition_service")

# 1. Define a Protocol to guarantee abstraction and type safety for any future connector
class DocumentConnectorProtocol(Protocol):
    @property
    def source_name(self) -> str: ...
    
    def fetch_latest(self, **kwargs: Any) -> list[RawDocument]: ...
    
    def fetch_history(self, start_date: datetime, end_date: datetime, **kwargs: Any) -> list[RawDocument]: ...
    
    def map_document(self, raw: RawDocument) -> Document | None: ...


class PipelineReport(BaseModel):
    # Track metrics for a single ingestion execution cycle
    fetched: int = 0
    raw_saved: int = 0
    mapped: int = 0
    cleaned: int = 0
    invalid: int = 0
    duplicates: int = 0
    stored: int = 0
    published: int = 0
    duration: float = 0.0


class AcquisitionService:
    def __init__(
        self,
        connector: DocumentConnectorProtocol, # 2. Use the Protocol for strict abstraction
        raw_repository: MongoRepository,
        document_repository: MongoRepository,
        cleaner: DocumentCleaner,
        validator: DocumentValidator,
        deduplicator: DocumentDeduplicator,
        publisher: KafkaPublisher,
        kafka_topic: str = "financial-news",
    ):
        self.connector = connector
        self.raw_repository = raw_repository
        self.document_repository = document_repository
        self.cleaner = cleaner
        self.validator = validator
        self.deduplicator = deduplicator
        self.publisher = publisher
        self.kafka_topic = kafka_topic

    def _process_pipeline(self, raw_docs: list[RawDocument]) -> PipelineReport:
        # Internal engine pushes raw payloads through ETL and Streaming
        start_time = time.time()
        report = PipelineReport(fetched=len(raw_docs))
        if not raw_docs:
            return report

        # 1. Save untouched JSON to raw_documents collection
        for raw in raw_docs:
            try:
                self.raw_repository.collection.update_one(
                    {"id": raw.id},
                    {"$setOnInsert": raw.model_dump(mode="json")},
                    upsert=True,
                )

                report.raw_saved += 1

            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed to archive raw doc {raw.id}: {e}")

        # 2. Map to Canonical Schema
        cannonical_docs: list[Document] = []
        for raw in raw_docs:
            doc = self.connector.map_document(raw)

            if doc:
                cannonical_docs.append(doc)
                report.mapped += 1

        # 3. Clean, Validate and Deduplicate
        valid_docs: list[Document] = []
        seen_in_batch: set[str] = set()
        for doc in cannonical_docs:
            # Validate
            if not self.validator.validate(doc).valid:
                report.invalid += 1
                continue

            # Clean Text
            cleaned_doc = self.cleaner.clean(doc)
            report.cleaned += 1

            deduped_doc = self.deduplicator.process(cleaned_doc)

            if (
                deduped_doc.fingerprint in seen_in_batch
            ) or self.deduplicator.is_duplicate(deduped_doc, self.document_repository):
                report.duplicates += 1
                continue

            if deduped_doc.fingerprint:
                seen_in_batch.add(deduped_doc.fingerprint)

            valid_docs.append(deduped_doc)

        # 4. Save to Collection
        if valid_docs:
            report.stored = self.document_repository.save_many(valid_docs)

            # 5. Publish to Kafka Stream
            report.published = self.publisher.publish_batch(
                self.kafka_topic, valid_docs
            )

        report.duration = time.time() - start_time
        return report

    # Execution modes
    def run_backfill(self, start_date: datetime, end_date: datetime) -> PipelineReport:
        # Mode 1: Historical backfill
        logger.info(f"Starting backfill mode: {start_date} -> {end_date}")
        
        # 3. Use abstract fetch_history instead of hardcoding FireAnt's _crawl_feed
        raw_docs = self.connector.fetch_history(start_date=start_date, end_date=end_date)
        return self._process_pipeline(raw_docs)
        
    def run_continuous(self, interval_seconds: int = 300, batch_limit: int = 500):
        # Mode 2: Continuous streaming
        logger.info("Starting continuous streaming mode")
        try:
            while True:
                logger.info("Starting new ingestion cycle")

                # 1. Get watermarks from DB to prevent re-fetching old data
                src = self.connector.source_name
                news_watermark = self.document_repository.get_latest_timestamp(
                    source=src, doc_type=DocumentType.NEWS.value
                )
                posts_watermark = self.document_repository.get_latest_timestamp(
                    source=src, doc_type=DocumentType.POST.value
                )

                # 2. Fetch latest data abstractly via fetch_latest with kwargs
                logger.info(f"Fetching news since watermark: {news_watermark}")
                latest_news = self.connector.fetch_latest(
                    limit=batch_limit, doc_type="news", since_timestamp=news_watermark
                )

                logger.info(f"Fetching posts since watermark: {posts_watermark}")
                latest_posts = self.connector.fetch_latest(
                    limit=batch_limit, doc_type="posts", since_timestamp=posts_watermark
                )

                all_raw = latest_news + latest_posts

                # 3. Process and Publish
                if all_raw:
                    report = self._process_pipeline(all_raw)
                    logger.info(
                        f"✅ Cycle Complete | Fetched: {report.fetched} | Stored: {report.stored} | Published to Kafka: {report.published} | Time: {report.duration:.2f}s"
                    )
                else:
                    logger.info("💤 No new documents found on server.")

                # 4. Sleep until next cycle
                logger.info(f"Sleeping for {interval_seconds} seconds...\n")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("🛑 Continuous loop terminated by user.")
        finally:
            self.publisher.close()
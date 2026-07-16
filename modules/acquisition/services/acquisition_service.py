import logging
import time 
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from pydantic import BaseModel

from preprocessing.cleaner import DocumentCleaner
from preprocessing.deduplicator import DocumentDeduplicator
from preprocessing.validator import DocumentValidator

from connectors.fireant import FireAntConnector
from connectors.base import BaseConnector
from repository.mongodb import MongoRepository
from publishers.kafka_publisher import KafkaDocumentPublisher
from models.document import Document, RawDocument, DocumentType


logger = logging.getLogger("acquisition_service")

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
        connector: BaseConnector,
        raw_repository: MongoRepository,
        document_repository: MongoRepository,
        cleaner: DocumentCleaner,
        validator: DocumentValidator,
        deduplicator: DocumentDeduplicator,
        publisher: KafkaDocumentPublisher,
        kafka_topic: str = "textual-documents"
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
                    upsert=True
                )

                report.raw_saved += 1
            
            except Exception as e:
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
        for doc in cannonical_docs:
            # Validate 
            if not self.validator.validate(doc).valid: 
                report.invalid += 1
                continue 

            # Clean Text
            cleaned_doc = self.cleaner.clean(doc)
            report.cleaned += 1


            deduped_doc = self.deduplicator.process(cleaned_doc)

            valid_docs.append(deduped_doc)
        
        # 4. Save to Collection
        if valid_docs:
            report.stored = self.document_repository.save_many(valid_docs)
        
            # 5. Publish to Kafka Stream
            report.published = self.publisher.publish_batch(
                self.kafka_topic,
                valid_docs
            )
        
        report.duration = time.time() - start_time
        return report
    
    # Execution modes 
    def run_backfill(self, start_date, end_date: datetime) -> PipelineReport:
        # Mode 1: Historical backfill
        logger.info(f"Starting backfill mode: {start_date} -> {end_date}")
        raw_docs = self.connector.fetch_history(start_date=start_date, end_date=end_date)

        return self._process_pipeline(raw_docs)
    

    def run_continuous(self, interval_seconds: int = 300, batch_limit: int = 500):
        # Mode 2: Continuous streaming
        logger.info(f"Starting continuous streaming mode")
        try: 
            while True:
                logger.info("Starting new ingestion cycle")

                # 1. Get watermarks from DB to prevent re-fetching old data
                news_watermark = self.document_repository.get_latest_timestamp(source="fireant", doc_type=DocumentType.NEWS.value)
                posts_watermark = self.document_repository.get_latest_timestamp(source="fireant", doc_type=DocumentType.POST.value)

                # 2. Fetch latest data
                logger.info(f"Fetching news since watermark: {news_watermark}")
                latest_news = self.connector.fetch_latest_news(limit=batch_limit, since_timestamp=news_watermark)

                logger.info(f"Fetch posts since watermark: {posts_watermark}")
                latest_posts = self.connector.fetch_latest_posts(limit=batch_limit, since_timestamp=posts_watermark)

                all_raw = latest_news + latest_posts

                # 3. Process and Publish
                if all_raw:
                    report = self._process_pipeline(all_raw)
                    logger.info(f"✅ Cycle Complete | Fetched: {report.fetched} | Stored: {report.stored} | Published to Kafka: {report.published} | Time: {report.duration:.2f}s")
                else:
                    logger.info("💤 No new documents found on server.")

                
                # 4. Sleep untill next cycle
                logger.info(f"Sleeping for {interval_seconds} seconds...\n")
                time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            logger.info("🛑 Continuous loop terminated by user.")
        finally:
            self.publisher.close()



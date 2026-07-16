""" 
Coordinates the acquisition pipeline:
Connector -> Raw Document -> Raw MongoDB -> Document Mapping 
Validation -> Deduplication -> Cleaning -> MongoDB
"""

from dataclasses import dataclass 
from datetime import datetime 
from time import perf_counter 

from connectors.base import BaseConnector
from models.document import Document, RawDocument
from preprocessing.cleaner import DocumentCleaner
from preprocessing.validator import DocumentValidator
from preprocessing.deduplicator import DocumentDeduplicator
from repository.mongodb import MongoRepository

# Report 
@dataclass
class ProcessingReport:
    fetched: int = 0
    mapped: int = 0
    cleaned: int = 0
    invalid: int = 0
    duplicates: int = 0
    stored: int = 0
    duration: float = 0.0 

# Acquisition Service
class AcquisitionService:
    def __init__(
        self,
        connector: BaseConnector,
        raw_repository: MongoRepository,
        document_repository: MongoRepository,
        cleaner: DocumentCleaner,
        validator: DocumentValidator,
        deduplicator: DocumentDeduplicator
    ):
        self.connector = connector 

        self.raw_repository = raw_repository
        self.document_repository = document_repository

        self.cleaner = cleaner 
        self.validator = validator
        self.deduplicator = deduplicator

        # In-memory duplicate cache
        self.document_hashes: set[str] = set()

    
    # Public APIs
    def backfill_news(self, limit: int = 100) -> ProcessingReport:
        raw_documents = self.connector.fetch_latest_news(limit)

        return self._run_pipeline(raw_documents)
    
    def backfill_posts(self, limit: int = 100) -> ProcessingReport:
        raw_documents = self.connector.fetch_latest_posts(limit)
        return self._run_pipeline(raw_documents)

    def process_raw_documents(self, raw_documents: list[RawDocument]) -> ProcessingReport:
        return self._run_pipeline(raw_documents)
    
    # Internal Pipeline
    def _run_pipeline(self, raw_documents: list[RawDocument]) -> ProcessingReport:
        report = ProcessingReport()

        start = perf_counter()

        report.fetched = len(raw_documents)

        # Save raw payloads
        self.raw_repository.save_many(raw_documents)

        processed_documents: list[Document] = []

        # Process documents 
        for raw_doc in raw_documents:
            # Mapping
            document = self.connector.map_document(raw_doc)

            if document is None:
                continue 

            report.mapped += 1 
        
            # Duplicate detection
            fingerprint = self.deduplicator.fingerprint(document)

            if fingerprint in self.document_hashes:
                report.duplicates += 1
                continue

            self.document_hashes.add(fingerprint)

            # Validation
            validation = self.validator.validate(document)

            if not validation.valid:
                report.invalid += 1
                continue

            # Cleaning 
            document = self.cleaner.clean(document)
            
            processed_documents.append(document)
        
        # Save processed documents
        if processed_documents:
            report.stored = self.document_repository.save_many(processed_documents)
        
        
        report.duration = perf_counter() - start 

        return report


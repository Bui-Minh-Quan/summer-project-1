import hashlib

from models.document import Document
from repository.mongodb import MongoRepository


class DocumentDeduplicator:
    """Computes deterministic document fingerprints and manages deduplication."""

    @staticmethod
    def fingerprint(document: Document) -> str:
        # Include title, content, and source to guarantee uniqueness!
        title_part = document.title or ""
        content_part = document.content or ""
        source_part = document.source or ""
        
        text = f"{title_part}|{content_part}|{source_part}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    def process(self, document: Document) -> Document:
        """Computes and assigns the SHA-256 fingerprint to the document."""
        document.fingerprint = self.fingerprint(document)
        return document

    # In preprocessing/deduplicator.py:
    @staticmethod
    def is_duplicate(document: Document, repository: MongoRepository) -> bool: 
        if not document.fingerprint:
            document.fingerprint = DocumentDeduplicator.fingerprint(document)
        return repository.exists_by_fingerprint(document.fingerprint)
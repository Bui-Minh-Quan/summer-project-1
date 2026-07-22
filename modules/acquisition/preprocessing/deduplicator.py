import hashlib
from models.document import Document
from repository.mongodb import MongoRepository

class DocumentDeduplicator:
    """Computes deterministic document fingerprints and manages deduplication."""

    @staticmethod
    def fingerprint(document: Document) -> str:
        # Create a deterministic string from title and source
        text = (document.title or "") + "|" + (document.source or "")
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
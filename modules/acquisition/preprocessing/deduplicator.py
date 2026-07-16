# simple duplicate detector

import hashlib

from models.document import Document

class DocumentDeduplicator:
    # Computes deterministic document figerprints

    @staticmethod
    def fingerprint(document: Document) -> str:
        text = (document.title or "") + "|" + (document.source or "")

        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    @staticmethod 
    def is_duplicate(document: Document, existing_hashes: set[str]) -> bool:
        fingerprint = DocumentDeduplicator.fingerprint(document)

        return fingerprint in existing_hashes

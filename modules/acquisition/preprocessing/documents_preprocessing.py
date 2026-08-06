import hashlib
import re
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from modules.acquisition.models.document import Document, DocumentType, Language
from modules.acquisition.repository.mongodb import MongoRepository

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


class DocumentCleaner:
    # Basic cleaner for textual documents.

    def clean(self, document: Document) -> Document:
        if document.content:
            document.content = self._clean_html(document.content)

        if document.title:
            document.title = self._clean_html(document.title)

        return document

    @staticmethod
    def _clean_html(text: str) -> str:
        # Remove HTML tags and normalize whitespace

        soup = BeautifulSoup(text, "html.parser")

        text = soup.get_text(separator=" ")

        text = re.sub(r"\s+", " ", text)

        return text.strip()


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


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


class DocumentValidator:
    REQUIRED_FIELDS: ClassVar[list[str]] = ["title", "content", "source"]

    def validate(self, document: Document) -> ValidationResult:
        errors = []

        # Required fields
        if document.document_type == DocumentType.NEWS and not document.title:
            errors.append("Missing title for news article.")

        if not document.content:
            errors.append("Missing content.")

        if not document.source:
            errors.append("Missing source.")

        # Date
        if document.published_at and document.published_at > datetime.now(timezone.utc):
            errors.append("Publication date is in the future.")

        # Language
        if document.language.value not in {
            Language.VI.value,
            Language.EN.value,
            Language.UNKNOWN.value,
        }:
            errors.append("Unsupported language.")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

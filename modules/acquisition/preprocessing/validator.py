from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar

from models.document import Document, DocumentType, Language


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
        if document.language.value not in {Language.VI.value, Language.EN.value, Language.UNKNOWN.value}:
            errors.append("Unsupported language.")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
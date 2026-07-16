# Basic document validator

from dataclasses import dataclass
from datetime import datetime

from models.document import Document, Language


@dataclass
class ValidationResult:
    valid: bool 
    errors: list[str]

class DocumentValidator:
    # Performs lightweight validation
    REQUIRED_FIELDS = [
        "title",
        "content",
        "source"
    ]

    def validate(self, document: Document) -> ValidationResult:
        errors = []

        # Required fields
        if not document.title:
            errors.append("Missing title.")
        
        if not document.content:
            errors.append("Missing content.")

        if not document.source:
            errors.append("Mssing source.")
        
        # Date

        if document.published_at:
            if document.published_at > datetime.utcnow():
                errors.appen("Publication date is in the future")

        
        # Language
        if document.language.value not in {Language.VI.value, Language.EN.value, Language.UNKNOWN.value}:
            errors.append("Unsupported language")
        

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
    




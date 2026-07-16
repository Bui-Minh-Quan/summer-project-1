from dataclasses import dataclass
from datetime import datetime, timezone
from models.document import Document, Language

@dataclass
class ValidationResult:
    valid: bool 
    errors: list[str]

class DocumentValidator:
    REQUIRED_FIELDS = ["title", "content", "source"]

    def validate(self, document: Document) -> ValidationResult:
        errors = []

        # Required fields
        if not document.title:
            errors.append("Missing title.")
        
        if not document.content:
            errors.append("Missing content.")

        if not document.source:
            errors.append("Missing source.")  # Fixed: Mssing -> Missing
        
        # Date
        if document.published_at:
            if document.published_at > datetime.now(timezone.utc):
                errors.append("Publication date is in the future.") # Fixed: appen -> append
        
        # Language
        if document.language.value not in {Language.VI.value, Language.EN.value, Language.UNKNOWN.value}:
            errors.append("Unsupported language.")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
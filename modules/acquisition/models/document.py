""" 
Canonical document model for Financial AI Platform

Every textual data source must be converted into this schema before entering the pipeline.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

# ----------------------------------------------------------------------
# Enumerations
# ----------------------------------------------------------------------
class DocumentType(str, Enum):
    NEWS = "news"
    POST = "post"
    REPORT = "report"
    ANNOUNCEMENT = "announcement"
    MACRO = "macro"
    OTHER = "other"

class Language(str, Enum):
    VI = "vi"
    EN = "en"
    UNKNOWN = "unknown"

# ----------------------------------------------------------------------
# Canonical Document
# ----------------------------------------------------------------------

class Document(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    # Identity
    id: str = Field(description="Unique document identifier")
    source: str = Field(description="Source provider")

    fingerprint: str | None = Field(
        default=None,
        description="SHA-256 deterministic content hash for deduplication"
    )

    url: str | None = Field(
        default=None,
        description="Original document url"
    )

    # Content
    title: str | None = None 
    content: str | None = None 
    raw_html: str | None = Field(
        default=None,
        description="Original HTML before cleaning"
    )

    # Metadata
    author: str | None = None 
    language: Language = Language.UNKNOWN 
    document_type: DocumentType = DocumentType.OTHER

    symbols: list[str] = Field(
        default_factory=list,
        description="Mentioned stock symbol"
    )

    # Time 
    published_at: datetime | None = None 
    
    retrieved_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    description="When this document was fetched"
    )

    # Processing
    quality_score: float | None = None 
    metadata: dict[str, Any] = Field(
        default_factory=dict, 
        description="Connector-specific metadata"
    )



class RawDocument(BaseModel):
    id: str 
    source: str 
    document_type: DocumentType
    fetched_at: datetime
    payload: dict[str, Any]

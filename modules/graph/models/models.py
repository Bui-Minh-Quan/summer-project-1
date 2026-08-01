"""
Pydantic schemas for Module 3 Graph Building and Neo4j hydration.
"""

from pydantic import BaseModel, ConfigDict, Field


class CanonicalNode(BaseModel):
    """Canonical representation of a graph entity node."""

    canonical_id: str = Field(description="Deterministic SHA-256 hash of type + normalized name")
    name: str = Field(description="Normalized entity name")
    entity_type: str = Field(description="Broad category of the entity (e.g., STOCK, SECTOR)")


class CanonicalEdge(BaseModel):
    """Canonical representation of a directed graph relationship ready for Cypher UNWIND batching."""

    edge_id: str = Field(description="Deterministic SHA-256 edge identifier")
    doc_id: str = Field(description="Source document identifier")

    # Subject Node
    subject_id: str
    subject_name: str
    subject_type: str

    # Relation / Predicate
    relation: str = Field(description="Verb phrase or action description")
    market_impact: str = Field(description="POSITIVE, NEGATIVE, or NEUTRAL")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(description="Chain-of-thought justification text")

    # Object Node
    object_id: str
    object_name: str
    object_type: str

    # Temporal anchor for TRR decay
    published_at: str = Field(description="ISO-8601 formatted timestamp string for Neo4j datetime()")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class GraphIngestionBatch(BaseModel):
    """Batch wrapper holding multiple canonical edges ready for Neo4j UNWIND transactions."""

    edges: list[CanonicalEdge] = Field(default_factory=list)
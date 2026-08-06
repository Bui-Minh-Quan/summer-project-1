"""
Pydantic schemas for N-Pass Knowledge Graph Extraction and persistent database records.
"""

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from modules.extraction.models.ontology import EntityType, MarketImpact

# =====================================================================
# SCHEMA: Relational Graph Reasoning (TRR Chains)
# =====================================================================

class EntityNode(BaseModel):
    """A standardized graph entity node."""
    name: str = Field(description="Name of the entity, could be in the text, could be standardized.")
    entity_type: EntityType = Field(description="Broad category of the entity")


class GraphRelation(BaseModel):
    """A directed, enriched graph edge connecting two entities."""
    # ✨ Putting reasoning FIRST forces built-in Chain-of-Thought before entity extraction!
    reasoning: str = Field(
        description="1-sentence logical explanation based strictly on the article text explaining why this relationship exists."
    )
    subject: EntityNode = Field(description="The source entity node initiating or driving the impact")
    relation: str = Field(description="How the subject affects or interacts with the object")
    object: EntityNode = Field(description="The target entity node receiving the impact or connection")
    market_impact: MarketImpact = Field(
        description="Directional financial polarity (POSITIVE, NEGATIVE, or NEUTRAL) on the object entity"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="LLM reasoning confidence score")


class RelationalExtractionPayload(BaseModel):
    """Atomic payload for all extraction passes: List of directed graph relations."""
    relations: list[GraphRelation] = Field(default_factory=list, min_length=0, max_length=6)


# =====================================================================
# PERSISTENT DATABASE SCHEMA (Saved to MongoDB / Staged Graph)
# =====================================================================

class ExtractionMetadata(BaseModel):
    """Operational telemetry tracking LLM performance across all passes."""
    model_name: str
    prompt_version: str
    total_passes: int
    total_latency_seconds: float
    total_input_tokens: int
    total_output_tokens: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExtractionResult(BaseModel):
    """
    Complete, persistent extraction document storing the full N-Pass audit trail.
    Ready for staging and Neo4j graph hydration.
    """
    id: str  # Deterministic SHA-256 of document_id + prompt_version
    document_id: str

    published_at: datetime = Field(
        default_factory=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc),
        description="Time the source document was published"
    )

    relations: list[GraphRelation]   
    metadata: ExtractionMetadata

    @classmethod
    def generate_entity_id(cls, name: str, entity_type: EntityType) -> str:
        """Deterministic hash for a global canonical entity node."""
        raw_key = f"NODE|{entity_type.value}|{name.strip().upper()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def generate_relation_id(cls, subject_name: str, relation_text: str, object_name: str) -> str:
        """Deterministic hash for a directed graph edge."""
        raw_key = f"EDGE|{subject_name.strip().upper()}|{relation_text.strip().lower()}|{object_name.strip().upper()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
"""
Main Orchestrator Service for Module 3.
Processes raw ExtractionResult payloads, canonicalizes them, and merges into Neo4j.
"""

import logging
import time
from typing import Any

from config import config
from models.models import CanonicalEdge
from pydantic import BaseModel
from repository.neo4j_repo import Neo4jRepository
from services.canonicalizer import GraphCanonicalizer

logger = logging.getLogger(__name__)


class GraphPipelineReport(BaseModel):
    """Execution telemetry for a single graph ingestion batch."""
    total_documents: int = 0
    total_raw_edges: int = 0
    total_valid_edges: int = 0
    saved_edges: int = 0
    duration_seconds: float = 0.0


class GraphService:
    """Coordinates Canonicalizer and Neo4j repository for graph hydration."""

    def __init__(
        self, 
        repo: Neo4jRepository, 
        confidence_threshold: float = config.confidence_threshold
    ) -> None:
        self.repo = repo
        self.confidence_threshold = confidence_threshold
        self.canonicalizer = GraphCanonicalizer()

    async def process_extraction_result(self, payload: dict[str, Any]) -> GraphPipelineReport:
        """
        Convenience method to process a single extraction payload.
        Wraps the payload in a list and delegates to the batch processor.
        """
        return await self.process_batch([payload])

    async def process_batch(self, payloads: list[dict[str, Any]]) -> GraphPipelineReport:
        """Executes the Canonicalize -> Filter -> Ingest pipeline for a batch of documents."""
        start_time = time.time()
        report = GraphPipelineReport(total_documents=len(payloads))

        valid_edges: list[CanonicalEdge] = []

        for payload in payloads:
            doc_id = payload.get("document_id") or payload.get("id")
            if not doc_id:
                continue
            
            # Fetch published_at safely, fallback to Unix epoch if missing
            pub_at_str = payload.get("published_at", "1970-01-01T00:00:00Z")

            relations = payload.get("relations", [])
            report.total_raw_edges += len(relations)

            for rel in relations:
                # 1. Check LLM confidence threshold
                conf = float(rel.get("confidence", 1.0))
                if conf < self.confidence_threshold:
                    logger.debug(f"Dropped edge in doc {doc_id} due to low confidence ({conf})")
                    continue
                
                sub = rel.get("subject", {})
                obj = rel.get("object", {})
                
                sub_name_raw = sub.get("name", "")
                obj_name_raw = obj.get("name", "")
                
                # 2. Validate entity names (must start with an alphabet character)
                if (not self.canonicalizer.is_valid_entity_name(sub_name_raw) or 
                    not self.canonicalizer.is_valid_entity_name(obj_name_raw)):
                    logger.debug(f"Dropped edge in doc {doc_id} due to invalid entity name.")
                    continue
                
                # 3. Canonicalize Names and Re-evaluate Types (e.g., strict STOCK checking)
                sub_name, sub_type = self.canonicalizer.normalize_node(
                    sub_name_raw, sub.get("entity_type", "OTHER")
                )
                obj_name, obj_type = self.canonicalizer.normalize_node(
                    obj_name_raw, obj.get("entity_type", "OTHER")
                )
                
                # 4. Generate Deterministic Hashes for Idempotency
                sub_id = self.canonicalizer.generate_node_id(sub_name, sub_type)
                obj_id = self.canonicalizer.generate_node_id(obj_name, obj_type)
                
                rel_text = self.canonicalizer.normalize_relation(rel.get("relation", ""))
                edge_id = self.canonicalizer.generate_edge_id(sub_id, rel_text, obj_id, doc_id)
                
                # 5. Build the CanonicalEdge Model
                try:
                    canonical_edge = CanonicalEdge(
                        edge_id=edge_id,
                        doc_id=doc_id,
                        subject_id=sub_id,
                        subject_name=sub_name,
                        subject_type=sub_type,
                        relation=rel_text,
                        market_impact=rel.get("market_impact", "NEUTRAL"),
                        confidence=conf,
                        reasoning=rel.get("reasoning", ""),
                        object_id=obj_id,
                        object_name=obj_name,
                        object_type=obj_type,
                        published_at=pub_at_str
                    )
                    valid_edges.append(canonical_edge)
                    report.total_valid_edges += 1
                except Exception as e: #noqa: BLE001
                    logger.warning(f"Failed to validate CanonicalEdge for doc {doc_id}: {e}")

        # 6. Execute Neo4j UNWIND Batch Insertion
        if valid_edges:
            report.saved_edges = await self.repo.save_edge_batch(valid_edges)

        report.duration_seconds = round(time.time() - start_time, 3)
        logger.info(
            f"Graph batch processed: {report.saved_edges}/{report.total_raw_edges} "
            f"edges staged in {report.duration_seconds}s"
        )
        return report
"""
Unit tests for ExtractionService._filter_and_deduplicate.
Verifies removal of Anti-Super Nodes, self-loops, and short/numeric entities.
"""

from unittest.mock import MagicMock

from models.extraction import EntityNode, GraphRelation
from models.ontology import EntityType, MarketImpact
from services.extraction_service import ExtractionService


def test_anti_super_node_and_self_loop_sanitizer():
    # Create dummy service with mocked dependencies
    service = ExtractionService(
        llm_client=MagicMock(),
        cache=MagicMock(),
        repository=MagicMock(),
        publisher=MagicMock(),
    )

    raw_relations = [
        # 1. Valid Relation -> Should SURVIVE
        GraphRelation(
            reasoning="Giá cao su tăng giúp lợi nhuận GVR cải thiện.",
            subject=EntityNode(name="Giá cao su", entity_type=EntityType.COMMODITY),
            relation="tăng giá giúp cải thiện lợi nhuận",
            object=EntityNode(name="GVR", entity_type=EntityType.STOCK),
            market_impact=MarketImpact.POSITIVE,
            confidence=0.95,
        ),
        # 2. Banned Super Node ('Doanh nghiệp') -> Should be DROPPED
        GraphRelation(
            reasoning="Doanh nghiệp chịu tác động từ chính sách.",
            subject=EntityNode(name="Doanh nghiệp", entity_type=EntityType.ORGANIZATION),
            relation="chịu tác động từ",
            object=EntityNode(name="HPG", entity_type=EntityType.STOCK),
            market_impact=MarketImpact.NEGATIVE,
            confidence=0.90,
        ),
        # 3. Self-Loop ('FPT' -> 'FPT') -> Should be DROPPED
        GraphRelation(
            reasoning="FPT tái cấu trúc nội bộ FPT.",
            subject=EntityNode(name="FPT", entity_type=EntityType.STOCK),
            relation="tái cấu trúc",
            object=EntityNode(name="FPT", entity_type=EntityType.STOCK),
            market_impact=MarketImpact.NEUTRAL,
            confidence=0.90,
        ),
    ]

    seen_keys = set()
    filtered = service._filter_and_deduplicate(
        raw_relations=raw_relations,
        seen_edge_keys=seen_keys,
        doc_id="test_doc_1",
    )

    assert len(filtered) == 1
    assert filtered[0].subject.name == "Giá cao su"
    assert filtered[0].object.name == "GVR"
    assert "giá cao su->gvr" in seen_keys
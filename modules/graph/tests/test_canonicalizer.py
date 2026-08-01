"""
Unit tests for GraphCanonicalizer entity validation, stock normalization, and hashing.
"""

from services.canonicalizer import GraphCanonicalizer


def test_is_valid_entity_name() -> None:
    # Valid names starting with alphabetic characters
    assert GraphCanonicalizer.is_valid_entity_name("FPT") is True
    assert GraphCanonicalizer.is_valid_entity_name("Vinhomes") is True
    assert GraphCanonicalizer.is_valid_entity_name("Ngân hàng Nhà nước") is True

    # Invalid names starting with numbers or symbols
    assert GraphCanonicalizer.is_valid_entity_name("12 people") is False
    assert GraphCanonicalizer.is_valid_entity_name("1. Antony") is False
    assert GraphCanonicalizer.is_valid_entity_name("@Joe") is False
    assert GraphCanonicalizer.is_valid_entity_name("   ") is False
    assert GraphCanonicalizer.is_valid_entity_name("") is False


def test_normalize_node_stock_rules() -> None:
    # Valid VN30 stocks should be uppercased and kept as STOCK
    name, entity_type = GraphCanonicalizer.normalize_node("fpt", "STOCK")
    assert name == "FPT"
    assert entity_type == "STOCK"

    name, entity_type = GraphCanonicalizer.normalize_node("  vic  ", "STOCK")
    assert name == "VIC"
    assert entity_type == "STOCK"

    # Invalid/unrecognized stocks should be downgraded to OTHER
    name, entity_type = GraphCanonicalizer.normalize_node("fpt corporation", "STOCK")
    assert name == "Fpt corporation"
    assert entity_type == "OTHER"


def test_normalize_relation() -> None:
    # Should strip whitespace, lowercase, and remove trailing punctuation
    assert GraphCanonicalizer.normalize_relation("  Tăng Lãi Suất.  ") == "tăng lãi suất"
    assert GraphCanonicalizer.normalize_relation("đầu tư vào...") == "đầu tư vào"


def test_deterministic_hashes() -> None:
    # Lowercase variant should produce exact same hash
    h1 = GraphCanonicalizer.generate_node_id("FPT", "STOCK")
    h2 = GraphCanonicalizer.generate_node_id("fpt", "STOCK")
    assert h1 == h2

    # Edge hash idempotency
    e1 = GraphCanonicalizer.generate_edge_id("sub1", "TĂNG GIÁ.", "obj1", "doc101")
    e2 = GraphCanonicalizer.generate_edge_id("sub1", "tăng giá", "obj1", "doc101")
    assert e1 == e2
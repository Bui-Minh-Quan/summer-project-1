"""
Ontology Enums for Financial Knowledge Graph Extraction.
Designed for N-Pass Temporal Relational Reasoning (TRR).
"""

from enum import Enum


class EntityType(str, Enum):
    """General classification types for market entities."""
    ORGANIZATION = "ORGANIZATION"  # Covers corporations, banks, government bodies, startups
    STOCK = "STOCK"                # Explicit stock tickers / tradable equities
    SECTOR = "SECTOR"              # Broad industry groups (e.g., Real Estate, Banking, Steel)
    PERSON = "PERSON"              # Executives, ministers, investors
    COMMODITY = "COMMODITY"        # Gold, oil, steel, agricultural products
    INDEX = "INDEX"                # VN30, VN-Index, S&P 500
    OTHER = "OTHER"                # Fallback for macro indicators, currencies, etc.


class MarketImpact(str, Enum):
    """Directional financial impact polarity for portfolio reasoning."""
    POSITIVE = "POSITIVE"  # Positive impact (e.g., revenue growth, competitor stumble, policy support)
    NEGATIVE = "NEGATIVE"  # Negative impact (e.g., profit warning, supply shock, tax hike)
    NEUTRAL = "NEUTRAL"    # Factual or structural association without direct directional bias
"""
Pydantic data models for Module 2 Feature Engineering.
Includes payload schemas for incoming market data and output Gold Feature Vectors.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MarketQuoteInput(BaseModel):
    """Input payload schema parsing messages from Module 1's 'market-ohlcv' Kafka topic."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    resolution: str = "1D"
    source: str = "vnstock"

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class MarketSentimentFeatureVector(BaseModel):
    """Gold Layer: Unified daily feature vector combining technical price action and social sentiment."""
    id: str | None = None  # Compound key: f"{symbol}_{date_str}"
    symbol: str
    date: str  # YYYY-MM-DD format for exact daily bucket alignment
    timestamp: datetime  # UTC midnight timestamp for indexing

    # Stream 1: Market & Price Action Features
    close_price: float = 0.0
    daily_return: float = 0.0
    intraday_volatility: float = 0.0
    volume_ratio: float = 1.0  # Current volume vs. 20-day moving average
    has_market_data: bool = False

    # Stream 2: Social Attention & Engagement Metrics
    post_count: int = 0
    total_likes: int = 0
    total_replies: int = 0
    total_shares: int = 0
    total_engagement: int = 0

    # Stream 2: Sentiment Polarity Tallies
    positive_posts: int = 0
    negative_posts: int = 0
    neutral_posts: int = 0
    sentiment_sum: float = 0.0

    # Derived Quantified Sentiment Features
    mean_sentiment: float = 0.0  # sentiment_sum / post_count
    net_sentiment_score: float = 0.0  # (pos - neg) / post_count
    sentiment_price_divergence: float = 0.0  # Highlights retail hype vs. price movement

    # NEW: Track processed posts to prevent double-counting math
    processed_document_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
"""
Pydantic data models for numeric market data.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class RawMarketQuote(BaseModel):
    """Bronze Layer: Raw OHLCV bar as received directly from the data provider."""

    ticker: str
    timestamp: datetime | str

    open_price: float = Field(alias="open")
    high_price: float = Field(alias="high")
    low_price: float = Field(alias="low")
    close_price: float = Field(alias="close")

    volume: float

    resolution: str = "1D"
    source: str = "vnstock"

    raw_payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


class MarketQuote(BaseModel):
    """Silver Layer: Canonical, validated OHLCV bar ready for storage and Kafka transmission."""
    id: str | None = None  # Canonical unique ID for MongoDB _id and Kafka routing key
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    resolution: str
    source: str
    fingerprint: str | None = None

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()
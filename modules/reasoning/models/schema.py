"""
Data contracts and schemas for the Reasoning Engine.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    SIDEWAYS = "Sideways"


class ReasoningRequest(BaseModel):
    """Payload received from the client or internal trigger."""
    symbol: str = Field(..., description="Target stock ticker, e.g., FPT")
    date: datetime = Field(
        default_factory=datetime.utcnow, 
        description="The target date to anchor reasoning (to prevent lookahead bias)"
    )


class MarketData(BaseModel):
    """Structure for recent price history injected into the prompt."""
    date: str
    close: float
    volume: float
    daily_return: float


class ReasoningResponse(BaseModel):
    """
    Strict output schema enforced on the LLM.
    """
    symbol: str = Field(..., description="The stock symbol analyzed")
    target_date: str = Field(..., description="The date the reasoning applies to")
    trend: TrendDirection = Field(..., description="Predicted directional trend")
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the reasoning between 0.0 and 1.0"
    )
    reasoning: str = Field(
        ..., 
        description="A concise, logical justification summarizing graph catalysts and market context."
    )
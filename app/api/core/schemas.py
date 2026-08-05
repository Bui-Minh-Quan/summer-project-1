from datetime import datetime

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="Target stock ticker, e.g., FPT")
    date: datetime | None = Field(
        default=None,
        description="Target date for prediction. Defaults to current UTC time if omitted."
    )

class HorizonPrediction(BaseModel):
    horizon_days: int
    expected_return_pct: float
    expected_price: float

class DualPredictionResponse(BaseModel):
    symbol: str
    target_date: str
    current_price: float
    trend: str
    confidence: float
    reasoning: str
    price_forecasts: list[HorizonPrediction]

class ClassificationRecord(BaseModel):
    date: str
    price: float
    predicted_trend: str
    actual_trend: str | None
    reasoning: str | None
    model: str


class RegressionRecord(BaseModel):
    date: str
    price: float
    predicted_price_t1: float
    predicted_price_t2: float
    predicted_price_t3: float
    predicted_price_t4: float
    predicted_price_t5: float
    actual_price_t1: float | None
    actual_price_t2: float | None
    actual_price_t3: float | None
    actual_price_t4: float | None
    actual_price_t5: float | None
    model: str
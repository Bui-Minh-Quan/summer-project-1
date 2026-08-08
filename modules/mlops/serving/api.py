"""
FastAPI Serving Engine for Multi-Horizon Classification & Regression Models.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

import mlflow
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from modules.mlops.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mlops_serving_api")

# Model Registry Cache
production_cls_models: dict[int, Any] = {}
production_reg_models: dict[int, Any] = {}


def ensure_models_trained():
    """Auto-trains and promotes baseline models if MLflow has no @production models."""
    mlflow.set_tracking_uri(config.mlflow_tracking_uri)
    client = mlflow.tracking.MlflowClient()

    # Check if t+1 model exists
    try:
        client.get_model_version_by_alias("VN30_Trend_Classifier_t1", "production")
        logger.info("✅ Existing @production models detected in MLflow.")
    except Exception: # noqa: BLE001
        logger.warning("⚠️ No @production models found. Running automatic bootstrap pipeline (Extract -> Train -> Promote)...")
        try:
            extract_gold_features()
            train_all_models()
            evaluate_and_promote_all()
            logger.info("🎉 Automatic model bootstrapping completed!")
        except Exception as e: # noqa: BLE001
            logger.error(f"❌ Auto-training failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-bootstraps models if needed, then loads @production models on startup."""
    mlflow.set_tracking_uri(config.mlflow_tracking_uri)

    # 1. Automatically train baseline models if database is fresh
    ensure_models_trained()

    # 2. Load production models
    for h in config.target_horizons:
        try:
            cls_name = f"VN30_Trend_Classifier_t{h}"
            production_cls_models[h] = mlflow.xgboost.load_model(f"models:/{cls_name}@production")
            logger.info(f"✅ Loaded @production for {cls_name}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"⚠️ Could not load @production for {cls_name}: {e}")

        try:
            reg_name = f"VN30_Return_Regressor_t{h}"
            production_reg_models[h] = mlflow.xgboost.load_model(f"models:/{reg_name}@production")
            logger.info(f"✅ Loaded @production for {reg_name}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"⚠️ Could not load @production for {reg_name}: {e}")

    yield
    logger.info("Shutting down Serving API...")


app = FastAPI(
    title="Financial AI Platform - Stock Prediction API",
    version="1.0.0",
    lifespan=lifespan,
)


class PredictionRequest(BaseModel):
    symbol: str = Field(..., json_schema_extra={"example": "FPT"})
    horizon: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Prediction horizon in trading days (1-5)",
    )
    close_price: float = Field(..., json_schema_extra={"example": 120.5})
    daily_return: float = Field(..., json_schema_extra={"example": 0.015})
    intraday_volatility: float = Field(..., json_schema_extra={"example": 0.02})
    volume_ratio: float = Field(..., json_schema_extra={"example": 1.1})
    post_count: int = Field(default=0, json_schema_extra={"example": 25})
    total_engagement: int = Field(default=0, json_schema_extra={"example": 150})
    mean_sentiment: float = Field(default=0.0, json_schema_extra={"example": 0.25})
    net_sentiment_score: float = Field(default=0.0, json_schema_extra={"example": 0.3})
    sentiment_price_divergence: float = Field(default=0.0, json_schema_extra={"example": -0.05})


class PredictionResponse(BaseModel):
    symbol: str
    horizon_days: int
    predicted_trend_class: int
    predicted_trend_label: str
    trend_probabilities: dict[str, float]
    predicted_return_pct: float


LABEL_MAP = {0: "Bearish", 1: "Sideways", 2: "Bullish"}


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "loaded_cls_horizons": list(production_cls_models.keys()),
        "loaded_reg_horizons": list(production_reg_models.keys()),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    h = request.horizon

    cls_model = production_cls_models.get(h)
    reg_model = production_reg_models.get(h)

    if not cls_model or not reg_model:
        raise HTTPException(
            status_code=503,
            detail=f"Production models for horizon t+{h} are not fully loaded.",
        )

    feature_vector = np.array([[
        request.close_price,
        request.daily_return,
        request.intraday_volatility,
        request.volume_ratio,
        request.post_count,
        request.total_engagement,
        request.mean_sentiment,
        request.net_sentiment_score,
        request.sentiment_price_divergence,
    ]])

    try:
        # Run Classification
        raw_pred_cls = cls_model.predict(feature_vector)[0]
        probs = cls_model.predict_proba(feature_vector)[0]
        pred_class = int(raw_pred_cls)

        # Run Regression
        pred_return = float(reg_model.predict(feature_vector)[0])

        return PredictionResponse(
            symbol=request.symbol.upper(),
            horizon_days=h,
            predicted_trend_class=pred_class - 1,
            predicted_trend_label=LABEL_MAP.get(pred_class, "Unknown"),
            trend_probabilities={
                "Bearish": float(probs[0]),
                "Sideways": float(probs[1]),
                "Bullish": float(probs[2]),
            },
            predicted_return_pct=round(pred_return, 4),
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference error: {e!s}")
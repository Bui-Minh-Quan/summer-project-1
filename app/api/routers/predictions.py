import asyncio
import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi_cache.decorator import cache

from app.api.core.config import settings
from app.api.core.schemas import (
    ClassificationRecord,
    DualPredictionResponse,
    HorizonPrediction,
    RegressionRecord,
)

logger = logging.getLogger("predictions_router")
logger.setLevel(logging.INFO)

router = APIRouter()

# ============================================================================
# CUSTOM CACHE KEY BUILDERS
# ============================================================================

def prediction_key_builder(
    func,
    namespace: str = "",
    request: Request | None = None,
    response: Response | None = None,
    args: tuple = (),
    kwargs: dict | None = None,
) -> str:
    """Generates a deterministic Redis key based on stock ticker and hourly date bucket."""
    try:
        kwargs = kwargs or {}
        symbol = str(kwargs.get("symbol", "UNKNOWN")).upper()
        target_dt: datetime | None = kwargs.get("date")
        
        date_part = target_dt.strftime("%Y-%m-%d-%H") if target_dt else datetime.now(UTC).strftime("%Y-%m-%d-%H")
        cache_key = f"api-cache:predictions:{symbol}:{date_part}"
        logger.info(f"🔑 [Cache Key Built] Key: '{cache_key}' (Symbol: {symbol}, DateBucket: {date_part})")
        return cache_key
    except Exception:
        logger.exception("❌ [Cache Key Builder Failed]")
        return f"api-cache:predictions:fallback:{datetime.now(UTC).timestamp()}"


def backtest_key_builder(
    func,
    namespace: str = "",
    request: Request | None = None,
    response: Response | None = None,
    args: tuple = (),
    kwargs: dict | None = None,
) -> str:
    """Generates a deterministic Redis key for backtest audit logs."""
    try:
        kwargs = kwargs or {}
        symbol = str(kwargs.get("symbol", "UNKNOWN")).upper()
        model = str(kwargs.get("model", "all"))
        page = kwargs.get("page", 1)
        limit = kwargs.get("limit", 50)
        endpoint = func.__name__
        cache_key = f"api-cache:backtest:{endpoint}:{symbol}:{model}:{page}:{limit}"
        logger.info(f"🔑 [Backtest Cache Key Built] Key: '{cache_key}'")
        return cache_key
    except Exception:
        logger.exception("❌ [Backtest Cache Key Builder Failed]")
        return f"api-cache:backtest:fallback:{datetime.now(UTC).timestamp()}"


# ============================================================================
# SERVICE HELPERS
# ============================================================================

async def fetch_mlops_prediction(symbol: str, features: dict, horizon: int) -> dict:
    """Calls the internal XGBoost MLOps service."""
    payload = {"symbol": symbol.upper(), "horizon": horizon, **features}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.MLOPS_API_URL}/predict", json=payload)
        response.raise_for_status()
        return response.json()


async def fetch_reasoning(symbol: str, target_date: datetime) -> dict:
    """Calls the internal vLLM Reasoning TRR service with the anchored date."""
    payload = {"symbol": symbol.upper(), "date": target_date.isoformat()}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{settings.REASONING_API_URL}/analyze", json=payload)
        response.raise_for_status()
        return response.json()


# ============================================================================
# ROUTER ENDPOINTS
# ============================================================================

@router.get("/{symbol}", response_model=DualPredictionResponse)
@cache(expire=43200, key_builder=prediction_key_builder)
async def get_dual_prediction(
    symbol: str, 
    request: Request,
    date: datetime | None = Query(None, description="Target date for prediction. Defaults to current UTC time if omitted.")
):
    symbol = symbol.upper()
    logger.info(f"🚨 [CACHE MISS / EXECUTING ENGINES] Running fresh dual prediction for symbol '{symbol}'...")
    
    db = request.app.state.db
    target_dt = date or datetime.now(UTC)

    # 1. Fetch feature record from gold_market_features on or before target_dt
    feature_doc = await db["gold_market_features"].find_one(
        {"symbol": symbol, "timestamp": {"$lte": target_dt}},
        sort=[("timestamp", -1)]
    )

    if not feature_doc:
        feature_doc = await db["gold_market_features"].find_one(
            {"symbol": symbol},
            sort=[("timestamp", -1)]
        )

    if not feature_doc:
        logger.error(f"❌ Stock features not found for ticker '{symbol}'")
        raise HTTPException(status_code=404, detail=f"No feature records found for stock {symbol}")

    base_price = float(feature_doc.get("close_price", 0.0))
    if base_price <= 0:
        raise HTTPException(status_code=400, detail=f"Invalid close price ({base_price}) for stock {symbol}")

    features = {
        "close_price": base_price,
        "daily_return": feature_doc.get("daily_return", 0.0),
        "intraday_volatility": feature_doc.get("intraday_volatility", 0.0),
        "volume_ratio": feature_doc.get("volume_ratio", 1.0),
        "post_count": feature_doc.get("post_count", 0),
        "total_engagement": feature_doc.get("total_engagement", 0),
        "mean_sentiment": feature_doc.get("mean_sentiment", 0.0),
        "net_sentiment_score": feature_doc.get("net_sentiment_score", 0.0),
        "sentiment_price_divergence": feature_doc.get("sentiment_price_divergence", 0.0),
    }

    # 2. Concurrently request MLOps Regressor (t+1..t+5) and vLLM TRR Reasoning
    mlops_tasks = [fetch_mlops_prediction(symbol, features, h) for h in range(1, 6)]
    try:
        results = await asyncio.gather(*mlops_tasks, fetch_reasoning(symbol, target_dt))
    except Exception as e:  # noqa: BLE001
        logger.error(f"❌ Internal prediction service failure: {e}")
        raise HTTPException(status_code=500, detail=f"Internal prediction service failure: {e!s}")

    mlops_results = results[:-1]
    reasoning_result = results[-1]

    # 3. Calculate expected target prices
    forecasts = []
    for res in mlops_results:
        ret_pct = res["predicted_return_pct"]
        expected_price = base_price * (1.0 + ret_pct)
        forecasts.append(
            HorizonPrediction(
                horizon_days=res["horizon_days"],
                expected_return_pct=ret_pct,
                expected_price=round(expected_price, 2)
            )
        )

    # 4. Construct response payload
    final_response = DualPredictionResponse(
        symbol=symbol,
        target_date=reasoning_result["target_date"],
        current_price=base_price,
        trend=reasoning_result["trend"],
        confidence=reasoning_result["confidence"],
        reasoning=reasoning_result["reasoning"],
        price_forecasts=forecasts
    )

    # 5. Log separate Classification and Regression records for backtesting
    now_utc = datetime.now(UTC)

    classification_log = {
        "symbol": symbol,
        "type": "classification",
        "model": "vLLM-TRR",
        "target_date": reasoning_result["target_date"],
        "current_price": base_price,
        "trend": reasoning_result["trend"],
        "confidence": reasoning_result["confidence"],
        "reasoning": reasoning_result["reasoning"],
        "actual_trend": None,
        "timestamp": now_utc
    }

    regression_log = {
        "symbol": symbol,
        "type": "regression",
        "model": "XGBoost-Regressor",
        "target_date": reasoning_result["target_date"],
        "current_price": base_price,
        "price_forecasts": [f.model_dump() for f in forecasts],
        "actual_price_t1": None,
        "actual_price_t2": None,
        "actual_price_t3": None,
        "actual_price_t4": None,
        "actual_price_t5": None,
        "timestamp": now_utc
    }

    await db["predictions_log"].insert_many([classification_log, regression_log])

    logger.info(f"✅ [DUAL PREDICTION COMPLETE] Finished prediction for symbol '{symbol}'. Returning to client/cache.")
    return final_response


@router.get("/backtest/classification/{symbol}", response_model=list[ClassificationRecord])
@cache(expire=3600, key_builder=backtest_key_builder)
async def get_classification_backtest(
    symbol: str, 
    request: Request,
    model: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    db = request.app.state.db
    skip = (page - 1) * limit
    
    query = {"symbol": symbol.upper(), "type": "classification"}
    if model:
        query["model"] = model
        
    cursor = db["predictions_log"].find(query).sort("timestamp", -1).skip(skip).limit(limit)
    predictions = await cursor.to_list(length=limit)
    
    return [
        ClassificationRecord(
            date=pred.get("target_date", ""),
            price=pred.get("current_price", 0.0),
            predicted_trend=pred.get("trend", "Sideways"),
            actual_trend=pred.get("actual_trend"),
            reasoning=pred.get("reasoning"),
            model=pred.get("model", "Unknown")
        )
        for pred in predictions
    ]


@router.get("/backtest/regression/{symbol}", response_model=list[RegressionRecord])
@cache(expire=3600, key_builder=backtest_key_builder)
async def get_regression_backtest(
    symbol: str, 
    request: Request,
    model: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    db = request.app.state.db
    skip = (page - 1) * limit
    
    query = {"symbol": symbol.upper(), "type": "regression"}
    if model:
        query["model"] = model
        
    cursor = db["predictions_log"].find(query).sort("timestamp", -1).skip(skip).limit(limit)
    predictions = await cursor.to_list(length=limit)
    
    results = []
    for pred in predictions:
        forecasts = pred.get("price_forecasts", [])
        results.append(
            RegressionRecord(
                date=pred.get("target_date", ""),
                price=pred.get("current_price", 0.0),
                predicted_price_t1=forecasts[0]["expected_price"] if len(forecasts) > 0 else 0.0,
                predicted_price_t2=forecasts[1]["expected_price"] if len(forecasts) > 1 else 0.0,
                predicted_price_t3=forecasts[2]["expected_price"] if len(forecasts) > 2 else 0.0,
                predicted_price_t4=forecasts[3]["expected_price"] if len(forecasts) > 4 else 0.0,
                predicted_price_t5=forecasts[4]["expected_price"] if len(forecasts) > 5 else 0.0,
                actual_price_t1=pred.get("actual_price_t1"),
                actual_price_t2=pred.get("actual_price_t2"),
                actual_price_t3=pred.get("actual_price_t3"),
                actual_price_t4=pred.get("actual_price_t4"),
                actual_price_t5=pred.get("actual_price_t5"),
                model=pred.get("model", "Unknown")
            )
        )
    return results
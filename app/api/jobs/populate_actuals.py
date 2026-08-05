import asyncio
import logging
from datetime import datetime, timezone
from redis.asyncio import from_url as redis_from_url
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("populate_actuals_job")

# Threshold for classifying actual trend (e.g., > +1% Bullish, < -1% Bearish)
BULLISH_THRESHOLD = 0.01
BEARISH_THRESHOLD = -0.01

async def populate_actuals():
    """Finds unfulfilled prediction logs and fills in actual market prices/trends."""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]

    # Query logs where actual outcomes have not been fully populated yet
    query = {
        "$or": [
            {"actual_price_t1": None},
            {"actual_trend": None}
        ]
    }

    unfulfilled_logs = await db["predictions_log"].find(query).to_list(length=1000)
    if not unfulfilled_logs:
        logger.info("No unfulfilled prediction records found.")
        client.close()
        return

    logger.info(f"Processing {len(unfulfilled_logs)} unfulfilled prediction logs...")

    updated_count = 0
    for log in unfulfilled_logs:
        symbol = log["symbol"]
        pred_timestamp = log.get("timestamp")
        log_id = log["_id"]

        if not pred_timestamp:
            continue

        # Fetch up to 5 subsequent daily market bars strictly after the prediction timestamp
        quotes = await db["silver_market_quotes"].find({
            "symbol": symbol,
            "timestamp": {"$gt": pred_timestamp}
        }).sort("timestamp", 1).limit(5).to_list(length=5)

        if not quotes:
            # Market data for future days not yet available in silver_market_quotes
            continue

        update_fields = {}

        # 1. Populate regression actuals (actual_price_t1 through actual_price_t5)
        for idx, quote in enumerate(quotes, start=1):
            update_fields[f"actual_price_t{idx}"] = quote["close"]

        # 2. Populate classification actual trend (t+1)
        actual_t1_close = quotes[0]["close"]
        base_price = log.get("current_price") or log.get("price")

        if base_price and base_price > 0:
            actual_return = (actual_t1_close - base_price) / base_price

            if actual_return > BULLISH_THRESHOLD:
                actual_trend = "Bullish"
            elif actual_return < BEARISH_THRESHOLD:
                actual_trend = "Bearish"
            else:
                actual_trend = "Sideways"

            update_fields["actual_trend"] = actual_trend

        # Update document in predictions_log
        if update_fields:
            await db["predictions_log"].update_one(
                {"_id": log_id},
                {"$set": update_fields}
            )
            updated_count += 1

    if updated_count > 0:
        redis = redis_from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
        keys = await redis.keys("api-cache:*backtest*")
        if keys:
            await redis.delete(*keys)
        await redis.aclose()

    logger.info(f"Successfully updated {updated_count} prediction records with actual outcomes.")
    client.close()

if __name__ == "__main__":
    asyncio.run(populate_actuals())
"""
Market Data Retrieval for Reasoning Engine.
Fetches recent feature vectors to ground the LLM in quantitative reality.
"""

import logging
from datetime import datetime

from pymongo import AsyncMongoClient

from modules.reasoning.config import config
from modules.reasoning.models.schema import MarketData

logger = logging.getLogger("reasoning_market")


class MarketRepository:
    def __init__(self):
        self.client = AsyncMongoClient(config.mongo_uri)
        self.db = self.client[config.mongo_db]
        self.collection = self.db[config.mongo_collection]

    async def close(self):
        await self.client.close()

    async def get_recent_market_data(
        self, symbol: str, target_date: datetime, days_history: int = 5
    ) -> list[MarketData]:
        """
        Fetches the exact market features (close price, volume, returns) 
        for the days immediately preceding the target date.
        """
        try:
            # Query: Matches symbol and date strictly <= target_date
            cursor = self.collection.find({
                "symbol": symbol,
                "timestamp": {"$lte": target_date}
            }).sort("timestamp", -1).limit(days_history)  # Sort descending to get most recent first
            
            docs = await cursor.to_list(length=days_history)
            
            # Reverse to chronological order (oldest to newest) for the LLM prompt
            docs.reverse()
            
            market_data = []
            for doc in docs:
                market_data.append(
                    MarketData(
                        date=doc["timestamp"].strftime("%Y-%m-%d"),
                        close=float(doc.get("close_price", 0.0)),
                        volume=float(doc.get("volume_ratio", 0.0)),
                        daily_return=float(doc.get("daily_return", 0.0))
                    )
                )
            return market_data
            
        except Exception as e: #noqa: BLE001
            logger.error(f"Failed to retrieve market data for {symbol}: {e}")
            return []
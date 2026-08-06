"""
Feature Engineering Service for Module 2.
Processes market OHLCV quotes and social media posts into unified daily feature vectors.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from modules.extraction.models.features import (
    MarketQuoteInput,
    MarketSentimentFeatureVector,
)
from modules.extraction.publishers.base import BasePublisher
from modules.extraction.repository.mongodb import MongoRepository

logger = logging.getLogger(__name__)

TARGET_SYMBOLS: set[str] = {
    "FPT", "SSI", "VCB", "VHM", "HPG", "GAS", "MSN", "MWG", "GVR", "VIC",
    "ACB", "BID", "CTG", "DGC", "LPB", "MBB", "PLX", "SAB", "SHB", "SSB",
    "STB", "TCB", "TPB", "VIB", "VJC", "VNM", "VPB", "VPL", "VRE"
}


class FeatureEngineeringService:
    """Orchestrates feature calculation and stateful merging across market and document streams."""

    def __init__(
        self,
        feature_repo: MongoRepository[MarketSentimentFeatureVector],
        silver_market_repo: MongoRepository[Any],
        publisher: BasePublisher[MarketSentimentFeatureVector] | None = None,  # NEW
        output_topic: str = "gold-market-features",
    ) -> None:
        self.feature_repo = feature_repo
        self.silver_market_repo = silver_market_repo
        self.publisher = publisher            # NEW
        self.output_topic = output_topic
        self.feature_repo.collection.drop_index("id_1")
    

    def _get_doc_id(self, symbol: str, date_str: str) -> str:
        return f"{symbol.upper().strip()}_{date_str}"

    async def process_market_quote(self, quote: MarketQuoteInput) -> MarketSentimentFeatureVector | None:
        """Stream 1: Processes an incoming OHLCV quote and computes technical momentum features."""
        symbol = quote.symbol.upper().strip()
        if symbol not in TARGET_SYMBOLS:
            return None

        date_str = quote.timestamp.strftime("%Y-%m-%d")
        doc_id = self._get_doc_id(symbol, date_str)

        prior_quotes = list(
            self.silver_market_repo.collection.find(
                {"symbol": symbol, "timestamp": {"$lt": quote.timestamp}}
            ).sort("timestamp", -1).limit(20)
        )

        prior_close = prior_quotes[0]["close"] if prior_quotes else quote.open
        daily_return = (quote.close - prior_close) / prior_close if prior_close > 0 else 0.0
        intraday_vol = (quote.high - quote.low) / quote.open if quote.open > 0 else 0.0

        if prior_quotes:
            avg_vol_20d = sum(q.get("volume", 0.0) for q in prior_quotes) / len(prior_quotes)
            volume_ratio = quote.volume / avg_vol_20d if avg_vol_20d > 0 else 1.0
        else:
            volume_ratio = 1.0

        existing_data = self.feature_repo.collection.find_one({"_id": doc_id})
        # Line 38 Fix: Explicit parse using datetime class
        parsed_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        vector = MarketSentimentFeatureVector.model_validate(existing_data) if existing_data else MarketSentimentFeatureVector(
            id=doc_id,
            symbol=symbol,
            date=date_str,
            timestamp=parsed_dt,
        )

        vector.close_price = round(quote.close, 2)
        vector.daily_return = round(daily_return, 4)
        vector.intraday_volatility = round(intraday_vol, 4)
        vector.volume_ratio = round(volume_ratio, 2)
        vector.has_market_data = True
        vector.sentiment_price_divergence = self._compute_divergence(vector)

        self._save_vector(vector)
        logger.info(f"[Market Stream] Updated Feature Vector for {symbol} on {date_str} (Return: {vector.daily_return:.2%})")
        return vector

    async def process_social_post(self, payload: dict[str, Any]) -> list[MarketSentimentFeatureVector]:
        """Stream 2: Processes a social media post, filters symbols, and quantifies sentiment."""
        doc_type = payload.get("document_type") or payload.get("type")
        if str(doc_type).strip().lower() != "post":
            return []

        # Extract a unique identifier for the post
        post_id = str(payload.get("id") or payload.get("fingerprint") or "")
        if not post_id:
            return []

        raw_symbols = payload.get("symbols") or []
        matched_symbols = [s.strip().upper() for s in raw_symbols if isinstance(s, str) and s.strip().upper() in TARGET_SYMBOLS]
        if not matched_symbols:
            return []

        pub_at = payload.get("published_at")
        try:
            if isinstance(pub_at, str):
                parsed_pub_dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
            elif isinstance(pub_at, datetime):
                parsed_pub_dt = pub_at
            else:
                parsed_pub_dt = datetime.now(timezone.utc)
            date_str = parsed_pub_dt.strftime("%Y-%m-%d")
        except ValueError:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        meta = payload.get("metadata") or {}
        likes = int(meta.get("totalLikes") or 0)
        replies = int(meta.get("totalReplies") or 0)
        shares = int(meta.get("totalShares") or 0)
        raw_sentiment = float(meta.get("sentiment") or 0.0)

        sentiment_val = 1.0 if raw_sentiment > 0 else (-1.0 if raw_sentiment < 0 else 0.0)

        updated_vectors = []
        for symbol in set(matched_symbols):
            doc_id = self._get_doc_id(symbol, date_str)
            existing_data = self.feature_repo.collection.find_one({"_id": doc_id})
            
            parsed_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            vector = MarketSentimentFeatureVector.model_validate(existing_data) if existing_data else MarketSentimentFeatureVector(
                id=doc_id,
                symbol=symbol,
                date=date_str,
                timestamp=parsed_dt,
            )

            # Idempotency Check! Skip if we already did the math for this post
            if post_id in vector.processed_document_ids:
                logger.debug(f"[Idempotency] Post {post_id} already processed for {symbol} on {date_str}. Skipping.")
                continue

            vector.post_count += 1
            vector.total_likes += likes
            vector.total_replies += replies
            vector.total_shares += shares
            vector.total_engagement = vector.total_likes + vector.total_replies + vector.total_shares

            vector.sentiment_sum += sentiment_val
            if sentiment_val > 0:
                vector.positive_posts += 1
            elif sentiment_val < 0:
                vector.negative_posts += 1
            else:
                vector.neutral_posts += 1

            vector.mean_sentiment = round(vector.sentiment_sum / vector.post_count, 4)
            vector.net_sentiment_score = round((vector.positive_posts - vector.negative_posts) / vector.post_count, 4)
            vector.sentiment_price_divergence = self._compute_divergence(vector)

            vector.processed_document_ids.append(post_id)

            self._save_vector(vector)
            logger.debug(f"[Social Stream] Updated {symbol} ({date_str}) | Posts: {vector.post_count} | Net Sentiment: {vector.net_sentiment_score}")
            updated_vectors.append(vector)

        return updated_vectors

    @staticmethod
    def _compute_divergence(vec: MarketSentimentFeatureVector) -> float:
        if not vec.has_market_data or vec.post_count == 0:
            return 0.0
        return round(vec.net_sentiment_score - (vec.daily_return * 10), 4)

    def _save_vector(self, vec: MarketSentimentFeatureVector) -> None:
        doc_id = f"{vec.symbol.upper().strip()}_{vec.date}"
        vec.id = doc_id
        
        payload = vec.model_dump(by_alias=True)
        self.feature_repo.collection.update_one(
            {"_id": doc_id},
            {"$set": payload},
            upsert=True,
        )

        if self.publisher:
            self.publisher.publish(self.output_topic, vec, key=vec.id)
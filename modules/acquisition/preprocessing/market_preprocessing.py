"""
Unified preprocessing module for numeric market data.
Contains cleaning, validation, and deduplication classes for OHLCV time-series bars.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import ClassVar

from models.market import MarketQuote, RawMarketQuote

logger = logging.getLogger(__name__)


class MarketCleaner:
    """Cleans raw numeric market data by standardizing tickers and filtering anomalies."""
    
    @staticmethod
    def clean(raw_quotes: list[RawMarketQuote]) -> list[RawMarketQuote]:
        cleaned: list[RawMarketQuote] = []
        for quote in raw_quotes:
            # 1. Standardize ticker string
            quote.ticker = quote.ticker.strip().upper()
            
            # 2. Convert string timestamps to datetime objects if necessary
            if isinstance(quote.timestamp, str):
                try:
                    # vnstock typically returns YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
                    parsed_dt = datetime.fromisoformat(quote.timestamp.replace(" ", "T"))
                    quote.timestamp = parsed_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Dropping quote for {quote.ticker}: Unparseable timestamp {quote.timestamp}")
                    continue
            elif isinstance(quote.timestamp, datetime) and quote.timestamp.tzinfo is None:
                quote.timestamp = quote.timestamp.replace(tzinfo=timezone.utc)
                
            # 3. Filter out zero or negative volume anomalies from market closures/holidays
            if quote.volume < 0:
                logger.debug(f"Dropping negative volume bar for {quote.ticker}")
                continue
                
            cleaned.append(quote)
        return cleaned


class MarketValidator:
    """Validates mathematical integrity of OHLCV bars."""
    
    REQUIRED_FIELDS: ClassVar[list[str]] = ["ticker", "timestamp", "open_price", "high_price", "low_price", "close_price", "volume"]

    @classmethod
    def validate(cls, quote: RawMarketQuote) -> tuple[bool, list[str]]:
        errors: list[str] = []
        
        # 1. Check basic positive price boundaries
        if quote.open_price <= 0 or quote.close_price <= 0:
            errors.append("Open and Close prices must be strictly positive.")
            
        # 2. Check High/Low mathematical envelope
        if quote.high_price < quote.low_price:
            errors.append(f"Math violation: High ({quote.high_price}) < Low ({quote.low_price}).")
        if quote.high_price < quote.open_price or quote.high_price < quote.close_price:
            errors.append("High price cannot be lower than Open or Close price.")
        if quote.low_price > quote.open_price or quote.low_price > quote.close_price:
            errors.append("Low price cannot be higher than Open or Close price.")
            
        # 3. Time sanity check (prevent future dates)
        if isinstance(quote.timestamp, datetime) and quote.timestamp > datetime.now(timezone.utc):
            errors.append("Market bar timestamp is in the future.")
            
        return len(errors) == 0, errors


class MarketDeduplicator:
    """Generates unique deterministic fingerprints to prevent storing duplicate OHLCV bars."""
    
    @staticmethod
    def fingerprint(symbol: str, timestamp: datetime, resolution: str) -> str:
        """SHA-256 hash of symbol + ISO timestamp + resolution."""
        raw_key = f"{symbol.upper()}|{timestamp.isoformat()}|{resolution.upper()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def process_and_deduplicate(cls, valid_quotes: list[RawMarketQuote]) -> list[MarketQuote]:
        """Maps RawMarketQuote to canonical MarketQuote and assigns deduplication fingerprints."""
        silver_quotes: list[MarketQuote] = []
        seen_fingerprints: set[str] = set()
        
        for raw in valid_quotes:
            assert isinstance(raw.timestamp, datetime), "Timestamp must be datetime by deduplication stage"
            
            fp = cls.fingerprint(raw.ticker, raw.timestamp, raw.resolution)
            
            # In-memory batch deduplication
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)
            
            silver = MarketQuote(
                id=fp,
                symbol=raw.ticker,
                timestamp=raw.timestamp,
                open=raw.open_price,
                high=raw.high_price,
                low=raw.low_price,
                close=raw.close_price,
                volume=raw.volume,
                resolution=raw.resolution,
                source=raw.source,
                fingerprint=fp
            )
            silver_quotes.append(silver)
            
        return silver_quotes
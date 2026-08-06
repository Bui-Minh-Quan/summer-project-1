"""
Connector for Vietnamese stock market data using the modern vnstock Quote API.
Includes automatic Rate-Limiting & Backoff Retry to respect free API limits (20 req/min).
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from pydantic import ValidationError

from modules.acquisition.connectors.base import BaseConnector
from modules.acquisition.models.market import RawMarketQuote

logger = logging.getLogger(__name__)

# Default watchlist: High-liquidity VN30 equity symbols
DEFAULT_WATCHLIST = [
    "ACB",
    "BID",
    "CTG",
    "DGC",
    "FPT",
    "GAS",
    "GVR",
    "HDB",
    "HPG",
    "LPB",
    "MBB",
    "MSN",
    "MWG",
    "PLX",
    "SAB",
    "SHB",
    "SSB",
    "SSI",
    "STB",
    "TCB",
    "TPB",
    "VCB",
    "VHM",
    "VIB",
    "VIC",
    "VJC",
    "VNM",
    "VPB",
    "VPL",
    "VRE",
]


class VnstockConnector(BaseConnector[RawMarketQuote]):
    def __init__(
        self,
        watchlist: list[str] | None = None,
        resolution: str = "1D",
        request_delay_seconds: float = 3.2,  # 3.2s delay enforces ~18 req/min (safe for 20 req/min Guest limit)
    ) -> None:
        self.watchlist = watchlist or DEFAULT_WATCHLIST
        self.resolution = resolution
        self.request_delay_seconds = request_delay_seconds
        self._vnstock_source = "VCI"

    @property
    def source_name(self) -> str:
        return "vnstock_quote"

    def fetch_latest(self, **kwargs: Any) -> list[RawMarketQuote]:
        """Fetch the most recent OHLCV bar for all symbols with rate limiting."""
        end_dt = datetime.now(timezone.utc)
        start_dt = pd.Timestamp(end_dt) - pd.Timedelta(days=5)

        latest_quotes: list[RawMarketQuote] = []
        for idx, symbol in enumerate(self.watchlist, 1):
            logger.info(
                f"[{idx}/{len(self.watchlist)}] Fetching latest quote for {symbol}..."
            )
            quotes = self._fetch_symbol_data_with_retry(symbol, start_dt, end_dt)
            if quotes:
                latest_quotes.append(quotes[-1])
            else:
                logger.warning(f"No latest market quote retrieved for symbol: {symbol}")

            # Rate limiting pause between requests
            time.sleep(self.request_delay_seconds)

        return latest_quotes

    def fetch_history(
        self, start_date: datetime, end_date: datetime, **kwargs: Any
    ) -> list[RawMarketQuote]:
        """Fetch historical OHLCV time-series across a date range with rate limiting."""
        logger.info(
            f"Starting market backfill from {start_date.date()} to {end_date.date()} "
            f"for {len(self.watchlist)} symbols (Pacing: {self.request_delay_seconds}s/req)..."
        )
        historical_quotes: list[RawMarketQuote] = []

        for idx, symbol in enumerate(self.watchlist, 1):
            logger.info(
                f"[{idx}/{len(self.watchlist)}] Pulling backfill for {symbol}..."
            )
            symbol_quotes = self._fetch_symbol_data_with_retry(
                symbol, start_date, end_date
            )
            historical_quotes.extend(symbol_quotes)
            logger.debug(f"Fetched {len(symbol_quotes)} historical bars for {symbol}")

            # Rate limiting pause between requests to respect 20 req/min limit
            if idx < len(self.watchlist):
                time.sleep(self.request_delay_seconds)

        return historical_quotes

    def health_check(self) -> bool:
        """Ping the data source by requesting 1 week of a highly liquid stock (FPT)."""
        try:
            test_end = datetime.now(timezone.utc)
            test_start = pd.Timestamp(test_end) - pd.Timedelta(days=7)
            results = self._fetch_symbol_data_with_retry(
                "FPT", test_start, test_end, max_retries=1
            )
            return len(results) > 0
        except Exception as e:  # noqa: BLE001
            logger.error(f"Vnstock health check failed: {e!s}")
            return False

    def _fetch_symbol_data_with_retry(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        max_retries: int = 3,
    ) -> list[RawMarketQuote]:
        """Fetches symbol data with automatic backoff retry if rate limit (429 / 20 req limit) is hit."""
        for attempt in range(1, max_retries + 1):
            try:
                return self._fetch_symbol_data(symbol, start_date, end_date)
            except Exception as e:  # noqa: BLE001
                err_str = str(e).lower()
                is_rate_limit = (
                    "giới hạn" in err_str or "limit" in err_str or "429" in err_str
                )

                if is_rate_limit and attempt < max_retries:
                    wait_time = 10.0 * attempt
                    logger.warning(
                        f"⚠️ Rate limit hit for {symbol} on attempt {attempt}/{max_retries}. "
                        f"Pausing for {wait_time}s before retrying..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch data for {symbol}: {e!s}")
                    break
        return []

    def _fetch_symbol_data(
        self, symbol: str, start_date: datetime, end_date: datetime
    ) -> list[RawMarketQuote]:
        """Internal helper calling vnstock Quote API, parsing DataFrames, and emitting Bronze models."""
        try:
            from vnstock import Quote
        except ImportError:
            from vnstock.api.quote import Quote

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        quote_client = Quote(symbol=symbol, source=self._vnstock_source)

        df = quote_client.history(
            start=start_str,
            end=end_str,
            interval=self.resolution,
        )

        # Fallback to TCBS source if VCI returns empty
        if (df is None or df.empty) and self._vnstock_source == "VCI":
            logger.debug(f"[{symbol}] VCI source empty. Retrying with source='TCBS'...")
            quote_fallback = Quote(symbol=symbol, source="TCBS")
            df = quote_fallback.history(
                start=start_str,
                end=end_str,
                interval=self.resolution,
            )

        if df is None or df.empty:
            logger.warning(
                f"No historical data returned for {symbol} between {start_str} and {end_str}."
            )
            return []

        return self._dataframe_to_models(symbol, df)

    def _dataframe_to_models(
        self, symbol: str, df: pd.DataFrame
    ) -> list[RawMarketQuote]:
        """Map pandas DataFrame rows into validated Bronze RawMarketQuote objects."""
        quotes: list[RawMarketQuote] = []
        df.columns = [str(col).lower().strip() for col in df.columns]

        for _, row in df.iterrows():
            try:
                row_dict = row.to_dict()
                raw_time = (
                    row_dict.get("time")
                    or row_dict.get("tradingdate")
                    or row_dict.get("date")
                    or row_dict.get("datetime")
                )

                if not raw_time:
                    continue

                quote = RawMarketQuote(
                    ticker=symbol.upper(),
                    timestamp=raw_time,
                    open=float(row_dict.get("open", 0.0)),
                    high=float(row_dict.get("high", 0.0)),
                    low=float(row_dict.get("low", 0.0)),
                    close=float(row_dict.get("close", 0.0)),
                    volume=float(row_dict.get("volume", 0.0)),
                    resolution=self.resolution,
                    source=self.source_name,
                    raw_payload=row_dict,
                )
                quotes.append(quote)
            except (ValidationError, ValueError, TypeError) as e:
                logger.debug(f"Skipping malformed row for {symbol}: {e}")
                continue

        return quotes

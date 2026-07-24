"""
Connector for Vietnamese stock market data using the vnstock library.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from pydantic import ValidationError

from connectors.base import BaseConnector
from models.market import RawMarketQuote

logger = logging.getLogger(__name__)

# Default watchlist: High-liquidity VN30 equity symbols
DEFAULT_WATCHLIST = ["FPT", "HPG", "VIC", "VHM", "VCB", "SSI", "MWG", "TCB"]


class VnstockConnector(BaseConnector[RawMarketQuote]):
    def __init__(self, watchlist: list[str] | None = None, resolution: str = "1D") -> None:
        self.watchlist = watchlist or DEFAULT_WATCHLIST
        self.resolution = resolution
        self._vnstock_source = "TCBS"  # Reliable default data provider in vnstock

    @property
    def source_name(self) -> str:
        return "vnstock"

    def fetch_latest(self, **kwargs: Any) -> list[RawMarketQuote]:
        """Fetch the most recent OHLCV bar for all symbols in the watchlist."""
        # For continuous streaming, we fetch the last 2 days to ensure we grab the latest active bar
        end_dt = datetime.now(timezone.utc)
        start_dt = pd.Timestamp(end_dt) - pd.Timedelta(days=5)  # Account for weekends
        
        latest_quotes: list[RawMarketQuote] = []
        for symbol in self.watchlist:
            quotes = self._fetch_symbol_data(symbol, start_dt, end_dt)
            if quotes:
                # Grab the single most recent bar for this symbol
                latest_quotes.append(quotes[-1])
            else:
                logger.warning(f"No latest market quote retrieved for symbol: {symbol}")
                
        return latest_quotes

    def fetch_history(self, start_date: datetime, end_date: datetime, **kwargs: Any) -> list[RawMarketQuote]:
        """Fetch historical OHLCV time-series for the entire watchlist across a date range."""
        logger.info(f"Starting market backfill from {start_date.date()} to {end_date.date()} for {len(self.watchlist)} symbols.")
        historical_quotes: list[RawMarketQuote] = []
        
        for symbol in self.watchlist:
            symbol_quotes = self._fetch_symbol_data(symbol, start_date, end_date)
            historical_quotes.extend(symbol_quotes)
            logger.debug(f"Fetched {len(symbol_quotes)} historical bars for {symbol}")
            
        return historical_quotes

    def health_check(self) -> bool:
        """Ping the data source by requesting 1 bar of a highly liquid stock (FPT)."""
        try:
            test_end = datetime.now(timezone.utc)
            test_start = pd.Timestamp(test_end) - pd.Timedelta(days=7)
            results = self._fetch_symbol_data("FPT", test_start, test_end)
            return len(results) > 0
        except Exception as e:  # noqa: BLE001
            logger.error(f"Vnstock health check failed: {e!s}")
            return False

    def _fetch_symbol_data(self, symbol: str, start_date: datetime, end_date: datetime) -> list[RawMarketQuote]:
        """Internal helper to call vnstock API, parse DataFrames, and emit Bronze models."""
        try:
            # Lazy import to keep startup light and allow mocking in CI tests
            from vnstock import stock_historical_data
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Call underlying library
            df = stock_historical_data(
                symbol=symbol,
                start_date=start_str,
                end_date=end_str,
                resolution=self.resolution,
                type="stock",
                source=self._vnstock_source
            )
            
            if df is None or df.empty:
                return []

            return self._dataframe_to_models(symbol, df)

        except ImportError:
            logger.error("The 'vnstock' library is not installed. Run: pip install vnstock")
            return []
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error fetching vnstock data for {symbol}: {e!s}")
            return []

    def _dataframe_to_models(self, symbol: str, df: pd.DataFrame) -> list[RawMarketQuote]:
        """Map pandas DataFrame rows into validated Bronze RawMarketQuote objects."""
        quotes: list[RawMarketQuote] = []
        
        # Ensure column names match expected lower-case standard
        df.columns = [str(col).lower() for col in df.columns]
        
        for _, row in df.iterrows():
            try:
                row_dict = row.to_dict()
                quote = RawMarketQuote(
                    ticker=symbol.upper(),
                    timestamp=row_dict.get("time") or row_dict.get("tradingdate"),
                    open=float(row_dict.get("open", 0.0)),
                    high=float(row_dict.get("high", 0.0)),
                    low=float(row_dict.get("low", 0.0)),
                    close=float(row_dict.get("close", 0.0)),
                    volume=float(row_dict.get("volume", 0.0)),
                    resolution=self.resolution,
                    source=self.source_name,
                    raw_payload=row_dict
                )
                quotes.append(quote)
            except (ValidationError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed row for {symbol}: {e}")
                continue
                
        return quotes
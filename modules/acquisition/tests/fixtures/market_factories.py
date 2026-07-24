"""
Factory functions for generating synthetic raw and silver market data for testing.
"""

from datetime import datetime, timedelta, timezone

from models.market import RawMarketQuote


def generate_raw_market_quote(
    ticker: str = "FPT",
    timestamp: datetime | str | None = None,
    open_price: float = 100.0,
    high_price: float = 105.0,
    low_price: float = 98.0,
    close_price: float = 103.0,
    volume: float = 1000000.0,
    resolution: str = "1D",
    source: str = "vnstock",
) -> RawMarketQuote:
    """Generates a single valid RawMarketQuote object."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    return RawMarketQuote(
        ticker=ticker,
        timestamp=timestamp,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        resolution=resolution,
        source=source,
    )


def generate_market_batch(
    symbols: list[str] | None = None,
    count_per_symbol: int = 5,
    include_invalid: bool = False,
) -> list[RawMarketQuote]:
    """Generates a batch of RawMarketQuote objects across multiple equity tickers."""
    symbols = symbols or ["FPT", "HPG", "VIC"]
    quotes: list[RawMarketQuote] = []
    base_time = datetime.now(timezone.utc) - timedelta(days=count_per_symbol)

    for symbol in symbols:
        for i in range(count_per_symbol):
            time_offset = base_time + timedelta(days=i)
            quote = generate_raw_market_quote(
                ticker=symbol,
                timestamp=time_offset,
                open_price=100.0 + i,
                high_price=105.0 + i,
                low_price=98.0 + i,
                close_price=103.0 + i,
                volume=500000.0 + (i * 10000),
            )
            quotes.append(quote)

    if include_invalid:
        # Invalid 1: High < Low math violation
        invalid_math = generate_raw_market_quote(
            ticker="FPT",
            high_price=90.0,
            low_price=110.0,
        )
        # Invalid 2: Negative volume anomaly
        invalid_volume = generate_raw_market_quote(
            ticker="HPG",
            volume=-500.0,
        )
        quotes.extend([invalid_math, invalid_volume])

    return quotes
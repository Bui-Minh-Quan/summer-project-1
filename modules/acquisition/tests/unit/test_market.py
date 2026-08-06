"""
Unit tests for market preprocessing: MarketCleaner, MarketValidator, and MarketDeduplicator.
"""

from datetime import datetime, timezone

from modules.acquisition.preprocessing.market_preprocessing import (
    MarketCleaner,
    MarketDeduplicator,
    MarketValidator,
)
from modules.acquisition.tests.fixtures.market_factories import (
    generate_raw_market_quote,
)


class TestMarketCleaner:
    def test_clean_standardizes_ticker_and_parses_iso_string_timestamp(self) -> None:
        raw = generate_raw_market_quote(
            ticker="  fpt  ", timestamp="2026-03-15 09:30:00"
        )
        cleaned = MarketCleaner.clean([raw])

        assert len(cleaned) == 1
        assert cleaned[0].ticker == "FPT"
        assert isinstance(cleaned[0].timestamp, datetime)
        assert cleaned[0].timestamp.tzinfo == timezone.utc

    def test_clean_filters_negative_volume_anomalies(self) -> None:
        valid_quote = generate_raw_market_quote(ticker="HPG", volume=100000.0)
        invalid_quote = generate_raw_market_quote(ticker="HPG", volume=-10.0)

        cleaned = MarketCleaner.clean([valid_quote, invalid_quote])
        assert len(cleaned) == 1
        assert cleaned[0].volume == 100000.0


class TestMarketValidator:
    def test_validate_accepts_valid_quote(self) -> None:
        quote = generate_raw_market_quote(
            open_price=10.0, high_price=12.0, low_price=9.0, close_price=11.0
        )
        is_valid, errors = MarketValidator.validate(quote)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_rejects_high_lower_than_low(self) -> None:
        quote = generate_raw_market_quote(high_price=8.0, low_price=10.0)
        is_valid, errors = MarketValidator.validate(quote)

        assert is_valid is False
        assert any("High" in err for err in errors)

    def test_validate_rejects_negative_or_zero_prices(self) -> None:
        quote = generate_raw_market_quote(open_price=0.0, close_price=-5.0)
        is_valid, errors = MarketValidator.validate(quote)

        assert is_valid is False
        assert any("strictly positive" in err for err in errors)


class TestMarketDeduplicator:
    def test_deduplicate_assigns_fingerprint_and_removes_in_batch_duplicates(
        self,
    ) -> None:
        dt = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
        q1 = generate_raw_market_quote(ticker="VIC", timestamp=dt)
        q2 = generate_raw_market_quote(ticker="VIC", timestamp=dt)  # Duplicate bar

        silver_quotes = MarketDeduplicator.process_and_deduplicate([q1, q2])

        assert len(silver_quotes) == 1
        assert silver_quotes[0].symbol == "VIC"
        assert silver_quotes[0].fingerprint is not None
        assert len(silver_quotes[0].fingerprint) == 64  # Valid SHA-256 string length

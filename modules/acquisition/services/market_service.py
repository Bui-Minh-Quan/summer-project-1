"""
Orchestrator service for Vietnamese numeric market data.
Runs completely independently from the textual news/posts acquisition pipeline.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from modules.acquisition.connectors.base import BaseConnector
from modules.acquisition.models.market import MarketQuote, RawMarketQuote
from modules.acquisition.preprocessing.market_preprocessing import (
    MarketCleaner,
    MarketDeduplicator,
    MarketValidator,
)
from modules.acquisition.repository.base import BaseRepository

logger = logging.getLogger(__name__)


@dataclass
class MarketPipelineReport:
    """Summary execution metrics for a market data pipeline run."""

    fetched: int = 0
    cleaned: int = 0
    valid: int = 0
    invalid: int = 0
    stored: int = 0
    published: int = 0
    duration_seconds: float = 0.0


class MarketAcquisitionService:
    def __init__(
        self,
        connector: BaseConnector[RawMarketQuote],
        repository: BaseRepository[MarketQuote],
        publisher: Any | None = None,
        kafka_topic: str = "market-ohlcv",
    ) -> None:
        self.connector = connector
        self.repository = repository
        self.publisher = publisher
        self.kafka_topic = kafka_topic

        self.cleaner = MarketCleaner()
        self.validator = MarketValidator()
        self.deduplicator = MarketDeduplicator()

    def run_backfill(
        self, start_date: datetime, end_date: datetime
    ) -> MarketPipelineReport:
        """Executes a historical pull for market bars bounded by start and end dates."""
        start_time = time.time()
        logger.info(
            f"[{self.connector.source_name}] Starting market backfill from {start_date} to {end_date}"
        )

        raw_quotes = self.connector.fetch_history(
            start_date=start_date, end_date=end_date
        )
        report = self._process_pipeline(raw_quotes)

        report.duration_seconds = round(time.time() - start_time, 3)
        logger.info(
            f"Market backfill completed: Stored={report.stored}, Published={report.published} in {report.duration_seconds}s"
        )
        return report

    def run_continuous(self, interval_seconds: int = 60) -> None:
        """Runs an infinite loop fetching the latest market quotes at polling intervals."""
        logger.info(
            f"Starting continuous market acquisition loop (interval: {interval_seconds}s)"
        )
        try:
            while True:
                cycle_start = time.time()
                try:
                    raw_quotes = self.connector.fetch_latest()
                    if raw_quotes:
                        self._process_pipeline(raw_quotes)
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Error in continuous market acquisition cycle: {e!s}")

                elapsed = time.time() - cycle_start
                sleep_time = max(0.0, interval_seconds - elapsed)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Continuous market acquisition stopped by user.")

    def _process_pipeline(
        self, raw_quotes: list[RawMarketQuote]
    ) -> MarketPipelineReport:
        """Internal pipeline: Clean -> Validate -> Deduplicate -> Store -> Publish."""
        report = MarketPipelineReport(fetched=len(raw_quotes))
        if not raw_quotes:
            return report

        # Step 1: Clean
        cleaned_quotes = self.cleaner.clean(raw_quotes)
        report.cleaned = len(cleaned_quotes)

        # Step 2: Validate
        valid_raw: list[RawMarketQuote] = []
        for quote in cleaned_quotes:
            is_valid, errs = self.validator.validate(quote)
            if is_valid:
                valid_raw.append(quote)
            else:
                report.invalid += 1
                logger.debug(f"Invalid market quote for {quote.ticker}: {errs}")
        report.valid = len(valid_raw)

        # Step 3: Deduplicate & map to Silver Canonical model
        silver_quotes = self.deduplicator.process_and_deduplicate(valid_raw)

        # Step 4: Store in Bronze/Silver MongoDB collection
        if silver_quotes and hasattr(self.repository, "save_many"):
            try:
                # Assuming your MongoRepository has a save_many or insert_many method
                report.stored = self.repository.save_many(silver_quotes)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Database error storing market quotes: {e!s}")

        # Step 5: Publish to Kafka
        if silver_quotes and self.publisher and hasattr(self.publisher, "publish"):
            for sq in silver_quotes:
                try:
                    # Uses your existing KafkaPublisher interface
                    self.publisher.publish(self.kafka_topic, sq)
                    report.published += 1
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Kafka error publishing quote {sq.symbol}: {e!s}")

        return report

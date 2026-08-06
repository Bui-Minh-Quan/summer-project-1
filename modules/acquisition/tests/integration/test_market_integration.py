"""
Integration tests for market pipeline with real or containerized MongoDB and Kafka.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from modules.acquisition.services.market_service import MarketAcquisitionService
from modules.acquisition.tests.fixtures.market_factories import generate_market_batch


def test_market_service_pipeline_storage_and_publishing(
    mongo_repo, kafka_publisher
) -> None:
    """Verifies that MarketAcquisitionService cleans, validates, stores in Mongo, and publishes to Kafka."""
    mongo_repo.clear()

    # Generate 5 valid quotes and 2 invalid quotes
    batch = generate_market_batch(
        symbols=["FPT"], count_per_symbol=5, include_invalid=True
    )

    # Mock connector
    mock_connector = MagicMock()
    mock_connector.source_name = "mock_vnstock"
    mock_connector.fetch_history.return_value = batch

    service = MarketAcquisitionService(
        connector=mock_connector,
        repository=mongo_repo,
        publisher=kafka_publisher,
        kafka_topic="test-market-topic",
    )

    start_date = datetime.now(timezone.utc) - timedelta(days=10)
    end_date = datetime.now(timezone.utc)

    report = service.run_backfill(start_date=start_date, end_date=end_date)

    # 7 fetched total -> 6 cleaned (1 negative vol dropped) -> 5 valid (1 high < low dropped)
    assert report.fetched == 7
    assert report.cleaned == 6
    assert report.valid == 5
    assert report.invalid == 1
    assert report.stored == 5
    assert report.published == 5

    # Verify MongoDB persistence
    assert mongo_repo.count() == 5

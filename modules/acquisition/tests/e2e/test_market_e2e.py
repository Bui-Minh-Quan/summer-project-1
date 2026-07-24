"""
End-to-end tests for MarketAcquisitionService running backfill and continuous streaming workflows.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from services.market_service import MarketAcquisitionService
from tests.fixtures.market_factories import generate_market_batch


def test_e2e_market_backfill_workflow(mongo_repo, kafka_publisher) -> None:
    """Verifies complete historical backfill workflow end-to-end."""
    mongo_repo.clear()
    raw_data = generate_market_batch(symbols=["FPT", "HPG", "VIC"], count_per_symbol=3)

    mock_connector = MagicMock()
    mock_connector.source_name = "vnstock_e2e"
    mock_connector.fetch_history.return_value = raw_data

    service = MarketAcquisitionService(
        connector=mock_connector,
        repository=mongo_repo,
        publisher=kafka_publisher,
        kafka_topic="e2e-market-backfill-topic"
    )

    report = service.run_backfill(
        start_date=datetime.now(timezone.utc) - timedelta(days=30),
        end_date=datetime.now(timezone.utc)
    )

    assert report.stored == 9
    assert report.published == 9
    assert mongo_repo.count() == 9


def test_e2e_market_continuous_streaming_workflow(mongo_repo, kafka_publisher) -> None:
    """Simulates 1 cycle of continuous real-time market streaming and terminates cleanly via mock sleep."""
    mongo_repo.clear()
    latest_quotes = generate_market_batch(symbols=["FPT"], count_per_symbol=1)

    mock_connector = MagicMock()
    mock_connector.source_name = "vnstock_stream"
    mock_connector.fetch_latest.return_value = latest_quotes

    service = MarketAcquisitionService(
        connector=mock_connector,
        repository=mongo_repo,
        publisher=kafka_publisher,
        kafka_topic="e2e-market-stream-topic"
    )

    # Unconditionally raise KeyboardInterrupt whenever time.sleep is called
    with patch("time.sleep", side_effect=KeyboardInterrupt("End of cycle 1")):
        service.run_continuous(interval_seconds=60)

    assert mongo_repo.count() == 1
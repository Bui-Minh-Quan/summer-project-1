from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from modules.acquisition.connectors.fireant import FireAntConnector
from modules.acquisition.preprocessing.documents_preprocessing import (
    DocumentCleaner,
    DocumentDeduplicator,
    DocumentValidator,
)
from modules.acquisition.repository.mongodb import MongoRepository
from modules.acquisition.services.documents_service import AcquisitionService
from modules.acquisition.tests.fixtures.document_factories import generate_fireant_batch


def test_e2e_historical_backfill_execution(mongo_repo, kafka_publisher):
    """
    Simulates a 2-day historical backfill.
    Intercepts HTTP calls to return 20 posts and 10 news articles.
    Verifies the entire engine from fetch to database to Kafka.
    """
    # 1. Setup temporary Bronze DB
    raw_repo = MongoRepository(
        uri="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        database="financial_ai_test",
        collection="e2e_raw_backfill",
    )
    raw_repo.clear()

    # 2. Instantiate real orchestrator
    service = AcquisitionService(
        connector=FireAntConnector(bearer_token="test_e2e_token"),
        raw_repository=raw_repo,
        document_repository=mongo_repo,
        cleaner=DocumentCleaner(),
        validator=DocumentValidator(),
        deduplicator=DocumentDeduplicator(),
        publisher=kafka_publisher,
        kafka_topic="e2e-backfill-topic",
    )

    # 3. Generate fake historical data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=2)

    fake_posts = generate_fireant_batch(
        count=20, is_news=False, start_id=5000, base_time=end_date
    )
    fake_news_meta = generate_fireant_batch(
        count=10, is_news=True, start_id=6000, base_time=end_date
    )

    # 4. HTTP Interception Router
    # Updated HTTP Interception Router inside test_e2e_historical_backfill_execution
    def mock_http_router(url, params=None, timeout=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        # Parse query params
        params = params or {}
        offset = params.get("offset", 0)
        api_type = params.get("type", 0)

        if url == "https://api.fireant.vn/posts":
            # If probing offset > 0, return empty list to simulate end of pagination!
            if offset > 0:
                mock_resp.json.return_value = []
                return mock_resp

            if api_type == 0:
                mock_resp.json.return_value = fake_posts
            else:
                mock_resp.json.return_value = fake_news_meta
            return mock_resp

        # Multithreaded news detail fetching: https://api.fireant.vn/posts/6000
        if "posts/" in url:
            post_id = int(url.split("/")[-1])
            detail = next(
                (item for item in fake_news_meta if item["postID"] == post_id), None
            )
            mock_resp.json.return_value = detail
            return mock_resp

        mock_resp.status_code = 404
        return mock_resp

    try:
        # Intercept requests.Session.get dynamically!
        with (
            patch("requests.Session.get", side_effect=mock_http_router),
            patch("time.sleep", return_value=None),
        ):
            # EXECUTE THE E2E BACKFILL ENGINE
            report = service.run_backfill(start_date, end_date)

            # Assert top-to-bottom pipeline success
            assert report.fetched == 30  # 20 posts + 10 news
            assert report.raw_saved == 30
            assert report.stored == 30  # All 30 saved to Silver MongoDB
            assert report.published == 30  # All 30 broadcasted to Kafka

            # Verify real MongoDB database state
            assert raw_repo.count() == 30
            assert mongo_repo.count() == 30

            # Verify data integrity of a saved news item
            sample_news = mongo_repo.find_by_id("6000")
            assert sample_news.title == "Macro Economic Report 6000"
            assert sample_news.symbols == ["VIC", "VHM"]

    finally:
        raw_repo.clear()
        raw_repo.close()


def test_e2e_continuous_streaming_with_api_resilience(mongo_repo, kafka_publisher):
    """
    Simulates 1 cycle of continuous real-time streaming.
    Demonstrates HTTP 500 failure recovery and breaks the infinite while-loop cleanly.
    """
    raw_repo = MongoRepository(
        uri="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        database="financial_ai_test",
        collection="e2e_raw_stream",
    )
    raw_repo.clear()

    service = AcquisitionService(
        connector=FireAntConnector(bearer_token="test_stream_token"),
        raw_repository=raw_repo,
        document_repository=mongo_repo,
        cleaner=DocumentCleaner(),
        validator=DocumentValidator(),
        deduplicator=DocumentDeduplicator(),
        publisher=kafka_publisher,
        kafka_topic="e2e-stream-topic",
    )

    fake_latest_news = generate_fireant_batch(count=5, is_news=True, start_id=9000)

    # We track how many times the API was called
    api_call_counter = {"count": 0}

    def flaky_server_router(url, params=None, timeout=None):
        api_call_counter["count"] += 1
        mock_resp = MagicMock()

        # SIMULATE SERVER FAILURE: Return HTTP 500 on the first attempt!
        if api_call_counter["count"] == 1:
            mock_resp.status_code = 500
            mock_resp.json.return_value = {"error": "Server Overloaded"}
            return mock_resp

        # On subsequent retry attempts, return success!
        mock_resp.status_code = 200
        if "posts/" in url:
            post_id = int(url.split("/")[-1])
            detail = next(
                (item for item in fake_latest_news if item["postID"] == post_id), None
            )
            mock_resp.json.return_value = detail
        else:
            mock_resp.json.return_value = fake_latest_news

        return mock_resp

    try:
        # Custom sleep handler: only raise KeyboardInterrupt when sleeping for the 300s interval!
        def mock_sleep_router(seconds):
            if seconds >= 300:
                raise KeyboardInterrupt("Simulated Ctrl+C at end of Cycle 1")

        with (
            patch("requests.Session.get", side_effect=flaky_server_router),
            patch("time.sleep", side_effect=mock_sleep_router),
        ):
            service.run_continuous(interval_seconds=300, batch_limit=10)

        # Verify that despite the initial HTTP 500 on news, the continuous loop survived,
        # fetched community posts, and successfully saved data to MongoDB!
        assert mongo_repo.count() > 0
        assert api_call_counter["count"] > 1

    finally:
        raw_repo.clear()
        raw_repo.close()

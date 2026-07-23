from unittest.mock import MagicMock, patch

from connectors.fireant import FireAntConnector
from preprocessing.cleaner import DocumentCleaner
from preprocessing.deduplicator import DocumentDeduplicator
from preprocessing.validator import DocumentValidator
from repository.mongodb import MongoRepository
from services.acquisition_service import AcquisitionService
from tests.fixtures.factories import generate_fireant_batch


def test_e2e_continuous_streaming_with_api_resilience(mongo_repo, kafka_publisher):
    """
    Simulates 1 cycle of continuous real-time streaming.
    Demonstrates HTTP 500 failure recovery and breaks the infinite while-loop cleanly.
    """
    raw_repo = MongoRepository(
        uri="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        database="financial_ai_test",
        collection="e2e_raw_stream"
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
        kafka_topic="e2e-stream-topic"
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
            detail = next((item for item in fake_latest_news if item["postID"] == post_id), None)
            mock_resp.json.return_value = detail
        else:
            mock_resp.json.return_value = fake_latest_news
            
        return mock_resp

    try:
            # Custom sleep handler: only raise KeyboardInterrupt when sleeping for the 300s interval!
        def mock_sleep_router(seconds):
            if seconds >= 300:
                raise KeyboardInterrupt("Simulated Ctrl+C at end of Cycle 1")

        with patch("requests.Session.get", side_effect=flaky_server_router), \
                patch("time.sleep", side_effect=mock_sleep_router):
            
            service.run_continuous(interval_seconds=300, batch_limit=10)

        # Verify that despite the initial HTTP 500 on news, the continuous loop survived,
        # fetched community posts, and successfully saved data to MongoDB!
        assert mongo_repo.count() > 0
        assert api_call_counter["count"] > 1

    finally:
        raw_repo.clear()
        raw_repo.close()
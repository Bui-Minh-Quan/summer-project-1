from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from connectors.fireant import FireAntConnector
from preprocessing.cleaner import DocumentCleaner
from preprocessing.deduplicator import DocumentDeduplicator
from preprocessing.validator import DocumentValidator
from repository.mongodb import MongoRepository
from services.acquisition_service import AcquisitionService
from tests.fixtures.factories import generate_fireant_batch


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
        collection="e2e_raw_backfill"
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
        kafka_topic="e2e-backfill-topic"
    )

    # 3. Generate fake historical data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=2)
    
    fake_posts = generate_fireant_batch(count=20, is_news=False, start_id=5000, base_time=end_date)
    fake_news_meta = generate_fireant_batch(count=10, is_news=True, start_id=6000, base_time=end_date)

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
            detail = next((item for item in fake_news_meta if item["postID"] == post_id), None)
            mock_resp.json.return_value = detail
            return mock_resp

        mock_resp.status_code = 404
        return mock_resp

    try:
        # Intercept requests.Session.get dynamically!
        with patch("requests.Session.get", side_effect=mock_http_router), \
            patch("time.sleep", return_value=None):
            # EXECUTE THE E2E BACKFILL ENGINE
            report = service.run_backfill(start_date, end_date)

            # Assert top-to-bottom pipeline success
            assert report.fetched == 30  # 20 posts + 10 news
            assert report.raw_saved == 30
            assert report.stored == 30   # All 30 saved to Silver MongoDB
            assert report.published == 30 # All 30 broadcasted to Kafka
            
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
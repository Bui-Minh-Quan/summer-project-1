from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


@pytest.fixture
def mock_db():
    """Creates a mocked Database instance."""
    return AsyncMock()

@pytest.fixture(autouse=True)
def override_lifespan_dependencies(mock_db):
    """Intercepts lifespan initializations to prevent real DB/Redis connections."""
    
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db

    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with patch("app.api.main.AsyncIOMotorClient", return_value=mock_client), \
         patch("app.api.main.redis_from_url", return_value=mock_redis), \
         patch("app.api.main.FastAPICache.init"), \
         patch("app.api.main.consume_kafka_market_data", AsyncMock()), \
         patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.start"), \
         patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.add_job"):
        
        # Disable caching globally for tests
        from fastapi_cache import FastAPICache
        FastAPICache._enable = False
        
        yield
        
        FastAPICache._enable = True

@pytest.fixture
def client(override_lifespan_dependencies):
    """Provides a TestClient. Lifespan will now use the patched dependencies."""
    with TestClient(app) as client:
        yield client
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def mock_db():
    """Creates a mocked Database instance."""
    return AsyncMock()

@pytest.fixture(autouse=True)
def override_lifespan_dependencies(mock_db):
    """Intercepts lifespan initializations to prevent real DB/Redis connections."""
    
    # When main.py calls AsyncIOMotorClient()[settings.MONGO_DB], it returns mock_db
    mock_client = MagicMock()
    mock_client.__getitem__.return_value = mock_db

    with patch("main.AsyncIOMotorClient", return_value=mock_client), \
         patch("main.redis_from_url", AsyncMock()), \
         patch("main.FastAPICache.init"), \
         patch("main.consume_kafka_market_data", AsyncMock()), \
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
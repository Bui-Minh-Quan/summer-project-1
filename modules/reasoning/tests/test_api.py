"""
API tests for Reasoning Engine FastAPI endpoints.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from modules.reasoning.api import app
from modules.reasoning.models.schema import ReasoningResponse, TrendDirection


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@patch("modules.reasoning.api.ReasoningService")
def test_analyze_endpoint_success(mock_service_cls):
    # Create the mock instance returned by ReasoningService()
    mock_service_instance = AsyncMock()
    mock_response = ReasoningResponse(
        symbol="FPT",
        target_date="2026-08-04",
        trend=TrendDirection.BULLISH,
        confidence=0.88,
        reasoning="Strong earnings momentum supported by volume expansion.",
    )
    mock_service_instance.analyze_trend.return_value = mock_response
    mock_service_cls.return_value = mock_service_instance

    with TestClient(app) as client:
        response = client.post(
            "/analyze",
            json={"symbol": "FPT", "date": "2026-08-04T00:00:00Z"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "FPT"
        assert data["trend"] == "Bullish"
        assert data["confidence"] == 0.88
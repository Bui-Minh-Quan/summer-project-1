"""
Unit tests for FastAPI Serving endpoints.
"""

from fastapi.testclient import TestClient

from modules.mlops.serving.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_validation_error():
    # Sending empty body should trigger HTTP 422 Unprocessable Entity
    response = client.post("/predict", json={})
    assert response.status_code == 422
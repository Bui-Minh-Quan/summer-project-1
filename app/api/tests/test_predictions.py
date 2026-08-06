from unittest.mock import AsyncMock, MagicMock, patch


def test_get_dual_prediction_success(client, mock_db):
    mock_feature_doc = {
        "symbol": "FPT",
        "close_price": 100.0,
        "daily_return": 0.02,
        "intraday_volatility": 0.015,
        "volume_ratio": 1.2,
        "post_count": 10,
        "total_engagement": 50,
        "mean_sentiment": 0.5,
        "net_sentiment_score": 0.4,
        "sentiment_price_divergence": -0.1,
    }

    mock_db["gold_market_features"].find_one = AsyncMock(return_value=mock_feature_doc)
    mock_db["predictions_log"].insert_many = AsyncMock()

    mock_mlops_resp = {"horizon_days": 1, "predicted_return_pct": 0.05}
    mock_reasoning_resp = {
        "symbol": "FPT",
        "target_date": "2026-08-06",
        "trend": "Bullish",
        "confidence": 0.85,
        "reasoning": "Strong Q3 growth and expanding margins.",
    }

    with patch("app.api.routers.predictions.fetch_mlops_prediction", AsyncMock(return_value=mock_mlops_resp)), \
         patch("app.api.routers.predictions.fetch_reasoning", AsyncMock(return_value=mock_reasoning_resp)):

        response = client.post("/api/v1/predictions/", json={"symbol": "FPT"})

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "FPT"
        assert data["current_price"] == 100.0
        assert data["trend"] == "Bullish"
        assert len(data["price_forecasts"]) == 5
        assert data["price_forecasts"][0]["expected_price"] == 105.0


def test_get_dual_prediction_stock_not_found(client, mock_db):
    mock_db["gold_market_features"].find_one = AsyncMock(return_value=None)

    response = client.post("/api/v1/predictions/", json={"symbol": "UNKNOWN"})
    assert response.status_code == 404


def test_get_classification_backtest(client, mock_db):
    mock_records = [
        {
            "target_date": "2026-08-01",
            "current_price": 100.0,
            "trend": "Bullish",
            "actual_trend": "Bullish",
            "reasoning": "Earnings surge.",
            "model": "vLLM-TRR",
        }
    ]

    # Motor's find() is synchronous, so we use MagicMock
    cursor_mock = MagicMock()
    cursor_mock.sort.return_value = cursor_mock
    cursor_mock.skip.return_value = cursor_mock
    cursor_mock.limit.return_value = cursor_mock
    cursor_mock.to_list = AsyncMock(return_value=mock_records)

    mock_db["predictions_log"].find = MagicMock(return_value=cursor_mock)

    response = client.get("/api/v1/predictions/backtest/classification/FPT?page=1&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price"] == 100.0
    assert data[0]["predicted_trend"] == "Bullish"


def test_get_regression_backtest(client, mock_db):
    mock_records = [
        {
            "target_date": "2026-08-01",
            "current_price": 100.0,
            "price_forecasts": [
                {"expected_price": 102.0},
                {"expected_price": 104.0},
                {"expected_price": 105.0},
                {"expected_price": 106.0},
                {"expected_price": 108.0},
            ],
            "actual_price_t1": 101.5,
            "model": "XGBoost-Regressor",
        }
    ]

    cursor_mock = MagicMock()
    cursor_mock.sort.return_value = cursor_mock
    cursor_mock.skip.return_value = cursor_mock
    cursor_mock.limit.return_value = cursor_mock
    cursor_mock.to_list = AsyncMock(return_value=mock_records)

    mock_db["predictions_log"].find = MagicMock(return_value=cursor_mock)

    response = client.get("/api/v1/predictions/backtest/regression/FPT")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price"] == 100.0
    assert data[0]["predicted_price_t1"] == 102.0
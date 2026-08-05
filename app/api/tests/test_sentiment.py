from unittest.mock import AsyncMock, MagicMock


def test_get_related_news(client, mock_db):
    mock_docs = [
        {
            "id": "news_001",
            "title": "FPT Quarter 3 Financial Results",
            "content": "FPT announced record profits for the third quarter.",
            "published_at": "2026-08-05T10:00:00Z",
            "source": "FireAnt",
            "url": "https://fireant.vn/news/001",
        }
    ]

    cursor_mock = MagicMock()
    cursor_mock.sort.return_value = cursor_mock
    cursor_mock.skip.return_value = cursor_mock
    cursor_mock.limit.return_value = cursor_mock
    cursor_mock.to_list = AsyncMock(return_value=mock_docs)

    mock_db["documents"].find = MagicMock(return_value=cursor_mock)

    response = client.get("/api/v1/sentiment/news/FPT?page=1&limit=20")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "news_001"


def test_get_social_sentiment_calculated(client, mock_db):
    mock_agg_result = [
        {
            "_id": ["FPT"],
            "total_posts": 10,
            "positive_count": 6,
            "negative_count": 2,
            "neutral_count": 2,
            "total_likes": 50,
            "total_shares": 10,
            "total_replies": 20,
        }
    ]

    agg_cursor = MagicMock()
    agg_cursor.to_list = AsyncMock(return_value=mock_agg_result)
    mock_db["documents"].aggregate = MagicMock(return_value=agg_cursor)

    response = client.get("/api/v1/sentiment/score/FPT")

    assert response.status_code == 200
    data = response.json()
    assert data["positive_count"] == 6
    assert data["negative_count"] == 2
    assert data["normalized_hype_score"] == 0.05


def test_get_social_sentiment_empty_fallback(client, mock_db):
    agg_cursor = MagicMock()
    agg_cursor.to_list = AsyncMock(return_value=[])
    mock_db["documents"].aggregate = MagicMock(return_value=agg_cursor)

    response = client.get("/api/v1/sentiment/score/UNKNOWN")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "UNKNOWN"
    assert data["normalized_hype_score"] == 0.0
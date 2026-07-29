"""
Unit tests for FeatureEngineeringService.
Verifies social post engagement math and net sentiment calculation.
"""

from unittest.mock import MagicMock

import pytest
from services.feature_service import FeatureEngineeringService


@pytest.mark.asyncio
async def test_process_social_post_sentiment_math():
    # Mock MongoDB repositories
    mock_feature_repo = MagicMock()
    mock_feature_repo.collection.find_one.return_value = None  # Simulate no existing vector
    mock_silver_repo = MagicMock()

    service = FeatureEngineeringService(
        feature_repo=mock_feature_repo,
        silver_market_repo=mock_silver_repo,
    )

    post_payload = {
        "id": "post_555",
        "document_type": "post",
        "published_at": "2026-07-29T10:00:00Z",
        "symbols": ["FPT"],
        "metadata": {
            "totalLikes": 25,
            "totalReplies": 5,
            "totalShares": 2,
            "sentiment": 1,  # Positive sentiment
        },
    }

    vectors = await service.process_social_post(post_payload)

    assert len(vectors) == 1
    fpt_vector = vectors[0]

    # Verify ID standard
    assert fpt_vector.id == "FPT_2026-07-29"
    assert fpt_vector.symbol == "FPT"
    
    # Verify engagement totals
    assert fpt_vector.post_count == 1
    assert fpt_vector.total_likes == 25
    assert fpt_vector.total_replies == 5
    assert fpt_vector.total_shares == 2
    assert fpt_vector.total_engagement == 32

    # Verify quantified sentiment scores
    assert fpt_vector.positive_posts == 1
    assert fpt_vector.mean_sentiment == 1.0
    assert fpt_vector.net_sentiment_score == 1.0
    
    # Ensure update_one was called on MongoDB collection
    mock_feature_repo.collection.update_one.assert_called_once()
"""
Unit tests for TRR prompt template formatting.
"""

from modules.reasoning.models.schema import MarketData
from modules.reasoning.prompts.templates import build_trr_prompt


def test_build_trr_prompt_structure():
    mock_graph = [
        {
            "subject_type": "NEWS",
            "subject": "FPT reports strong quarterly earnings",
            "relation": "MENTIONS",
            "object": "FPT",
            "date": "2026-08-01",
            "attention_score": 0.95,
        }
    ]
    mock_market = [
        MarketData(date="2026-08-01", close=130.5, volume=1.8, daily_return=0.025)
    ]

    messages = build_trr_prompt(
        symbol="FPT",
        target_date="2026-08-02",
        graph_data=mock_graph,
        market_data=mock_market,
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "FPT reports strong quarterly earnings" in messages[1]["content"]
    assert "130.50" in messages[1]["content"]


def test_build_trr_prompt_empty_context():
    messages = build_trr_prompt(
        symbol="VIC",
        target_date="2026-08-02",
        graph_data=[],
        market_data=[],
    )

    assert "No recent impactful news" in messages[1]["content"]
    assert "No recent market data available" in messages[1]["content"]
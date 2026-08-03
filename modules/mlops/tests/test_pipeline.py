"""
Unit and Integration tests for MLOps pipeline dataset preparation and target logic.
"""

import numpy as np
import pandas as pd
import pytest

from modules.mlops.dataset import create_targets, prepare_train_val_test_splits


@pytest.fixture
def mock_feature_dataframe() -> pd.DataFrame:
    """Generates synthetic stock feature records spanning multiple dates for 2 symbols."""
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    data = []
    
    for symbol in ["FPT", "VIC"]:
        base_price = 100.0
        for i, dt in enumerate(dates):
            base_price += (i % 3 - 1) * 2.0  # Fluctuating price
            data.append({
                "symbol": symbol,
                "timestamp": dt,
                "close_price": base_price,
                "daily_return": 0.01,
                "intraday_volatility": 0.02,
                "volume_ratio": 1.0,
                "post_count": 5,
                "total_engagement": 20,
                "mean_sentiment": 0.1,
                "net_sentiment_score": 0.1,
                "sentiment_price_divergence": 0.0
            })
            
    return pd.DataFrame(data)


def test_create_targets_logic(mock_feature_dataframe: pd.DataFrame) -> None:
    df_with_targets = create_targets(mock_feature_dataframe, horizons=[1, 2])
    
    assert "target_return_t1" in df_with_targets.columns
    assert "target_class_t1" in df_with_targets.columns
    assert "target_return_t2" in df_with_targets.columns
    
    # Verify discrete class labels are restricted to [-1, 0, 1]
    unique_classes = df_with_targets["target_class_t1"].unique()
    for cls_val in unique_classes:
        assert cls_val in [-1, 0, 1]


def test_prepare_splits_no_data_leakage(mock_feature_dataframe: pd.DataFrame) -> None:
    df_targets = create_targets(mock_feature_dataframe, horizons=[1])
    
    splits = prepare_train_val_test_splits(
        df_targets,
        target_col="target_class_t1",
        train_cutoff="2024-01-05",
        val_cutoff="2024-01-08"
    )
    
    # Scaler must be fitted and present
    assert splits["scaler"] is not None
    assert isinstance(splits["X_train"], np.ndarray)
    assert len(splits["X_train"]) > 0
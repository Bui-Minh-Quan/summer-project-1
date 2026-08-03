"""
Dataset Preprocessing and Feature Engineering Utilities for MLOps Pipeline.
Handles target horizon generation and leak-free feature scaling.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "close_price",
    "daily_return",
    "intraday_volatility",
    "volume_ratio",
    "post_count",
    "total_engagement",
    "mean_sentiment",
    "net_sentiment_score",
    "sentiment_price_divergence",
]


def create_targets(
    df: pd.DataFrame, 
    horizons: list[int] | None = None,
    bullish_threshold: float = 0.01,
    bearish_threshold: float = -0.01
) -> pd.DataFrame:
    target_horizons = horizons if horizons is not None else [1, 2, 3, 4, 5]
    data = df.copy().sort_values(by=["symbol", "timestamp"]).reset_index(drop=True)
    
    for h in target_horizons:
        future_close = data.groupby("symbol")["close_price"].shift(-h)
        
        # 1. Percentage Return (Regression Target)
        ret_col = f"target_return_t{h}"
        data[ret_col] = np.where(
            data["close_price"] > 0.001, 
            (future_close - data["close_price"]) / data["close_price"], 
            0.0
        )
        data[ret_col] = data[ret_col].replace([np.inf, -np.inf], 0.0).fillna(0.0)
        
        # 2. 3-Class Discrete Buckets (Classification Target)
        class_col = f"target_class_t{h}"
        conditions = [
            data[ret_col] > bullish_threshold,
            data[ret_col] < bearish_threshold
        ]
        choices = [1, -1]
        data[class_col] = np.select(conditions, choices, default=0)

    return data


def prepare_train_val_test_splits(
    df: pd.DataFrame,
    feature_cols: list[str] = FEATURE_COLUMNS,
    target_col: str = "target_class_t1",
    train_cutoff: str = "2025-01-01",
    val_cutoff: str = "2026-01-01"
) -> dict[str, np.ndarray | StandardScaler]:
    """
    Performs a temporal split and fits the StandardScaler strictly on training data
    to eliminate lookahead bias.
    """
    # Filter out rows where target is NaN (due to forward shifting)
    clean_df = df.dropna(subset=[target_col]).copy()
    
    train_mask = clean_df["timestamp"] < train_cutoff
    val_mask = (clean_df["timestamp"] >= train_cutoff) & (clean_df["timestamp"] < val_cutoff)
    test_mask = clean_df["timestamp"] >= val_cutoff

    X_train_raw = clean_df.loc[train_mask, feature_cols].fillna(0.0)
    X_val_raw = clean_df.loc[val_mask, feature_cols].fillna(0.0)
    X_test_raw = clean_df.loc[test_mask, feature_cols].fillna(0.0)

    # Convert classification targets from [-1, 0, 1] to [0, 1, 2] for XGBoost compatibility
    y_train = clean_df.loc[train_mask, target_col].values
    y_val = clean_df.loc[val_mask, target_col].values
    y_test = clean_df.loc[test_mask, target_col].values

    if "class" in target_col:
        y_train = y_train + 1
        y_val = y_val + 1
        y_test = y_test + 1

    # Fit scaler ONLY on training data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_val_scaled = scaler.transform(X_val_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    return {
        "X_train": X_train_scaled,
        "y_train": y_train,
        "X_val": X_val_scaled,
        "y_val": y_val,
        "X_test": X_test_scaled,
        "y_test": y_test,
        "scaler": scaler
    }
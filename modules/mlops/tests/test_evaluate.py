"""
Unit tests for evaluation gates.
"""

from modules.mlops.config import config


def test_quality_gate_config():
    assert config.min_accuracy == 0.40
    assert config.max_rmse == 0.05
    assert len(config.target_horizons) == 5
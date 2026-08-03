"""
Configuration settings for Module 4: MLOps Pipeline.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLOpsConfig(BaseSettings):
    # Quality Gates (Lowered thresholds for testing & pipeline validation)
    min_accuracy: float = Field(default=0.0, alias="ML_MIN_ACCURACY")
    max_rmse: float = Field(default=1.0, alias="ML_MAX_RMSE")
    
    # Target Horizons (in trading days ahead)
    target_horizons: list[int] = Field(default=[1, 2, 3, 4, 5], alias="ML_TARGET_HORIZONS")
    
    # Database Settings
    mongo_uri: str = Field(
        default="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        alias="MONGO_URI",
    )
    db_name: str = "financial_ai"
    collection_name: str = "gold_market_features"
    
    # Storage & Versioning Paths
    data_dir: Path = Path("data")
    parquet_filename: str = "gold_features.parquet"
    
    @property
    def parquet_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / self.parquet_filename

    # MLflow Settings
    mlflow_tracking_uri: str = Field(
        default="sqlite:///mlflow.db",
        alias="MLFLOW_TRACKING_URI"
    )
    mlflow_experiment_name: str = "VN30_Stock_Trend_Prediction"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


config = MLOpsConfig()
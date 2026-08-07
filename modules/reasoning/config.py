"""
Configuration for Module 4: Reasoning Engine.
Handles connections for vLLM, Neo4j, and MongoDB.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReasoningConfig(BaseSettings):
    # vLLM Server Settings
    vllm_base_url: str = Field(default="http://localhost:8000/v1", alias="VLLM_BASE_URL")
    vllm_api_key: str = Field(default="sk-empty-key", alias="VLLM_API_KEY")
    vllm_model_name: str = Field(default="Qwen/Qwen2.5-7B-Instruct", alias="VLLM_MODEL_NAME")
    
    # LLM Generation Parameters
    max_tokens: int = 512
    temperature: float = 0.2  # Keep low for analytical, deterministic reasoning
    
    # Neo4j Settings (Knowledge Graph)
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="secretpassword", alias="NEO4J_PASSWORD")
    
    # MongoDB Settings 
    mongo_uri: str = Field(
        default="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        alias="MONGO_URI",
    )
    mongo_db: str = "financial_ai"
    mongo_collection: str = "silver_market_quotes" # Adjust if using gold_market_features

    # TRR (Temporal Relational Reasoning) Settings
    lookback_days: int = Field(default=30, description="How many days of history to fetch")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


config = ReasoningConfig()
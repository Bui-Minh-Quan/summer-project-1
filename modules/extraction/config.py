"""
Configuration settings for Module 2 Knowledge Graph Extraction.
Reads environment variables with fallback defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class ExtractionConfig(BaseSettings):
    mongo_uri: str = Field(
        default="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        alias="MONGO_URI",
    )
    kafka_broker: str = Field(
        default="localhost:9092",
        alias="KAFKA_BROKER",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    vllm_url: str = Field(
        default="http://localhost:8000/v1",
        alias="VLLM_URL",
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


config = ExtractionConfig()
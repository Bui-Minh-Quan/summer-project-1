"""
Configuration settings for Module 3 Graph Building Engine.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphConfig(BaseSettings):
    mongo_uri: str = Field(
        default="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        alias="MONGO_URI",
    )
    kafka_broker: str = Field(
        default="localhost:9092",
        alias="KAFKA_BROKER",
    )
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        alias="NEO4J_URI",
    )
    neo4j_user: str = Field(
        default="neo4j",
        alias="NEO4J_USER",
    )
    neo4j_password: str = Field(
        default="secretpassword",
        alias="NEO4J_PASS",
    )
    batch_size: int = Field(
        default=100,
        alias="GRAPH_BATCH_SIZE",
    )
    confidence_threshold: float = Field(
        default=0.6,
        alias="GRAPH_CONFIDENCE_THRESHOLD",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


config = GraphConfig()
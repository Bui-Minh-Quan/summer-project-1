import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB for reading market data and saving predictions
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://admin:secretpassword@localhost:27017/?authSource=admin")
    MONGO_DB: str = "financial_ai"
    
    # Internal Module API Endpoints
    MLOPS_API_URL: str = os.getenv("MLOPS_API_URL", "http://localhost:8001")
    REASONING_API_URL: str = os.getenv("REASONING_API_URL", "http://localhost:8002")
    
    # Neo4j and Redis for later steps
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASS: str = os.getenv("NEO4J_PASS", "secretpassword")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
settings = Settings()
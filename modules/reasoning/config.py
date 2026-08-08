from pydantic import Field
from pydantic_settings import BaseSettings


class ReasoningConfig(BaseSettings):
    # vLLM Configuration
    vllm_base_url: str = Field(default="http://vllm:8000/v1", alias="VLLM_BASE_URL")
    vllm_model_name: str = Field(default="qwen-1.5b", alias="MODEL_NAME")
    vllm_api_key: str = Field(default="EMPTY", alias="VLLM_API_KEY")
    max_tokens: int = Field(default=1024, alias="MAX_TOKENS")
    temperature: float = Field(default=0.1, alias="TEMPERATURE")

    @property
    def model_name(self) -> str:
        return self.vllm_model_name

    # MongoDB Configuration
    mongo_uri: str = Field(
        default="mongodb://admin:secretpassword@mongodb:27017/?authSource=admin",
        alias="MONGO_URI",
    )
    mongo_db: str = "financial_ai"
    mongo_collection: str = "silver_market_quotes"

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="secretpassword", alias="NEO4J_PASS")

    # Algorithm Hyperparameters
    lookback_days: int = Field(default=30)
    decay_lambda: float = Field(default=0.05)

    class Config:
        env_file = ".env"
        extra = "ignore"

config = ReasoningConfig()
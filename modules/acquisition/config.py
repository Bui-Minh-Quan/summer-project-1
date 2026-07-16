from pydantic_settings import BaseSettings, SettingsConfigDict

class AcquisitionConfig(BaseSettings):
    mongo_uri: str 
    fire_ant_bearer: str 
    kafka_broker: str = "localhost: 9092"
    database_name: str = "financial_ai"
    kafka_topic: str = "textual-documents"

    model_config = SettingsConfigDict(env_file=".env", 
                                      env_file_encoding="utf-8",
                                      extra="ignore")

# Global config instance
config = AcquisitionConfig()
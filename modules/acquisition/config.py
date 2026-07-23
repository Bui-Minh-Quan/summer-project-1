from pydantic import Field
from pydantic_settings import BaseSettings


class AcquisitionConfig(BaseSettings):
    mongo_uri: str = Field(
        default="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        alias="MONGO_URI"
    )
    fire_ant_bearer: str = Field(
        default="",
        alias="FIRE_ANT_BEARER"
    )
    kafka_broker: str = Field(
        default="localhost:9092",
        alias="KAFKA_BROKER"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"

# Line 15 instantiation:
config = AcquisitionConfig()
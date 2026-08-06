import pytest

from modules.acquisition.models.document import Document
from modules.acquisition.publishers.kafka_publisher import KafkaPublisher
from modules.acquisition.repository.mongodb import MongoRepository

TEST_MONGO_URI = "mongodb://admin:secretpassword@localhost:27017/?authSource=admin"
TEST_DATABASE = "financial_ai_test"
TEST_KAFKA_BROKER = "localhost:9092"




@pytest.fixture(scope="function")
def mongo_repo():
    # Spines up a real connection to the temporary test database
    repo = MongoRepository(
        uri=TEST_MONGO_URI,
        database=TEST_DATABASE,
        collection="test_documents",
        model_class=Document,
    )

    repo.clear()

    yield repo

    repo.clear()  # Clean up after test
    repo.close()  # Close the connection


@pytest.fixture(scope="function")
def kafka_publisher():
    # Spins up a real Kafka producer for testing
    publisher = KafkaPublisher(bootstrap_servers=TEST_KAFKA_BROKER)
    yield publisher
    publisher.close()  # Close the producer after test

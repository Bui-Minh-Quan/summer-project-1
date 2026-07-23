from models.document import Document, DocumentType
from publishers.kafka_publisher import KafkaDocumentPublisher


def test_publish_batch_to_broker(kafka_publisher: KafkaDocumentPublisher):
    doc1 = Document(
        id="kafka_test_1",
        source="fireant",
        document_type=DocumentType.NEWS,
        content="Kafka test document 1",
    )

    doc2 = Document(
        id="kafka_test_2",
        source="fireant",
        document_type=DocumentType.POST,
        content="Kafka test document 2",
    )

    # Send across TCP socket to localhost:9092 (Kafka broker)
    published_count = kafka_publisher.publish_batch(
        topic="test-integration-topic", documents=[doc1, doc2]
    )

    assert published_count == 2
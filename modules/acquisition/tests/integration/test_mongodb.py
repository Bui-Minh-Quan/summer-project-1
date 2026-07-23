from models.document import Document, DocumentType, Language
from repository.mongodb import MongoRepository

def test_save_and_find_by_id(mongo_repo: MongoRepository):
    # 1. Create a sample document
    doc = Document(
        id="test_doc_1",
        source="fireant",
        document_type=DocumentType.NEWS,
        title="Test Document",
        content="This is a test document.",
        language=Language.VI
    )

    # 2. Save the document to MongoDB
    mongo_repo.save(doc)

    # 3. Query the document by its ID
    retrieved_doc = mongo_repo.find_by_id("test_doc_1")

    assert retrieved_doc is not None
    assert retrieved_doc.id == doc.id
    assert retrieved_doc.title == doc.title


def test_swallow_duplicate_fingerprint(mongo_repo: MongoRepository):
    # 1. Create sample documents
    doc1 = Document(
        id="batch_1",
        source="fireant",
        document_type=DocumentType.NEWS,
        title="Duplicate Fingerprint Test",
        content="contentA",
        fingerprint="fingerprint123",
        language=Language.VI
    )

    # doc2 with a different ID but the same fingerprint as doc1
    doc2 = Document(
        id="batch_2",
        source="fireant",
        document_type=DocumentType.NEWS,
        title="Duplicate Fingerprint Test",
        content="contentB",
        fingerprint="fingerprint123",  # Same fingerprint as doc1
        language=Language.VI
    )

    # 2. Save both documents to MongoDB
    saved_count = mongo_repo.save_many([doc1, doc2])

    # 3. Only one document should be saved due to the duplicate fingerprint
    assert mongo_repo.count() == 1
    assert saved_count == 1
    
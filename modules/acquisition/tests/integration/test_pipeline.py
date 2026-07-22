from datetime import datetime, timezone
from models.document import RawDocument, DocumentType
from preprocessing.cleaner import DocumentCleaner
from preprocessing.deduplicator import DocumentDeduplicator
from preprocessing.validator import DocumentValidator
from connectors.fireant import FireAntConnector
from repository.mongodb import MongoRepository
from services.acquisition_service import AcquisitionService

def test_full_acquisition_pipeline_flow(mongo_repo, kafka_publisher):
    """
    Feeds 4 raw payloads into the AcquisitionService and verifies that:
    - All 4 are archived to the Bronze Lake (raw_repository).
    - 1 is dropped by validation (missing title).
    - 1 is dropped by deduplication (duplicate content).
    - Exactly 2 clean, unique documents land in Silver Mongo and Kafka!
    """
    # 1. Setup a temporary Bronze repository for raw documents
    raw_repo = MongoRepository(
        uri="mongodb://admin:secretpassword@localhost:27017/?authSource=admin",
        database="financial_ai_test",
        collection="test_raw_documents"
    )
    raw_repo.clear()  # Clean slate

    # 2. Instantiate our real orchestrator (using dummy token since we don't fetch from web)
    service = AcquisitionService(
        connector=FireAntConnector(bearer_token="dummy_token"),
        raw_repository=raw_repo,
        document_repository=mongo_repo,  # Our Silver repo fixture
        cleaner=DocumentCleaner(),
        validator=DocumentValidator(),
        deduplicator=DocumentDeduplicator(),
        publisher=kafka_publisher,
        kafka_topic="test-pipeline-stream"
    )

    # 3. Create 4 raw test payloads
    now = datetime.now(timezone.utc).isoformat()
    
    # Doc A: Valid News with HTML
    doc_a = RawDocument(
        id="pipe_1", source="fireant", document_type=DocumentType.NEWS, fetched_at=datetime.now(timezone.utc),
        payload={"postID": "pipe_1", "title": "Market Surge", "content": "<p>VN-Index <b>tăng</b> mạnh.</p>", "date": now}
    )
    
    # Doc B: Valid Post
    doc_b = RawDocument(
        id="pipe_2", source="fireant", document_type=DocumentType.POST, fetched_at=datetime.now(timezone.utc),
        payload={"postID": "pipe_2", "title": "Good stock!", "content": "Buying more VIC today.", "date": now}
    )
    
    # Doc C: Duplicate of Doc A (Same title and source!)
    doc_c = RawDocument(
        id="pipe_3", source="fireant", document_type=DocumentType.NEWS, fetched_at=datetime.now(timezone.utc),
        payload={"postID": "pipe_3", "title": "Market Surge", "content": "<p>VN-Index <b>tăng</b> mạnh.</p>", "date": now}
    )
    
    # Doc D: Invalid News (Missing Title!)
    doc_d = RawDocument(
        id="pipe_4", source="fireant", document_type=DocumentType.NEWS, fetched_at=datetime.now(timezone.utc),
        payload={"postID": "pipe_4", "title": None, "content": "This news has no headline.", "date": now}
    )

    try:
        # 4. EXECUTE THE PIPELINE ENGINE!
        report = service._process_pipeline([doc_a, doc_b, doc_c, doc_d])

        # 5. ASSERTIONS: Verify every metric on the pipeline report
        assert report.fetched == 4
        assert report.raw_saved == 4       # All 4 landed in Bronze Mongo
        assert report.mapped == 4          # All 4 successfully mapped to Document schema
        assert report.invalid == 1         # Doc D failed validation
        assert report.duplicates == 1      # Doc C failed deduplication
        assert report.cleaned == 3         # Docs A, B, and C went through cleaner
        assert report.stored == 2          # Only Docs A and B saved to Silver Mongo!
        assert report.published == 2       # Only Docs A and B streamed to Kafka!

        # 6. Verify actual database state
        assert raw_repo.count() == 4       # Bronze DB actually holds 4 records
        assert mongo_repo.count() == 2     # Silver DB actually holds 2 records
        
        # Verify that HTML cleaning actually happened in the Silver DB
        saved_doc_a = mongo_repo.find_by_id("pipe_1")
        assert saved_doc_a.content == "VN-Index tăng mạnh."  # <p> and <b> tags stripped!

    finally:
        # Teardown the temporary raw collection
        raw_repo.clear()
        raw_repo.close()
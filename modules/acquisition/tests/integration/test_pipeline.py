from datetime import datetime, timezone
from models.document import RawDocument, DocumentType
from conftest import TEST_MONGO_URI, TEST_DATABASE
from preprocessing.cleaner import DocumentCleaner
from preprocessing.deduplicator import DocumentDeduplicator
from preprocessing.validator import DocumentValidator
from connectors.fireant import FireAntConnector
from repository.mongodb import MongoRepository
from services.acquisition_service import AcquisitionService



def test_full_acquisition_pipeline_flow_1(mongo_repo, kafka_publisher):
    """
    Feeds 4 raw payloads into the AcquisitionService and verifies that:
    - All 4 are archived to the Bronze Lake (raw_repository).
    - 1 is dropped by validation (missing title).
    - 1 is dropped by deduplication (duplicate content).
    - Exactly 2 clean, unique documents land in Silver Mongo and Kafka!
    """
    # 1. Setup a temporary Bronze repository for raw documents
    raw_repo = MongoRepository(
        uri=TEST_MONGO_URI,
        database=TEST_DATABASE,
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
        assert report.stored == 2          # Only Docs A and B saved to Silver Mongo
        assert report.published == 2       # Only Docs A and B streamed to Kafka

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

def test_full_acquisition_pipeline_flow_2(mongo_repo, kafka_publisher): 
    """ 
    Feeds 3 raw identical payloads into the AcquisitionService and verifies that:
    - All 3 are archived to the Bronze Lake (raw_repository).
    - 2 are dropped by deduplication (duplicate content).
    - Exactly 1 clean, unique document lands in Silver Mongo and Kafka!
    """

    # 1. Setup 
    raw_repo = MongoRepository(
        uri=TEST_MONGO_URI,
        database=TEST_DATABASE,
        collection="test_raw_documents"
    )

    raw_repo.clear()  # Clean slate

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

    # 2. Create 3 identical raw test payloads
    now = datetime.now(timezone.utc).isoformat()
    identical_payload = {
        "postID": "pipe_5",
        "title": "Duplicate Test",
        "content": "<p>This is a duplicate test.</p>",
        "date": now
    }

    raw_docs = [
        RawDocument(id="pipe_5a", source="fireant", document_type=DocumentType.NEWS, fetched_at=datetime.now(timezone.utc), payload=identical_payload),
        RawDocument(id="pipe_5b", source="fireant", document_type=DocumentType.NEWS, fetched_at=datetime.now(timezone.utc), payload=identical_payload),
        RawDocument(id="pipe_5c", source="fireant", document_type=DocumentType.NEWS, fetched_at=datetime.now(timezone.utc), payload=identical_payload)
    ]

    try:
        # 3. EXECUTE THE PIPELINE ENGINE!
        report = service._process_pipeline(raw_docs)

        # 4. ASSERTIONS: Verify every metric on the pipeline report
        assert report.fetched == 3
        assert report.raw_saved == 3       # All 3 landed in Bronze Mongo
        assert report.mapped == 3          # All 3 successfully mapped to Document schema
        assert report.invalid == 0         # No validation failures
        assert report.duplicates == 2      # 2 duplicates dropped
        assert report.cleaned == 3         # All 3 went through cleaner
        assert report.stored == 1          # Only 1 saved to Silver Mongo
        assert report.published == 1       # Only 1 streamed to Kafka

        # Verify actual database state
        assert raw_repo.count() == 3       # Bronze DB actually holds 3 records
        assert mongo_repo.count() == 1     # Silver DB actually holds 1 record

    finally:
        # Teardown the temporary raw collection
        raw_repo.clear()
        raw_repo.close()


def test_full_acquisition_pipeline_flow_3(mongo_repo, kafka_publisher): 
    """ 
    Feeds 100 randomly generated raw payloads with:
    - 100 unique documents
    - 0 duplicates (same title and content)
    - 0 invalid documents (missing title or content)
    Verifies that:
    - All 100 are archived to the Bronze Lake (raw_repository).
    - All 100 are successfully mapped, cleaned, validated, and stored in Silver Mongo and Kafka!
    """

    # 1. Setup
    raw_repo = MongoRepository(
        uri=TEST_MONGO_URI,
        database=TEST_DATABASE,
        collection="test_raw_documents"
    )

    raw_repo.clear()  # Clean slate

    # 2. Instantiate the orchestrator
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

    # 3. Generate 100 unique raw test payloads
    now = datetime.now(timezone.utc).isoformat()
    raw_docs = [
        RawDocument(
            id=f"pipe_{i}",
            source="fireant",
            document_type=DocumentType.NEWS,
            fetched_at=datetime.now(timezone.utc),
            payload={
                "postID": f"pipe_{i}",
                "title": f"Unique Title {i}",
                "content": f"<p>This is unique content for document {i}.</p>",
                "date": now
            }
        )
        for i in range(100)
    ]

    # 4. EXECUTE THE PIPELINE ENGINE
    try:
        report = service._process_pipeline(raw_docs)

        # 5. ASSERTIONS: Verify every metric on the pipeline report
        assert report.fetched == 100
        assert report.raw_saved == 100       # All 100 landed in Bronze Mongo
        assert report.mapped == 100          # All 100 successfully mapped to Document schema
        assert report.invalid == 0           # No validation failures
        assert report.duplicates == 0        # No duplicates dropped
        assert report.cleaned == 100         # All 100 went through cleaner
        assert report.stored == 100          # All 100 saved to Silver Mongo
        assert report.published == 100       # All 100 streamed to Kafka

        # Verify actual database state
        assert raw_repo.count() == 100       # Bronze DB actually holds 100 records
        assert mongo_repo.count() == 100     # Silver DB actually holds 100 records

    finally:
        # Teardown the temporary raw collection
        raw_repo.clear()
        raw_repo.close()



def test_full_acquisition_pipeline_flow_4(mongo_repo, kafka_publisher):
    """ 
    Feeds 50 raw payloads with:
    - 25 unique documents
    - 25 duplicates (same title and content as the first 25)
    - 0 invalid documents (missing title or content)
    Verifies that:
    - All 50 are archived to the Bronze Lake (raw_repository).
    - 25 are dropped by deduplication (duplicate content).
    - Exactly 25 clean, unique documents land in Silver Mongo and Kafka!
    - Kafka streaming is verified by checking the published count.
    """

    # 1. Setup
    raw_repo = MongoRepository(
        uri=TEST_MONGO_URI,
        database=TEST_DATABASE,
        collection="test_raw_documents"
    )

    raw_repo.clear()  # Clean slate

    # 2. Instantiate the orchestrator
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

    # 3. Generate 25 unique raw test payloads and 25 duplicates
    now = datetime.now(timezone.utc).isoformat()
    unique_raw_docs = [
        RawDocument(
            id=f"pipe_{i}",
            source="fireant",
            document_type=DocumentType.NEWS,
            fetched_at=datetime.now(timezone.utc),
            payload={
                "postID": f"pipe_{i}",
                "title": f"Unique Title {i}",
                "content": f"<p>This is unique content for document {i}.</p>",
                "date": now
            }
        )
        for i in range(25)
    ]

    duplicate_raw_docs = [
        RawDocument(
            id=f"pipe_dup_{i}",
            source="fireant",
            document_type=DocumentType.NEWS,
            fetched_at=datetime.now(timezone.utc),
            payload={
                "postID": f"pipe_dup_{i}",
                "title": f"Unique Title {i}",  # Same title as unique docs
                "content": f"<p>This is unique content for document {i}.</p>",  # Same content as unique docs
                "date": now
            }
        )
        for i in range(25)
    ]

    all_raw_docs = unique_raw_docs + duplicate_raw_docs

    # 4. EXECUTE THE PIPELINE ENGINE
    try:
        report = service._process_pipeline(all_raw_docs)


        # 5. ASSERTIONS: Verify every metric on the pipeline report
        assert report.fetched == 50
        assert report.raw_saved == 50       # All 50 landed in Bronze Mongo
        assert report.mapped == 50          # All 50 successfully mapped to Document schema
        assert report.invalid == 0           # No validation failures
        assert report.duplicates == 25       # 25 duplicates dropped
        assert report.cleaned == 50          # All 50 went through cleaner
        assert report.stored == 25           # Only 25 saved to Silver Mongo
        assert report.published == 25        # Only 25 streamed to Kafka
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        raise
    finally:
        # Teardown the temporary raw collection
        raw_repo.clear()
        raw_repo.close()
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from connectors.fireant import FireAntConnector
from models.document import Document, DocumentType, Language, RawDocument
from preprocessing.documents_preprocessing import (
    DocumentCleaner,
    DocumentDeduplicator,
    DocumentValidator,
)


def test_cleaner_strips_html_tags():
    cleaner = DocumentCleaner()
    raw_doc = Document(
        id="101",
        source="Fireant",
        document_type=DocumentType.NEWS,
        title="<h1>Breaking News</h1>",
        content="<p>This is a <strong>test</strong> document.</p>",
        language=Language.VI
    )

    cleaned_doc = cleaner.clean(raw_doc)
    assert cleaned_doc.title == "Breaking News"
    assert cleaned_doc.content == "This is a test document."

def test_cleaner_handles_none_content():
    cleaner = DocumentCleaner()
    doc = Document(id="102", source="fireant", document_type=DocumentType.POST, content=None)

    cleaned_doc = cleaner.clean(doc)

    assert cleaned_doc.content is None
    assert cleaned_doc.title is None




def test_fingerprint_is_deterministic():
    deduplicator = DocumentDeduplicator()
    # Ensure document_type is only passed once per Document!
    doc1 = Document(id="1", source="fireant", title="Same Title", document_type=DocumentType.NEWS)
    doc2 = Document(id="2", source="fireant", title="Same Title", document_type=DocumentType.NEWS)

    hash1 = deduplicator.fingerprint(doc1)
    hash2 = deduplicator.fingerprint(doc2)
    assert hash1 == hash2

def test_is_duplicate_checks_repository():
    deduplicator = DocumentDeduplicator()
    doc = Document(id="3", source="fireant", title="Existing News", document_type=DocumentType.NEWS)
    
    mock_repo = MagicMock()
    mock_repo.exists_by_fingerprint.return_value = True

    is_dup = deduplicator.is_duplicate(doc, mock_repo)
    
    assert is_dup is True
    mock_repo.exists_by_fingerprint.assert_called_once()




def test_map_document_extracts_correct_fields():
    # Initialize connector
    connector = FireAntConnector(bearer_token="dummy_token")

    raw_payload = {
        "postID": "12345",
        "title": "Sample News Title",
        "content": "<p>This is a sample news content.</p>",
        "date": "2023-10-01T12:00:00Z",
        "taggedSymbols": [{"symbol": "VIC"}, {"symbol": "VHM"}],
        "sentiment": 1,
        "totalLikes": 100
    }

    raw_doc = RawDocument(
        id="22222",
        source="fireant",
        document_type=DocumentType.NEWS,
        fetched_at=datetime.now(timezone.utc),
        payload=raw_payload
    )

    doc = connector.map_document(raw_doc)

    assert doc is not None
    assert doc.id == "22222"
    assert doc.title == "Sample News Title"
    assert doc.symbols == ["VIC", "VHM"]
    assert doc.metadata["sentiment"] == 1
    assert doc.metadata["totalLikes"] == 100





def test_news_missing_title():
    validator = DocumentValidator()
    doc = Document(
        id="123",
        source="fireant",
        document_type=DocumentType.NEWS,
        title=None,
        content="This is a news article.",
        language=Language.VI
    )

    result = validator.validate(doc)
    assert not result.valid
    assert any("title" in err.lower() for err in result.errors)


def test_post_missing_title():
    validator = DocumentValidator()
    doc = Document(
        id="124",
        source="fireant",
        document_type=DocumentType.POST,
        title=None,
        content="This is a post.",
        language=Language.VI
    )

    result = validator.validate(doc)
    assert result.valid  # Posts can have no title
    assert len(result.errors) == 0

def test_future_publication_date():
    validator = DocumentValidator()
    future_date = datetime.now(timezone.utc) + timedelta(days=1)
    doc = Document(
        id="125",
        source="fireant",
        document_type=DocumentType.NEWS,
        title="Future News",
        content="This news is from the future.",
        published_at=future_date,
        language=Language.VI
    )

    result = validator.validate(doc)
    assert not result.valid
    assert any("future" in err.lower() for err in result.errors)
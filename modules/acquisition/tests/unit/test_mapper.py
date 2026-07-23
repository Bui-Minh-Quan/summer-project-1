from datetime import datetime, timezone

from connectors.fireant import FireAntConnector
from models.document import DocumentType, RawDocument


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

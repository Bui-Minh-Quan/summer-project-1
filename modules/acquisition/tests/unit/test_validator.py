from datetime import datetime, timedelta, timezone

from models.document import Document, DocumentType, Language
from preprocessing.validator import DocumentValidator


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
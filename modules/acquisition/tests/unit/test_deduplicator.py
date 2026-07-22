from unittest.mock import MagicMock
from models.document import Document, DocumentType
from preprocessing.deduplicator import DocumentDeduplicator

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
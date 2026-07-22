from models.document import Document, DocumentType, Language 
from preprocessing.cleaner import DocumentCleaner

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
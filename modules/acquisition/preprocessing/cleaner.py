# Basic document cleaner

import re 

import warnings
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from models.document import Document

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

class DocumentCleaner:
    # Basic cleaner for textual documents.

    def clean(self, document: Document) -> Document:
        if document.content:
            document.content = self._clean_html(document.content)

        if document.title:
            document.title = self._clean_html(document.title)
        
        return document
    
    @staticmethod
    def _clean_html(text: str) -> str:
        # Remove HTML tags and normalize whitespace

        soup = BeautifulSoup(text, "html.parser")

        text = soup.get_text(separator=" ")

        text = re.sub(r"\s+", " ", text)

        return text.strip()
    
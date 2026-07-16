# Basic document cleaner

import re 

from bs4 import BeautifulSoup

from models.document import Document

class DocumentCleaner:
    # Basic cleaner for textual documents.

    def clean(self, document: Document) -> Document:
        if document.content:
            document.content = self._clean_html(document.content)
        
        return document
    
    @staticmethod
    def _clean_html(text: str) -> str:
        # Remove HTML tags and normalize whitespace

        soup = BeautifulSoup(text, "html.parser")

        text = soup.get_text(separator=" ")

        text = re.sub(r"\s+", " ", text)

        return text.strip()
    
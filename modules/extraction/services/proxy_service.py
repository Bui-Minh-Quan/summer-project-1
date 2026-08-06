"""
Proxy service wrappers for Module 2 extraction pipelines.
"""

import logging
from datetime import datetime
from typing import Any

from modules.extraction.models.extraction import ExtractionResult
from modules.extraction.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)


class NewsOnlyServiceProxy:
    """
    Proxy wrapper around ExtractionService to guarantee that ONLY 'news' documents
    are processed during real-time Kafka streaming (Continuous Mode).
    """

    def __init__(self, target_service: ExtractionService, default_symbols: list[str] | None = None) -> None:
        self.target_service = target_service
        self.default_symbols = default_symbols

    async def process_document(
        self,
        document_id: str,
        title: str,
        content: str,
        symbols: list[str] | None = None,
        document_type: str | None = None,
        published_at: datetime | None = None,
        **kwargs: Any,
    ) -> ExtractionResult | None:
        """Intercepts individual document calls from Kafka consumer and drops non-news items."""
        raw_doc_type = document_type or kwargs.get("type") or kwargs.get("doc_type") or kwargs.get("document_type")
        doc_type_str = str(raw_doc_type).strip().lower() if raw_doc_type else ""

        # Fail Closed: Drop anything that isn't explicitly 'news'
        if doc_type_str != "news":
            logger.debug(f"[Continuous Filter] Dropped non-news item {document_id} (detected type: '{raw_doc_type}')")
            return None

        effective_symbols = self.default_symbols if self.default_symbols is not None else symbols

        return await self.target_service.process_document(
            document_id=document_id,
            title=title,
            content=content,
            symbols=effective_symbols,
            published_at=published_at,
            caching=kwargs.get("caching", True),
        )

    async def process_batch(self, documents: list[dict[str, Any]]) -> list[ExtractionResult]:
        """Intercepts batch calls from Kafka consumer, stripping out non-news documents."""
        news_docs = []
        for doc in documents:
            raw_doc_type = doc.get("document_type") or doc.get("type") or doc.get("doc_type")
            doc_type_str = str(raw_doc_type).strip().lower() if raw_doc_type else ""

            if doc_type_str != "news":
                logger.debug(f"[Continuous Filter] Dropped non-news doc {doc.get('id')} from batch (type: '{raw_doc_type}')")
                continue

            if self.default_symbols is not None:
                doc["symbols"] = self.default_symbols
            news_docs.append(doc)

        if not news_docs:
            return []

        return await self.target_service.process_batch(news_docs)
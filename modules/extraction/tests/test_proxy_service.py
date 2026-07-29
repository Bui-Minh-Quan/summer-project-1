"""
Unit tests for NewsOnlyServiceProxy in Module 2.
Verifies that social posts and non-news items are rejected before reaching vLLM.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from services.proxy_service import NewsOnlyServiceProxy


@pytest.mark.asyncio
async def test_proxy_drops_non_news():
    mock_service = MagicMock()
    mock_service.process_document = AsyncMock()
    proxy = NewsOnlyServiceProxy(target_service=mock_service)

    # 1. Test passing a social post -> Must return None and NOT call process_document
    result = await proxy.process_document(
        document_id="post_123",
        title="Forum discussion",
        content="FPT is going up today!",
        symbols=["FPT"],
        document_type="post",
    )
    assert result is None
    mock_service.process_document.assert_not_called()

    # 2. Test passing an item with empty/None type -> Must fail closed
    result_none = await proxy.process_document(
        document_id="unknown_123",
        title="Unknown type",
        content="Some content",
        document_type=None,
    )
    assert result_none is None
    mock_service.process_document.assert_not_called()


@pytest.mark.asyncio
async def test_proxy_forwards_news_with_default_symbols():
    mock_service = MagicMock()
    mock_service.process_document = AsyncMock(return_value="success_result")
    
    # Configure proxy with target portfolio override
    target_symbols = ["FPT", "VIC"]
    proxy = NewsOnlyServiceProxy(target_service=mock_service, default_symbols=target_symbols)

    result = await proxy.process_document(
        document_id="news_101",
        title="State Bank interest rate policy",
        content="The State Bank announced new interest rate targets.",
        symbols=["VCB"],  # Original symbols should be overridden by default_symbols
        document_type="news",
    )

    assert result == "success_result"
    mock_service.process_document.assert_called_once_with(
        document_id="news_101",
        title="State Bank interest rate policy",
        content="The State Bank announced new interest rate targets.",
        symbols=target_symbols,
        caching=True,
    )
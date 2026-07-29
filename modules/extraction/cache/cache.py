"""
Asynchronous Redis cache for LLM extraction payloads.
"""

import json
import logging
from typing import Any

from redis.asyncio import Redis, from_url

logger = logging.getLogger(__name__)


class LLMExtractionCache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl_seconds: int = 604800) -> None:
        # Default TTL: 7 days (604,800 seconds)
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._redis: Redis | None = None

    async def connect(self) -> None:
        if not self._redis:
            self._redis = await from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            logger.info("Connected to async Redis cache.")

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _format_key(self, doc_hash: str, schema_name: str) -> str:
        return f"llm_cache:{schema_name}:{doc_hash}"

    async def get(self, doc_hash: str, schema_name: str = "default") -> dict[str, Any] | None:
        """Retrieve a cached extraction payload by document hash."""
        if not self._redis:
            await self.connect()
        try:
            assert self._redis is not None
            key = self._format_key(doc_hash, schema_name)
            data = await self._redis.get(key)
            if data:
                logger.debug(f"Cache hit for {key}")
                return json.loads(str(data))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis cache GET error: {e}")
        return None

    async def set(self, doc_hash: str, payload: dict[str, Any], schema_name: str = "default") -> None:
        """Store an extraction payload in Redis with an expiration TTL."""
        if not self._redis:
            await self.connect()
        try:
            assert self._redis is not None
            key = self._format_key(doc_hash, schema_name)
            await self._redis.set(key, json.dumps(payload), ex=self.ttl_seconds)
            logger.debug(f"Cache set for {key}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Redis cache SET error: {e}")
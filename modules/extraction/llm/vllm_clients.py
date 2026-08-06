"""
Asynchronous vLLM client supporting OpenAI-compatible endpoints and GPU guided decoding.
"""

import json
import logging
import time
from typing import Any

import httpx

from modules.extraction.llm.base import BaseLLMClient
from modules.extraction.llm.models import LLMRequest, LLMResponse, LLMUsageTelemetry

logger = logging.getLogger(__name__)


class VLLMClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model_name: str = "qwen-1.5b",
        api_key: str = "EMPTY",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout_seconds
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

    @property
    def client_name(self) -> str:
        return f"vllm:{self.model_name}"

    async def health_check(self) -> bool:
        """Ping the vLLM /models endpoint to verify GPU server status."""
        try:
            resp = await self._http_client.get(f"{self.base_url}/models")
            return resp.status_code == 200
        except Exception as e:  # noqa: BLE001
            logger.error(f"vLLM health check failed: {e!s}")
            return False

    @staticmethod
    def _clean_schema(obj: Any) -> Any:
        """Recursively strip metadata fields across all nested levels of Pydantic $defs."""
        if isinstance(obj, dict):
            return {
                k: VLLMClient._clean_schema(v)
                for k, v in obj.items()
                if k not in ("title", "description", "$schema")
            }
        elif isinstance(obj, list):
            return [VLLMClient._clean_schema(item) for item in obj]
        return obj

    async def extract_structured(self, request: LLMRequest) -> LLMResponse:
        """Execute structured extraction against vLLM using GPU guided decoding."""
        start_time = time.time()

        # Clean metadata from schema recursively to prevent 400 xgrammar syntax errors
        schema = self._clean_schema(request.response_schema)

        # Estimate prompt tokens for Vietnamese text (~2.2 chars per token safety margin)
        total_prompt_chars = len(request.system_prompt) + len(request.user_prompt)
        estimated_prompt_tokens = int(total_prompt_chars / 2.2)

        # Context budget: 8192 total limit - estimated prompt tokens - 128 safety buffer
        max_context = 8192
        available_gen_tokens = max_context - estimated_prompt_tokens - 128

        # Allocate between 512 and 1536 tokens for output JSON generation
        max_gen_tokens = max(512, min(available_gen_tokens, 1536))

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt}
            ],
            "temperature": request.temperature,
            "max_tokens": max_gen_tokens,
            "guided_json": schema,
        }

        try:
            resp = await self._http_client.post(f"{self.base_url}/chat/completions", json=payload)
            
            if resp.is_error:
                logger.error(f"vLLM HTTP {resp.status_code} error response: {resp.text}")
                resp.raise_for_status()

            data = resp.json()

            choice = data["choices"][0]
            raw_text = choice["message"]["content"]
            usage = data.get("usage", {})

            parsed_json = json.loads(raw_text)
            latency = round(time.time() - start_time, 4)

            telemetry = LLMUsageTelemetry(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_seconds=latency,
                model_name=self.client_name,
                cached_hit=False
            )

            return LLMResponse(
                raw_content=raw_text,
                parsed_payload=parsed_json,
                telemetry=telemetry
            )

        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"vLLM inference failure for hash {request.document_hash}: {e!s}")
            return LLMResponse(
                raw_content="",
                parsed_payload={},
                telemetry=LLMUsageTelemetry(
                    model_name=self.client_name,
                    latency_seconds=round(time.time() - start_time, 4)
                ),
                error=str(e)
            )

    async def close(self) -> None:
        """Clean up HTTP connections."""
        await self._http_client.aclose()
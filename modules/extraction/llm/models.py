from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class LLMUsageTelemetry(BaseModel):
    """Token usage and runtime performance metrics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0
    model_name: str = ""
    cached_hit: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LLMRequest(BaseModel):
    """Standardized request wrapper for structured extraction."""
    system_prompt: str
    user_prompt: str
    temperature: float = 0.0  # 0.0 forces deterministic output for JSON extraction
    max_tokens: int = 4096
    response_schema: dict[str, Any] = Field(description="JSON Schema dictionary for guided decoding")
    document_hash: str = Field(description="SHA-256 hash of the input document text for Redis caching")


class LLMResponse(BaseModel):
    """Unified response payload returning parsed JSON data and execution telemetry."""
    raw_content: str
    parsed_payload: dict[str, Any]
    telemetry: LLMUsageTelemetry
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None and len(self.parsed_payload) > 0
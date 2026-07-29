from abc import ABC, abstractmethod

from llm.models import LLMRequest, LLMResponse


class BaseLLMClient(ABC):
    @property
    @abstractmethod
    def client_name(self) -> str:
        """Return identifier of the underlying LLM engine (e.g., 'vllm-qwen2.5', 'gemini-1.5')."""

    @abstractmethod
    async def extract_structured(self, request: LLMRequest) -> LLMResponse:
        """Execute a structured inference call and return a parsed response with telemetry."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify whether the inference server is responsive."""
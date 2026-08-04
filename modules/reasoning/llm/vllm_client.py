"""
OpenAI-compatible client for communicating with the local vLLM server.
"""

import logging

from openai import AsyncOpenAI
from pydantic import ValidationError

from modules.reasoning.config import config
from modules.reasoning.models.schema import ReasoningResponse, TrendDirection

logger = logging.getLogger("vllm_client")


class VLLMClient:
    def __init__(self):
        # Initializes using the local vLLM URL and dummy API key from config
        self.client = AsyncOpenAI(
            base_url=config.vllm_base_url,
            api_key=config.vllm_api_key
        )

    async def generate_structured_reasoning(self, messages: list[dict[str, str]]) -> ReasoningResponse:
        """
        Sends the synthesized prompt to vLLM and validates the output against the Pydantic schema.
        """
        try:
            response = await self.client.chat.completions.create(
                model=config.vllm_model_name,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                # Forces the model to output a JSON object rather than free-text
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
            
            # Parse and validate strictly against the schema
            return ReasoningResponse.model_validate_json(raw_content)
            
        except ValidationError as ve:
            logger.error(f"LLM output failed schema validation: {ve}")
            return self._build_fallback(str(ve))
        except Exception as e: #noqa: BLE001
            logger.error(f"vLLM inference failed: {e}")
            return self._build_fallback(str(e))

    def _build_fallback(self, error_msg: str) -> ReasoningResponse:
        """Safe fallback if the LLM crashes or hallucinates broken JSON."""
        return ReasoningResponse(
            symbol="ERROR",
            target_date="ERROR",
            trend=TrendDirection.SIDEWAYS,
            confidence=0.0,
            reasoning=f"Reasoning engine failure: {error_msg}"
        )
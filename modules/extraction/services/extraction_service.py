"""
Asynchronous Orchestrator Service for Target-Anchored Knowledge Graph Extraction.
Executes iterative Temporal Relational Reasoning (TRR) across financial streams.
"""

import asyncio
import hashlib
import logging
import time
from typing import Any

from cache.cache import LLMExtractionCache
from llm.base import BaseLLMClient
from llm.models import LLMRequest
from models.extraction import (
    ExtractionMetadata,
    ExtractionResult,
    GraphRelation,
    RelationalExtractionPayload,
)
from models.ontology import EntityType
from prompts.templates import ExtractionPromptManager
from publishers.base import BasePublisher
from repository.base import BaseRepository

logger = logging.getLogger(__name__)

# Banned generic super-nodes and placeholders that pollute Knowledge Graphs
BANNED_SUPER_NODES: set[str] = {
    "doanh nghiệp",
    "công ty",
    "nhà đầu tư",
    "người dân",
    "thị trường",
    "kinh tế",
    "việt nam",
    "chính phủ",
    "nhà nước",
    "khách hàng",
    "người lao động",
    "xã hội",
    "trọng điểm",
    "thực thể",
    "chi tiết",
    "bài báo",
    "nhân tố",
    "đối tượng",
    "yếu tố",
}


class ExtractionService:
    """Orchestrates Target-Anchored N-Pass LLM extraction, MongoDB graph staging, and Kafka streaming."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        cache: LLMExtractionCache,
        repository: BaseRepository[ExtractionResult],
        publisher: BasePublisher[ExtractionResult],
        prompt_version: str = "v1.0",
        output_kafka_topic: str = "extracted-knowledge-topic",
        max_concurrency: int = 8,
        max_passes: int = 2,
    ) -> None:
        self.llm_client = llm_client
        self.cache = cache
        self.repository = repository
        self.publisher = publisher
        self.prompt_version = prompt_version
        self.output_kafka_topic = output_kafka_topic
        self.max_passes = max(1, max_passes)
        self._semaphore = asyncio.Semaphore(max_concurrency)

    def _generate_deterministic_id(self, document_id: str) -> str:
        """Creates an idempotent primary key based on document ID, prompt version, and pass depth."""
        raw_key = f"{document_id}|{self.prompt_version}|passes:{self.max_passes}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _generate_content_hash(
        self,
        title: str | None,
        content: str | None,
        pass_num: int,
        symbols: list[str] | None = None,
    ) -> str:
        """Creates a SHA-256 fingerprint for Redis caching per pass, incorporating symbol tags."""
        safe_title = (title or "").strip()
        safe_content = (content or "").strip()
        sorted_symbols = ",".join(sorted(symbols)) if symbols else ""
        raw_text = f"trr_v6_pass:{pass_num}|syms:{sorted_symbols}|{safe_title}\n{safe_content}"
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def _filter_and_deduplicate(
        self,
        raw_relations: list[GraphRelation],
        seen_edge_keys: set[str],
        doc_id: str,
    ) -> list[GraphRelation]:
        """
        Imperative Python Filter executed immediately after each pass.
        Removes self-loops, banned Anti-Super Nodes, blank/numeric entities,
        and truncates paragraph-long predicates before staging.
        """
        valid_relations: list[GraphRelation] = []

        for rel in raw_relations:
            sub_name = rel.subject.name.strip()
            obj_name = rel.object.name.strip()
            sub_norm = sub_name.lower()
            obj_norm = obj_name.lower()

            # 1. Anti-Self-Loop Defense
            if sub_norm == obj_norm:
                logger.warning(f"[Sanitizer] Dropped self-relation on '{sub_name}' in doc {doc_id}")
                continue

            # 2. Length and pure-numeric validation
            if len(sub_name) < 2 or len(obj_name) < 2 or sub_name.isnumeric() or obj_name.isnumeric():
                logger.warning(f"[Sanitizer] Dropped short/numeric entity link: '{sub_name}' -> '{obj_name}' in doc {doc_id}")
                continue

            # 3. Anti-Super-Node & Generic Placeholder Filter
            if sub_norm in BANNED_SUPER_NODES or obj_norm in BANNED_SUPER_NODES:
                logger.warning(f"[Sanitizer] Dropped banned super-node link: '{sub_name}' -> '{obj_name}' in doc {doc_id}")
                continue

            # 4. Predicate Truncation (Limits verbosity to concise verb phrases)
            words = rel.relation.strip().split()
            if len(words) > 12:
                rel.relation = " ".join(words[:10]) + "..."
                logger.debug(f"[Sanitizer] Truncated verbose predicate: '{sub_name}' -> '{obj_name}'")

            # 5. Edge Deduplication
            edge_key = f"{sub_norm}->{obj_norm}"
            if edge_key not in seen_edge_keys:
                seen_edge_keys.add(edge_key)
                valid_relations.append(rel)

        return valid_relations

    @staticmethod
    def _format_context_block(relations: list[GraphRelation], pass_num: int) -> str:
        """
        Dynamically generates the guidance block for the current pass using ONLY validated relations.
        Returns an empty string on Pass 1 to avoid triggering negative context hallucinations.
        """
        if pass_num == 1 or not relations:
            return ""

        lines = [
            f"BỐI CẢNH: Dưới đây là {len(relations)} quan hệ ĐÃ ĐƯỢC PHÁT HIỆN VÀ XÁC NHẬN ở bước trước:",
        ]
        for r in relations:
            lines.append(
                f"- ({r.subject.name} [{r.subject.entity_type.value}]) --[{r.relation}]--> "
                f"({r.object.name} [{r.object.entity_type.value}]) | Tác động: {r.market_impact.value}"
            )
        lines.append(
            "\nYÊU CẦU BƯỚC NÀY: Dựa trên các quan hệ trên, hãy suy luận tiếp các tác động lan truyền gián tiếp đến CỔ PHIẾU hoặc NGÀNH liên quan. KHÔNG lặp lại các quan hệ đã có ở trên."
        )
        return "\n".join(lines)

    async def _execute_pass(
        self,
        title: str,
        content: str,
        context_block: str,
        pass_num: int,
        doc_id: str,
        symbols: list[str] | None = None,
        caching: bool = True,
    ) -> tuple[list[GraphRelation], float, int, int]:
        """Executes a single extraction pass against vLLM with Target-Anchored prompt formatting."""
        content_hash = self._generate_content_hash(
            title, f"{content}\n{context_block}", pass_num=pass_num, symbols=symbols
        )
        cached_data = await self.cache.get(content_hash, schema_name=f"trr_pass_{pass_num}")

        if cached_data and caching:
            logger.debug(f"[Pass {pass_num}] Redis cache hit for doc {doc_id}")
            payload = RelationalExtractionPayload.model_validate(cached_data)
            return payload.relations, 0.0, 0, 0

        system_prompt, user_prompt = ExtractionPromptManager.get_prompt(
            title=title,
            content=content,
            context_block=context_block,
            symbols=symbols,
            version=self.prompt_version,
        )

        logger.debug(
            f"[Pass {pass_num} Exec] Doc {doc_id} | Title len: {len(title)} | "
            f"Content len: {len(content)} | Symbols: {symbols}"
        )

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            response_schema=RelationalExtractionPayload.model_json_schema(),
            document_hash=content_hash,
        )

        async with self._semaphore:
            resp = await self.llm_client.extract_structured(request)

        if not resp.is_success:
            logger.error(f"[Pass {pass_num}] Inference failed for doc {doc_id}: {resp.error}")
            return [], resp.telemetry.latency_seconds, resp.telemetry.prompt_tokens, resp.telemetry.completion_tokens

        raw_text = resp.raw_content.strip()
        logger.info(f"[Pass {pass_num} Raw Output - Doc {doc_id}] {raw_text}")

        try:
            payload = RelationalExtractionPayload.model_validate(resp.parsed_payload)
            if not payload.relations:
                logger.warning(f"[Pass {pass_num}] Doc {doc_id} returned an EMPTY relations list.")
            return payload.relations, resp.telemetry.latency_seconds, resp.telemetry.prompt_tokens, resp.telemetry.completion_tokens
        except Exception as e: #noqa: BLE001
            logger.error(
                f"[Pass {pass_num}] Pydantic validation failed for doc {doc_id}: {e}\nRaw payload: {resp.parsed_payload}"
            )
            return [], resp.telemetry.latency_seconds, resp.telemetry.prompt_tokens, resp.telemetry.completion_tokens

    async def process_document(
        self,
        document_id: str,
        title: str,
        content: str,
        symbols: list[str] | None = None,
        caching: bool = True,
    ) -> ExtractionResult | None:
        """Executes the Target-Anchored N-Pass reasoning pipeline for a single document."""
        start_time = time.time()
        result_id = self._generate_deterministic_id(document_id)

        if self.repository.exists(result_id) and caching:
            logger.debug(f"Document {document_id} already processed with {self.max_passes} passes. Skipping.")
            return self.repository.find_by_id(result_id)

        safe_content = content[:8000] if content else ""
        if not safe_content.strip():
            logger.warning(f"Doc {document_id} has EMPTY content! Aborting extraction.")
            return None

        total_latency = 0.0
        total_in_tokens = 0
        total_out_tokens = 0

        accumulated_relations: list[GraphRelation] = []
        seen_edge_keys: set[str] = set()

        # Execute iterative reasoning loop
        for pass_num in range(1, self.max_passes + 1):
            context_block = self._format_context_block(accumulated_relations, pass_num)
            raw_relations, p_lat, p_in, p_out = await self._execute_pass(
                title=title,
                content=safe_content,
                context_block=context_block,
                pass_num=pass_num,
                doc_id=document_id,
                symbols=symbols,
                caching=caching,
            )

            total_latency += p_lat
            total_in_tokens += p_in
            total_out_tokens += p_out

            # FILTERING
            valid_pass_relations = self._filter_and_deduplicate(
                raw_relations=raw_relations,
                seen_edge_keys=seen_edge_keys,
                doc_id=document_id,
            )
            accumulated_relations.extend(valid_pass_relations)

            # Early Exit 1: If Pass 1 yielded 0 valid relations, stop immediately
            if pass_num == 1 and not accumulated_relations:
                logger.warning(f"[Early Exit] Doc {document_id} yielded 0 valid relations on Pass 1. Skipping subsequent passes.")
                break

            # Early Exit 2: Stop as soon as target STOCK entity is reached in valid relations
            has_stock_entity = any(
                r.subject.entity_type in (EntityType.STOCK, "STOCK") or 
                r.object.entity_type in (EntityType.STOCK, "STOCK")
                for r in valid_pass_relations
            )
            if has_stock_entity:
                logger.info(f"[Early Exit] Doc {document_id} reached target STOCK entity on Pass {pass_num}. Stopping reasoning chain.")
                break

        metadata = ExtractionMetadata(
            model_name=self.llm_client.client_name,
            prompt_version=self.prompt_version,
            total_passes=self.max_passes,
            total_latency_seconds=round(time.time() - start_time, 4),
            total_input_tokens=total_in_tokens,
            total_output_tokens=total_out_tokens,
        )

        result = ExtractionResult(
            id=result_id,
            document_id=document_id,
            relations=accumulated_relations,
            metadata=metadata,
        )

        self.repository.save(result)
        self.publisher.publish(self.output_kafka_topic, result, key=result.id)

        logger.info(
            f"Doc {document_id} completed in {metadata.total_latency_seconds}s across {self.max_passes} passes "
            f"({len(accumulated_relations)} unique graph relations discovered)"
        )
        return result

    async def process_batch(
        self, documents: list[dict[str, Any]]
    ) -> list[ExtractionResult]:
        """Executes concurrent N-pass batch processing for historical backfills."""
        if not documents:
            return []

        logger.info(f"Starting {self.max_passes}-pass batch extraction for {len(documents)} documents...")
        start_time = time.time()

        tasks = [
            self.process_document(
                document_id=str(doc.get("id") or doc.get("fingerprint") or doc.get("_id") or ""),
                title=str(doc.get("title", "")),
                content=str(doc.get("content", "")),
                symbols=doc.get("symbols"),
            )
            for doc in documents
            if doc.get("content")
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_results: list[ExtractionResult] = []
        for r in results:
            if isinstance(r, ExtractionResult):
                successful_results.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Unhandled exception during batch execution: {r!s}")

        self.publisher.flush(timeout=10.0)

        total_duration = round(time.time() - start_time, 2)
        logger.info(
            f"Batch completed: {len(successful_results)}/{len(documents)} docs processed "
            f"in {total_duration}s (Avg: {round(total_duration / max(len(successful_results), 1), 2)}s/doc)"
        )
        return successful_results

    async def test_document(
        self,
        document_id: str,
        title: str,
        content: str,
        symbols: list[str] | None = None,
        caching: bool = False,
    ) -> ExtractionResult | None:
        """Executes the Target-Anchored pipeline for testing without database persistence."""
        start_time = time.time()

        safe_content = content[:8000] if content else ""
        if not safe_content.strip():
            logger.warning(f"Doc {document_id} has EMPTY content! Aborting extraction.")
            return None

        total_latency = 0.0
        total_in_tokens = 0
        total_out_tokens = 0

        accumulated_relations: list[GraphRelation] = []
        seen_edge_keys: set[str] = set()

        for pass_num in range(1, self.max_passes + 1):
            context_block = self._format_context_block(accumulated_relations, pass_num)
            raw_relations, p_lat, p_in, p_out = await self._execute_pass(
                title=title,
                content=safe_content,
                context_block=context_block,
                pass_num=pass_num,
                doc_id=document_id,
                symbols=symbols,
                caching=caching,
            )

            total_latency += p_lat
            total_in_tokens += p_in
            total_out_tokens += p_out

            # Filtering
            valid_pass_relations = self._filter_and_deduplicate(
                raw_relations=raw_relations,
                seen_edge_keys=seen_edge_keys,
                doc_id=document_id,
            )
            accumulated_relations.extend(valid_pass_relations)

            if pass_num == 1 and not accumulated_relations:
                logger.warning(f"[Early Exit] Doc {document_id} yielded 0 valid relations on Pass 1. Skipping subsequent passes.")
                break

            has_stock_entity = any(
                r.subject.entity_type in (EntityType.STOCK, "STOCK") or 
                r.object.entity_type in (EntityType.STOCK, "STOCK")
                for r in valid_pass_relations
            )
            if has_stock_entity:
                logger.info(f"[Early Exit] Doc {document_id} reached target STOCK entity on Pass {pass_num}. Stopping reasoning chain.")
                break

        metadata = ExtractionMetadata(
            model_name=self.llm_client.client_name,
            prompt_version=self.prompt_version,
            total_passes=self.max_passes,
            total_latency_seconds=round(time.time() - start_time, 4),
            total_input_tokens=total_in_tokens,
            total_output_tokens=total_out_tokens,
        )

        result = ExtractionResult(
            id="test",
            document_id=document_id,
            relations=accumulated_relations,
            metadata=metadata,
        )

        logger.info(
            f"Doc {document_id} completed in {metadata.total_latency_seconds}s across {self.max_passes} passes "
            f"({len(accumulated_relations)} unique graph relations discovered)"
        )
        return result
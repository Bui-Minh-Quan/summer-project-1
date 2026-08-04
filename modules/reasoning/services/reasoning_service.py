"""
Reasoning Service Orchestrator.
Combines Graph Data, Market Data, and LLM Inference into a single pipeline.
"""

import asyncio
import logging

from modules.reasoning.llm.vllm_client import VLLMClient
from modules.reasoning.models.schema import ReasoningRequest, ReasoningResponse
from modules.reasoning.prompts.templates import build_trr_prompt
from modules.reasoning.repository.graph_query import GraphRepository
from modules.reasoning.repository.market_query import MarketRepository

logger = logging.getLogger("reasoning_service")


class ReasoningService:
    def __init__(self):
        self.graph_repo = GraphRepository()
        self.market_repo = MarketRepository()
        self.llm_client = VLLMClient()

    async def close(self):
        """Clean up database connections."""
        await self.graph_repo.close()
        await self.market_repo.close()

    async def analyze_trend(self, request: ReasoningRequest) -> ReasoningResponse:
        """
        Executes the full TRR pipeline for a given stock and date.
        """
        target_date_str = request.date.strftime("%Y-%m-%d")
        logger.info(f"Starting TRR analysis for {request.symbol} at {target_date_str}")
        
        # 1. Fetch data concurrently
        graph_task = self.graph_repo.get_trr_subgraph(
            symbol=request.symbol, 
            target_date=request.date
        )
        market_task = self.market_repo.get_recent_market_data(
            symbol=request.symbol, 
            target_date=request.date
        )
        
        graph_data, market_data = await asyncio.gather(graph_task, market_task)
        logger.info(f"Retrieved {len(graph_data)} graph edges and {len(market_data)} market records.")

        # 2. Synthesize Prompt
        messages = build_trr_prompt(
            symbol=request.symbol,
            target_date=target_date_str,
            graph_data=graph_data,
            market_data=market_data
        )

        # 3. Call LLM
        response = await self.llm_client.generate_structured_reasoning(messages)
        
        # 4. Final verification: Ensure the LLM didn't hallucinate the wrong symbol/date
        if response.symbol != "ERROR":
            response.symbol = request.symbol
            response.target_date = target_date_str
            
        return response
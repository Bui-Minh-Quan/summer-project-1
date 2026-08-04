"""
Knowledge Graph Retrieval for TRR Framework.
Executes temporal-decay pruning directly in Cypher to extract G_TRR.
"""

import logging
from datetime import datetime
from typing import Any

from neo4j import AsyncGraphDatabase

from modules.reasoning.config import config

logger = logging.getLogger("reasoning_graph")


class GraphRepository:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            config.neo4j_uri, 
            auth=(config.neo4j_user, config.neo4j_password)
        )
        # Lambda sets the half-life of news. 
        # A lambda of 0.1 means news loses ~63% of its weight after 10 days.
        self.decay_lambda = 0.1

    async def close(self):
        await self.driver.close()

    async def get_trr_subgraph(
        self, symbol: str, target_date: datetime, top_k: int = 15
    ) -> list[dict[str, Any]]:
        """
        Retrieves the pruned TRR graph (G_TRR) using native Cypher temporal decay.
        Returns paths as structured tuples.
        """
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Cypher query that implements the TRR Attention/Decay mechanism natively
        query = """
        MATCH (s:Stock {symbol: $symbol})-[r]-(event)
        
        // 1. Filter out future events (no lookahead bias) and extremely old events
        WHERE event.timestamp <= datetime($target_date)
          AND duration.inDays(datetime(event.timestamp), datetime($target_date)).days <= $lookback
          
        // 2. Calculate time delta in days
        WITH s, r, event, 
             duration.inDays(datetime(event.timestamp), datetime($target_date)).days AS delta_t
             
        // 3. Apply exponential time decay: exp(-lambda * delta_t)
        // Multiply by an engagement multiplier if available, else 1.0
        WITH s, r, event, delta_t,
             exp(-1.0 * $lambda_val * delta_t) * coalesce(event.total_engagement, 1.0) AS attention_score
             
        // 4. Order by the highest attention score (most recent & impactful)
        ORDER BY attention_score DESC
        LIMIT $top_k
        
        // 5. Format as Tuples for LLM Reasoning
        RETURN 
            labels(event)[0] AS subject_type,
            coalesce(event.title, event.content, event.id) AS subject_value,
            type(r) AS relation,
            s.symbol AS object,
            event.timestamp AS event_date,
            attention_score,
            delta_t
        """
        
        records = []
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query, 
                    symbol=symbol, 
                    target_date=f"{date_str}T00:00:00Z",
                    lookback=config.lookback_days,
                    lambda_val=self.decay_lambda,
                    top_k=top_k
                )
                async for record in result:
                    records.append({
                        "subject_type": record["subject_type"],
                        "subject": record["subject_value"],
                        "relation": record["relation"],
                        "object": record["object"],
                        "date": str(record["event_date"])[:10],
                        "attention_score": round(record["attention_score"], 4),
                        "days_ago": record["delta_t"]
                    })
        except Exception as e: #noqa: BLE001
            logger.error(f"Failed to retrieve TRR subgraph for {symbol}: {e}")
            
        return records
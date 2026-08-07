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
        # FIX: Removed `date_str = target_date.strftime("%Y-%m-%d")`
        
        query = """
        MATCH (s:Entity {name: $symbol, entity_type: 'STOCK'})-[r:IMPACTS]-(other:Entity)
        WHERE r.published_at <= datetime($target_date)
          AND duration.inDays(r.published_at, datetime($target_date)).days <= $lookback
        WITH s, r, other, 
             duration.inDays(r.published_at, datetime($target_date)).days AS delta_t
        WITH s, r, other, delta_t,
             exp(-1.0 * $lambda_val * delta_t) * coalesce(r.confidence, 1.0) AS attention_score
        ORDER BY attention_score DESC
        LIMIT $top_k
        RETURN 
            other.entity_type AS subject_type,
            other.name AS subject_value,
            r.relation AS relation,
            s.name AS object,
            r.published_at AS event_date,
            attention_score,
            delta_t
        """
        
        records = []
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query, 
                    symbol=symbol, 
                    # FIX: Pass the exact timestamp, preserving hours and minutes
                    target_date=target_date.isoformat(), 
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
        except Exception as e: # noqa: BLE001
            logger.error(f"Failed to retrieve TRR subgraph for {symbol}: {e}")
            
        return records
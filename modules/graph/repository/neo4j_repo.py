"""
Asynchronous Neo4j repository executing idempotent Cypher UNWIND batch ingestion.
"""

import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from modules.graph.models.models import CanonicalEdge

logger = logging.getLogger(__name__)


class Neo4jRepository:
    """Asynchronous Neo4j driver wrapper executing idempotent Cypher UNWIND batch ingestion."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "secretpassword",
        database: str = "neo4j",
    ) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Initialize the async Neo4j driver connection."""
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            logger.info("Connected to async Neo4j database.")

    async def close(self) -> None:
        """Close driver network connections."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Closed Neo4j driver connection.")

    async def health_check(self) -> bool:
        """Verify connectivity to Neo4j instance."""
        if not self._driver:
            await self.connect()
        try:
            assert self._driver is not None
            await self._driver.verify_connectivity()
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Neo4j health check failed: {e!s}")
            return False

    async def ensure_constraints(self) -> None:
        """Pre-initialize graph uniqueness constraints and indexes."""
        if not self._driver:
            await self.connect()

        queries = [
            "CREATE CONSTRAINT idx_entity_canonical_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_id IS UNIQUE;",
            "CREATE INDEX idx_entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);",
            "CREATE INDEX idx_entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type);",
            "CREATE INDEX idx_rel_impacts_doc_id IF NOT EXISTS FOR ()-[r:IMPACTS]-() ON (r.doc_id);",
            "CREATE INDEX idx_rel_impacts_pub_at IF NOT EXISTS FOR ()-[r:IMPACTS]-() ON (r.published_at);",
        ]

        assert self._driver is not None
        async with self._driver.session(database=self.database) as session:
            for q in queries:
                try:
                    await session.run(q)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Notice executing Neo4j constraint/index query: {e!s}")

        logger.info("✅ Neo4j constraints and indexes verified.")

    async def save_edge_batch(self, edges: list[CanonicalEdge]) -> int:
        """
        Executes a single high-performance UNWIND transaction in Neo4j.
        Guarantees idempotent node and relationship creation.
        """
        if not edges:
            return 0

        if not self._driver:
            await self.connect()

        cypher_query = """
        UNWIND $batch AS item

        // 1. Merge Subject Node
        MERGE (sub:Entity {canonical_id: item.subject_id})
        ON CREATE SET 
            sub.name = item.subject_name,
            sub.entity_type = item.subject_type,
            sub.created_at = datetime()
        ON MATCH SET 
            sub.name = item.subject_name

        // 2. Merge Object Node
        MERGE (obj:Entity {canonical_id: item.object_id})
        ON CREATE SET 
            obj.name = item.object_name,
            obj.entity_type = item.object_type,
            obj.created_at = datetime()
        ON MATCH SET 
            obj.name = item.object_name

        // 3. Merge Idempotent Relationship
        MERGE (sub)-[r:IMPACTS {edge_id: item.edge_id}]->(obj)
        ON CREATE SET 
            r.relation = item.relation,
            r.market_impact = item.market_impact,
            r.confidence = item.confidence,
            r.reasoning = item.reasoning,
            r.published_at = datetime(item.published_at),
            r.doc_id = item.doc_id
        ON MATCH SET
            r.confidence = item.confidence,
            r.published_at = datetime(item.published_at)
        """

        batch_payload = [e.model_dump(mode="json") for e in edges]

        assert self._driver is not None
        async with self._driver.session(database=self.database) as session:
            result = await session.run(cypher_query, batch=batch_payload)
            summary = await result.consume()
            counters = summary.counters
            logger.debug(
                f"Neo4j UNWIND Batch executed: {len(edges)} edges processed | "
                f"Nodes created: {counters.nodes_created}, Rels created: {counters.relationships_created}"
            )
            return len(edges)

    async def count_nodes(self) -> int:
        """Return total count of Entity nodes in Neo4j."""
        if not self._driver:
            await self.connect()
        assert self._driver is not None
        async with self._driver.session(database=self.database) as session:
            res = await session.run("MATCH (n:Entity) RETURN count(n) AS cnt")
            record = await res.single()
            return record["cnt"] if record else 0

    async def count_relationships(self) -> int:
        """Return total count of IMPACTS relationships in Neo4j."""
        if not self._driver: # type: ignore
            await self.connect()
        assert self._driver is not None
        async with self._driver.session(database=self.database) as session:
            res = await session.run("MATCH ()-[r:IMPACTS]->() RETURN count(r) AS cnt")
            record = await res.single()
            return record["cnt"] if record else 0
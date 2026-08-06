"""
Integration tests for GraphService and Neo4jRepository.
Runs against local containerized Neo4j database (bolt://localhost:7687).
"""

import pytest
import pytest_asyncio

from modules.graph.config import config
from modules.graph.repository.neo4j_repo import Neo4jRepository
from modules.graph.services.graph_service import GraphService


@pytest_asyncio.fixture
async def neo4j_service():
    """Fixture initializing real Neo4j repository connection and GraphService."""
    repo = Neo4jRepository(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    await repo.connect()
    await repo.ensure_constraints()

    # Clean test graph before running
    async with repo._driver.session(database=repo.database) as session:
        await session.run("MATCH (n:Entity) DETACH DELETE n")

    service = GraphService(repo=repo, confidence_threshold=0.6)

    yield service

    # Cleanup after test run
    async with repo._driver.session(database=repo.database) as session:
        await session.run("MATCH (n:Entity) DETACH DELETE n")
    await repo.close()


@pytest.mark.asyncio
async def test_process_batch_and_idempotency(neo4j_service: GraphService) -> None:
    mock_payload = {
        "document_id": "test_doc_001",
        "published_at": "2026-08-02T02:00:00Z",
        "relations": [
            {
                "reasoning": "VPBank tăng lãi suất giúp huy động vốn tốt hơn.",
                "subject": {"name": "VPB", "entity_type": "STOCK"},
                "relation": "tăng lãi suất huy động",
                "object": {"name": "Ngành Ngân hàng", "entity_type": "SECTOR"},
                "market_impact": "POSITIVE",
                "confidence": 0.95,
            },
            {
                # Low confidence edge -> Should be DROPPED
                "reasoning": "Tin đồn không rõ nguồn gốc.",
                "subject": {"name": "FPT", "entity_type": "STOCK"},
                "relation": "bị ảnh hưởng",
                "object": {"name": "Thị trường", "entity_type": "OTHER"},
                "market_impact": "NEGATIVE",
                "confidence": 0.40,
            },
            {
                # Invalid name starting with number -> Should be DROPPED
                "reasoning": "Số liệu thống kê.",
                "subject": {"name": "100 doanh nghiệp", "entity_type": "OTHER"},
                "relation": "báo cáo lợi nhuận",
                "object": {"name": "VIC", "entity_type": "STOCK"},
                "market_impact": "NEUTRAL",
                "confidence": 0.90,
            },
        ],
    }

    # 1. First Execution
    report1 = await neo4j_service.process_batch([mock_payload])
    assert report1.total_raw_edges == 3
    assert report1.total_valid_edges == 1  # 2 dropped by filters
    assert report1.saved_edges == 1

    # Verify Neo4j state
    node_count = await neo4j_service.repo.count_nodes()
    rel_count = await neo4j_service.repo.count_relationships()
    assert node_count == 2  # VPB and Ngành Ngân hàng
    assert rel_count == 1

    # 2. Second Execution (Idempotency check)
    report2 = await neo4j_service.process_batch([mock_payload])
    assert report2.saved_edges == 1

    # Node and relationship count in Neo4j MUST NOT increase
    assert await neo4j_service.repo.count_nodes() == 2
    assert await neo4j_service.repo.count_relationships() == 1
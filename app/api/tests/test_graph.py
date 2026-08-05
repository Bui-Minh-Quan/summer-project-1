import io
from unittest.mock import AsyncMock, MagicMock, patch


def test_extract_knowledge_graph_txt_file(client):
    fake_txt = io.BytesIO(b"FPT corporate revenue grew 15% in 2026.")

    mock_relation = MagicMock()
    mock_relation.subject.name = "FPT"
    mock_relation.subject.entity_type.value = "STOCK"
    mock_relation.object.name = "Revenue"
    mock_relation.object.entity_type.value = "OTHER"
    mock_relation.relation = "increased"
    mock_relation.market_impact.value = "POSITIVE"
    mock_relation.reasoning = "Revenue grew 15%"
    mock_relation.confidence = 0.95

    mock_result = MagicMock()
    mock_result.relations = [mock_relation]
    mock_result.metadata.model_dump.return_value = {"latency": 0.5}

    with patch(
        "modules.extraction.services.extraction_service.ExtractionService.test_document",
        AsyncMock(return_value=mock_result),
    ), patch("modules.extraction.cache.cache.LLMExtractionCache.connect", AsyncMock()):

        response = client.post(
            "/api/v1/graph/extract",
            files={"file": ("report.txt", fake_txt, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["source"] == "FPT"
        assert data["edges"][0]["target"] == "Revenue"
        assert data["edges"][0]["impact"] == "POSITIVE"


def test_extract_knowledge_graph_invalid_extension(client):
    fake_img = io.BytesIO(b"fake image data")

    response = client.post(
        "/api/v1/graph/extract",
        files={"file": ("chart.png", fake_img, "image/png")},
    )

    assert response.status_code == 400
    assert "Only .pdf and .txt files are supported" in response.json()["detail"]
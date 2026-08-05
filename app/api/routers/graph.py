import io
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from modules.extraction.cache.cache import LLMExtractionCache
from modules.extraction.llm.vllm_clients import VLLMClient

# Import Module 2 extraction service
from modules.extraction.services.extraction_service import ExtractionService
from pypdf import PdfReader

from core.config import settings

router = APIRouter()

llm_client = VLLMClient(base_url=settings.MLOPS_API_URL.replace("8001", "8000") + "/v1") 
cache = LLMExtractionCache(redis_url=settings.REDIS_URL)


@router.post("/extract")
async def extract_knowledge_graph(
    file: Annotated[UploadFile, File(description="Uploaded PDF or TXT file")]
):
    """Feature 3: On-the-fly Knowledge Graph Extraction from PDF/TXT."""
    
    filename = file.filename or "uploaded_document"
    content = ""

    if filename.lower().endswith(".pdf"):
        try:
            pdf_bytes = await file.read()
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e!s}")

    elif filename.lower().endswith(".txt"):
        content = (await file.read()).decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported.")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Document contains no extractable text.")

    # Mock dependencies for testing mode
    class DummyRepo:
        def exists(self, id: str) -> bool: return False
        def save(self, entity: object) -> None: pass

    class DummyPublisher:
        def publish(self, topic: str, entity: object, key: str | None = None) -> None: pass

    service = ExtractionService(
        llm_client=llm_client,
        cache=cache,
        repository=DummyRepo(),  # type: ignore[arg-type]
        publisher=DummyPublisher(),  # type: ignore[arg-type]
        prompt_version="v1.0",
        max_passes=2
    )

    await cache.connect()

    result = await service.test_document(
        document_id=str(uuid.uuid4()),
        title=filename,  # Guaranteed to be str
        content=content,
        symbols=[],
        caching=False
    )

    if not result:
        raise HTTPException(status_code=500, detail="Graph extraction failed or returned no relations.")

    nodes_dict = {}
    edges = []

    for rel in result.relations:
        sub = rel.subject
        obj = rel.object

        if sub.name not in nodes_dict:
            nodes_dict[sub.name] = {"id": sub.name, "label": sub.name, "type": sub.entity_type.value}
        if obj.name not in nodes_dict:
            nodes_dict[obj.name] = {"id": obj.name, "label": obj.name, "type": obj.entity_type.value}

        edges.append({
            "source": sub.name,
            "target": obj.name,
            "label": rel.relation,
            "impact": rel.market_impact.value,
            "reasoning": rel.reasoning,
            "confidence": rel.confidence
        })

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges,
        "metadata": result.metadata.model_dump()
    }
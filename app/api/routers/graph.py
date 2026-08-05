import io
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader

from modules.extraction.services.extraction_service import ExtractionService
from modules.extraction.llm.vllm_clients import VLLMClient
from modules.extraction.cache.cache import LLMExtractionCache
from core.config import settings

router = APIRouter()

# Initialize the vLLM client and Redis cache for the Extraction Engine
llm_client = VLLMClient(base_url=settings.MLOPS_API_URL.replace("8001", "8000") + "/v1") 
cache = LLMExtractionCache(redis_url=settings.REDIS_URL)

@router.post("/extract")
async def extract_knowledge_graph(file: UploadFile = File(...)):
    """Feature 3: On-the-fly Knowledge Graph Extraction from PDF/TXT."""
    
    # 1. Parse the uploaded file
    content = ""
    if file.filename.endswith(".pdf"):
        try:
            pdf_bytes = await file.read()
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
            
    elif file.filename.endswith(".txt"):
        content = (await file.read()).decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported.")
        
    if not content.strip():
        raise HTTPException(status_code=400, detail="Document contains no extractable text.")
        
    # 2. Mock dependencies since we are bypassing database staging
    class DummyRepo:
        def exists(self, id): return False
        def save(self, entity): pass
        
    class DummyPublisher:
        def publish(self, topic, entity, key): pass

    service = ExtractionService(
        llm_client=llm_client,
        cache=cache,
        repository=DummyRepo(),
        publisher=DummyPublisher(),
        prompt_version="v1.0",
        max_passes=2
    )
    
    await cache.connect()
    
    # 3. Call the engine in testing mode (no database saves)
    result = await service.test_document(
        document_id=str(uuid.uuid4()),
        title=file.filename,
        content=content,
        symbols=[], 
        caching=False # Force a fresh extraction run
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Graph extraction failed or returned no relations.")
        
    # 4. Map the Pydantic schema into a clean JSON structure for React Force Graph
    nodes_dict = {}
    edges = []
    
    for rel in result.relations:
        sub = rel.subject
        obj = rel.object
        
        # Deduplicate nodes by name
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
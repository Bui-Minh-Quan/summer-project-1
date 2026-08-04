"""
FastAPI Server for Module 4 Reasoning Engine.
Exposes the TRR reasoning pipeline via an HTTP endpoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from modules.reasoning.models.schema import ReasoningRequest, ReasoningResponse
from modules.reasoning.services.reasoning_service import ReasoningService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reasoning_api")

service: ReasoningService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes ReasoningService and manages connection cleanup."""
    global service
    logger.info("Initializing Reasoning Service resources...")
    service = ReasoningService()
    yield
    logger.info("Closing Reasoning Service database connections...")
    if service:
        await service.close()


app = FastAPI(
    title="Financial AI Platform - TRR Reasoning Engine API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "reasoning_engine"}


@app.post("/analyze", response_model=ReasoningResponse)
async def analyze_stock_trend(request: ReasoningRequest) -> ReasoningResponse:
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Reasoning Service is not initialized.",
        )

    try:
        response = await service.analyze_trend(request)
        return response
    except Exception as e: #noqa: BLE001
        logger.error(f"Reasoning API endpoint failure: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failure: {e!s}")
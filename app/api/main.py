import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import from_url as redis_from_url

from app.api.core.config import settings
from app.api.jobs.populate_actuals import populate_actuals
from app.api.routers import graph, predictions, sentiment, stream
from app.api.routers.stream import consume_kafka_market_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_main")

db_client: AsyncIOMotorClient | None = None
consumer_task: asyncio.Task[Any] | None = None
scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client, consumer_task, scheduler

    # 1. Start MongoDB Client
    db_client = AsyncIOMotorClient(settings.MONGO_URI)
    app.state.db = db_client[settings.MONGO_DB]
    logger.info("✅ MongoDB client initialized.")

    # 2. Start Redis Cache with Connection Health-Check
    # 2. Start Redis Cache with Connection Health-Check
    try:
        redis_client = redis_from_url(settings.REDIS_URL)
        pong = await redis_client.ping()
        logger.info(f"🔴 [REDIS CACHE INIT SUCCESS] Connected to Redis at {settings.REDIS_URL}. Ping: {pong}")
        FastAPICache.init(RedisBackend(redis_client), prefix="api-cache")
    except Exception:
        logger.exception("❌ [REDIS CACHE INIT ERROR] Failed to initialize FastAPICache with Redis")

    # 3. Start Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(populate_actuals, "cron", hour=16, minute=0)
    scheduler.start()

    # 4. Launch Kafka WebSocket Consumer
    consumer_task = asyncio.create_task(consume_kafka_market_data())

    yield

    # Safe Teardown
    if consumer_task:
        consumer_task.cancel()

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)

    if db_client:
        db_client.close()


app = FastAPI(title="Financial AI Gateway API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Knowledge Graph"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["Sentiment"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["Streaming"])
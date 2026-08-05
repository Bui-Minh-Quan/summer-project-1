import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import from_url as redis_from_url
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import settings
from routers.stream import consume_kafka_market_data
from routers import predictions, graph, stream, sentiment
from jobs.populate_actuals import populate_actuals

db_client = None
consumer_task = None
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client, consumer_task, scheduler
    
    # 1. Start MongoDB
    db_client = AsyncIOMotorClient(settings.MONGO_URI)
    app.state.db = db_client[settings.MONGO_DB]
    
    # 2. Start Redis Cache
    redis = redis_from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="api-cache")

    # 3. Start Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(populate_actuals, 'cron', hour=16, minute=0)
    scheduler.start()
    
    # 4. Launch Kafka WebSocket Consumer
    consumer_task = asyncio.create_task(consume_kafka_market_data())
    
    yield
    
    # Clean up resources safely
    if consumer_task:
        consumer_task.cancel()
    
    # Check running state before shutting down
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        
    db_client.close()

app = FastAPI(title="Financial AI Gateway API", lifespan=lifespan)

app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Knowledge Graph"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["Sentiment"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["Streaming"])
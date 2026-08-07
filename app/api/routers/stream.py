import asyncio
import json
import logging
import os

from confluent_kafka import Consumer, KafkaError
from fastapi import (
    APIRouter,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

logger = logging.getLogger("stream_api")
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        symbol = symbol.upper()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = []
        self.active_connections[symbol].append(websocket)
        logger.info(f"Client connected to stream for {symbol}")

    def disconnect(self, websocket: WebSocket, symbol: str):
        symbol = symbol.upper()
        if symbol in self.active_connections:
            self.active_connections[symbol].remove(websocket)
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]
        logger.info(f"Client disconnected from stream for {symbol}")

    async def broadcast(self, symbol: str, message: dict):
        symbol = symbol.upper()
        if symbol in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[symbol]:
                try:
                    await connection.send_json(message)
                except Exception: # noqa: BLE001
                    dead_connections.append(connection)
            
            for dead in dead_connections:
                self.disconnect(dead, symbol)

manager = ConnectionManager()

async def consume_kafka_market_data():
    """Background worker that listens to Kafka and broadcasts to active WebSockets."""
    kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    conf = {
        'bootstrap.servers': kafka_broker,
        'group.id': 'fastapi-websocket-gateway',
        'auto.offset.reset': 'latest',
        'enable.auto.commit': True
    }
    consumer = Consumer(conf)
    consumer.subscribe(["market-ohlcv"]) 
    logger.info("WebSocket Kafka Consumer started listening to 'market-ohlcv'")
    
    try:
        while True:
            msg = await asyncio.to_thread(consumer.poll, 0.5)
            
            if msg is None:
                await asyncio.sleep(0.05)
                continue
                
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error(f"Kafka Stream Error: {msg.error()}")
                continue
                
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                symbol = payload.get("symbol") or payload.get("ticker")
                if symbol:
                    await manager.broadcast(symbol, payload)
            except Exception as e: # noqa: BLE001
                logger.error(f"Failed to broadcast Kafka message: {e}")
                
    except asyncio.CancelledError:
        logger.info("Kafka streaming task cancelled.")
    finally:
        consumer.close()

# ============================================================================
# NEW: REST ENDPOINT TO FETCH HISTORICAL CHART BARS
# ============================================================================

@router.get("/history/{symbol}")
async def get_market_history(
    symbol: str, 
    request: Request, 
    limit: int = Query(30, ge=5, le=100)
):
    """Fetches recent historical OHLCV bars from silver_market_quotes for chart hydration."""
    db = request.app.state.db
    symbol = symbol.upper().strip()

    quotes = await db["silver_market_quotes"].find(
        {"symbol": symbol}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)

    if not quotes:
        # Fallback to empty list if no historical quotes exist yet
        return []

    # Reverse to chronological order (oldest -> newest) for plotting
    quotes.reverse()

    results = []
    for q in quotes:
        ts = q.get("timestamp")
        time_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        results.append({
            "time": time_str,
            "open": float(q.get("open", 0.0)),
            "high": float(q.get("high", 0.0)),
            "low": float(q.get("low", 0.0)),
            "close": float(q.get("close", 0.0)),
            "volume": float(q.get("volume", 0.0)),
            "symbol": symbol
        })

    return results

@router.websocket("/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket, symbol)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)

@router.get("/status")
async def get_stream_status():
    return {"status": "streaming active", "websocket_url": "ws://localhost:8000/api/v1/stream/ws"}
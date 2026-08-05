import asyncio
import json
import logging
import os

from confluent_kafka import Consumer, KafkaError
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("stream_api")
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps a stock symbol to a list of active WebSocket connections
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
            
            # Clean up dropped connections
            for dead in dead_connections:
                self.disconnect(dead, symbol)

manager = ConnectionManager()

async def consume_kafka_market_data():
    """
    Background worker that listens to Kafka and broadcasts to active WebSockets.
    """
    kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")
    conf = {
        'bootstrap.servers': kafka_broker,
        'group.id': 'fastapi-websocket-gateway',
        'auto.offset.reset': 'latest',
        'enable.auto.commit': True
    }
    consumer = Consumer(conf)
    
    # Subscribing to the topic established in Module 1 and 2
    consumer.subscribe(["market-ohlcv"]) 
    logger.info("WebSocket Kafka Consumer started listening to 'market-ohlcv'")
    
    try:
        while True:
            # Use asyncio.to_thread for the blocking poll() call to avoid freezing FastAPI
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
                
                # Support both Silver (symbol) and Bronze (ticker) schema keys
                symbol = payload.get("symbol") or payload.get("ticker")
                
                if symbol:
                    await manager.broadcast(symbol, payload)
            except Exception as e: # noqa: BLE001
                logger.error(f"Failed to broadcast Kafka message: {e}")
                
    except asyncio.CancelledError:
        logger.info("Kafka streaming task cancelled.")
    finally:
        consumer.close()

@router.websocket("/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    """
    Feature 4: Live market data ticker. 
    Frontend connects to: ws://localhost:8000/api/v1/stream/FPT
    """
    await manager.connect(websocket, symbol)
    try:
        while True:
            # Keep the socket open; we don't expect client messages, 
            # but waiting detects client disconnects gracefully.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)
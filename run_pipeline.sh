#!/bin/bash
echo "🚀 Starting Financial AI Platform..."

mkdir -p logs
ROOT_DIR=$(pwd)

# 1. Clean up stale Uvicorn processes
echo "🧹 Cleaning up existing API ports (8000, 8001, 8002)..."
fuser -k 8000/tcp 8001/tcp 8002/tcp >/dev/null 2>&1 || true
pkill -f uvicorn >/dev/null 2>&1 || true
sleep 1

# 2. Boot Docker services
echo "📦 Booting Docker containers..."
docker compose up -d --remove-orphans
docker compose -f docker-compose.llm.yml up -d

# 3. Wait for vLLM to become healthy
echo "⏳ Verifying vLLM server availability on port 8008..."
until curl -f -s http://localhost:8008/health > /dev/null; do
    echo "  Waiting for vLLM on http://localhost:8008/health..."
    sleep 30
done
echo "✅ vLLM is ready!"

# Clean shutdown handler
trap 'echo "🛑 Stopping all services..."; kill $(jobs -p) 2>/dev/null; exit' EXIT

# 4. Start internal APIs
echo "🧠 Starting ML API (port 8001)..."
PYTHONPATH="$ROOT_DIR" uvicorn modules.mlops.serving.api:app --port 8001 --reload > logs/mlops_api.log 2>&1 &

echo "🧠 Starting Reasoning API (port 8002)..."
PYTHONPATH="$ROOT_DIR" VLLM_URL="http://localhost:8008/v1" VLLM_BASE_URL="http://localhost:8008/v1" uvicorn modules.reasoning.api:app --port 8002 --reload > logs/reasoning_api.log 2>&1 &

# 5. Start Gateway API (Includes modules/extraction in PYTHONPATH)
echo "🌐 Starting Gateway API (port 8000)..."
(cd app/api && PYTHONPATH="$ROOT_DIR:$ROOT_DIR/app/api:$ROOT_DIR/modules/extraction" uvicorn main:app --port 8000 --reload) > logs/gateway_api.log 2>&1 &

sleep 3

# 6. Start Streaming Pipelines
echo "📡 Starting Module 1: Data Acquisition..."
(cd modules/acquisition && PYTHONPATH="" python documents_stream.py --mode continuous) > logs/mod1_docs.log 2>&1 &
(cd modules/acquisition && PYTHONPATH="" python market_stream.py --mode continuous) > logs/mod1_market.log 2>&1 &

echo "⚙️ Starting Module 2: Extraction & Features..."
(cd modules/extraction && PYTHONPATH="" python documents_stream.py --mode continuous --vllm-url http://localhost:8008/v1) > logs/mod2_docs.log 2>&1 &
(cd modules/extraction && PYTHONPATH="" python market_stream.py) > logs/mod2_market.log 2>&1 &

echo "🕸️ Starting Module 3: Graph Engine..."
(cd modules/graph && PYTHONPATH="" python graph_stream.py --mode continuous) > logs/mod3_graph.log 2>&1 &

echo ""
echo "✅ All services are up and running cleanly!"
echo "Press Ctrl+C to stop all background processes."
echo ""

wait
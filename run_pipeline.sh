#!/bin/bash
echo "🚀 Starting Financial AI Platform..."

mkdir -p logs

# 1. Export global environment variables
export ROOT_DIR="$(pwd)"
export PYTHONPATH="$ROOT_DIR"
export VLLM_URL="http://localhost:8008/v1"
export VLLM_BASE_URL="http://localhost:8008/v1"

# 2. Clean up stale Uvicorn processes
echo "🧹 Cleaning up existing API ports (8000, 8001, 8002)..."
fuser -k 8000/tcp 8001/tcp 8002/tcp >/dev/null 2>&1 || true
pkill -f uvicorn >/dev/null 2>&1 || true
sleep 1

# 3. Boot Docker infrastructure
echo "📦 Booting Docker containers..."
docker compose up -d --remove-orphans
docker compose -f docker-compose.llm.yml up -d

# 4. Wait for vLLM health check
echo "⏳ Verifying vLLM server availability on port 8008..."
until curl -f -s http://localhost:8008/health > /dev/null; do
    echo "  Waiting for vLLM model weights to load..."
    sleep 30
done
echo "✅ vLLM is ready!"

# Clean shutdown handler for all background processes
trap 'echo -e "\n🛑 Stopping all services..."; kill $(jobs -p) 2>/dev/null; exit' EXIT

# 5. Start APIs from the root directory
echo "🧠 Starting MLOps Serving API (port 8001)..."
uvicorn modules.mlops.serving.api:app --port 8001 --reload > logs/mlops_api.log 2>&1 &

echo "🧠 Starting Reasoning API (port 8002)..."
uvicorn modules.reasoning.api:app --port 8002 --reload > logs/reasoning_api.log 2>&1 &

echo "🌐 Starting Gateway API (port 8000)..."
uvicorn app.api.main:app --port 8000 --reload > logs/gateway_api.log 2>&1 &

sleep 3

# 6. Start Streaming Pipelines directly from root
echo "📡 Starting Module 1: Data Acquisition..."
python modules/acquisition/documents_stream.py --mode continuous > logs/mod1_docs.log 2>&1 &
python modules/acquisition/market_stream.py --mode continuous > logs/mod1_market.log 2>&1 &

echo "⚙️ Starting Module 2: Extraction & Features..."
python modules/extraction/documents_stream.py --mode continuous --vllm-url "$VLLM_URL" > logs/mod2_docs.log 2>&1 &
python modules/extraction/market_stream.py > logs/mod2_market.log 2>&1 &

echo "🕸️ Starting Module 3: Graph Engine..."
python modules/graph/graph_stream.py --mode continuous > logs/mod3_graph.log 2>&1 &

echo ""
echo "=================================================="
echo "✅ All services are up and running cleanly!"
echo "📁 Logs are saved in the 'logs/' folder."
echo "Press Ctrl+C to stop all background processes."
echo "=================================================="
echo ""

wait
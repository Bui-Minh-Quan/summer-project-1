#!/bin/bash
echo "🚀 Starting Financial AI Platform..."

mkdir -p logs
export ROOT_DIR="$(pwd)"
export PYTHONPATH="$ROOT_DIR"
export VLLM_URL="http://localhost:8008/v1"
export VLLM_BASE_URL="http://localhost:8008/v1"
export VLLM_MODEL_NAME="qwen-1.5b"

# 1. Clean up stale Uvicorn processes only
echo "🧹 Cleaning up existing API ports (8000, 8001, 8002)..."
fuser -k 8000/tcp 8001/tcp 8002/tcp >/dev/null 2>&1 || true
pkill -f uvicorn >/dev/null 2>&1 || true

# 2. Check if Docker infrastructure is already running
if ! curl -f -s http://localhost:8008/health > /dev/null; then
    echo "📦 Booting Docker containers (First-time or stopped state)..."
    docker compose up -d --no-recreate
    docker compose -f docker-compose.llm.yml up -d --no-recreate

    echo "⏳ Verifying vLLM availability on http://localhost:8008/health..."
    until curl -f -s http://localhost:8008/health > /dev/null; do
        echo "  Waiting for vLLM..."
        sleep 30
    done
else
    echo "⚡ Docker infrastructure & vLLM are already running! Skipping container boot."
fi

echo "✅ Infrastructure is ready!"

# Clean shutdown handler (Kills Python background processes)
trap 'echo -e "\n🛑 Stopping Python application processes..."; kill $(jobs -p) 2>/dev/null; exit' EXIT

# 3. Start internal APIs
echo "🧠 Starting MLOps Serving API (port 8001)..."
uvicorn modules.mlops.serving.api:app --port 8001 --reload > logs/mlops_api.log 2>&1 &

echo "🧠 Starting Reasoning API (port 8002)..."
uvicorn modules.reasoning.api:app --port 8002 --reload > logs/reasoning_api.log 2>&1 &

echo "🌐 Starting Gateway API (port 8000)..."
uvicorn app.api.main:app --port 8000 --reload > logs/gateway_api.log 2>&1 &

sleep 2

# 4. Start Streaming Pipelines
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
echo "✅ Application services running!"
echo "📁 Logs: 'tail -f logs/<service>.log'"
echo "Press Ctrl+C to stop app processes"
echo "=================================================="
echo ""

wait
#!/bin/bash
# ============================================================================
# llama.cpp Server Startup Script - Gemma2-2b for chat-default
# ============================================================================
# Starts the llama.cpp server on port 8002 with gemma2-2b-it model
#
# Usage: ./start_llamacpp.sh
# ============================================================================

set -euo pipefail

# Configuration
LLAMA_CPP_DIR="/LAB/@ai_hub/llama.cpp/build/bin"
MODEL_PATH="/LAB/@ai_hub/models/gguf-chat/gemma2-2b-it-Q4_K_M.gguf"
PORT=8002
HOST="0.0.0.0"
CTX_SIZE=2048
THREADS=6

# Disable CUDA to avoid GPU conflicts with Ollama
export CUDA_VISIBLE_DEVICES=""

# Check if model exists
if [[ ! -f "$MODEL_PATH" ]]; then
    echo "ERROR: Model not found at $MODEL_PATH"
    exit 1
fi

# Check if server binary exists
if [[ ! -f "$LLAMA_CPP_DIR/llama-server" ]]; then
    echo "ERROR: llama-server not found at $LLAMA_CPP_DIR/llama-server"
    exit 1
fi

# Check if port is already in use
if ss -tlnp | grep -q ":$PORT "; then
    echo "ERROR: Port $PORT is already in use"
    echo "Run: pkill -f llama-server"
    exit 1
fi

echo "Starting llama.cpp server..."
echo "  Model: $MODEL_PATH"
echo "  Port: $PORT"
echo "  Context: $CTX_SIZE"
echo "  Threads: $THREADS"
echo "  CUDA: Disabled (CPU-only mode)"

cd "$LLAMA_CPP_DIR"
exec ./llama-server \
    --model "$MODEL_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --ctx-size "$CTX_SIZE" \
    --threads "$THREADS" \
    --metrics \
    --n-gpu-layers 0

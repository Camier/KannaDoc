#!/bin/bash
# ============================================================================
# llama.cpp Server Stop Script
# ============================================================================
# Stops the llama.cpp server on port 8002
#
# Usage: ./stop_llamacpp.sh
# ============================================================================

set -euo pipefail

PORT=8002
PROCESS_NAME="llama-server"

# Find and kill the process
if pgrep -f "$PROCESS_NAME" > /dev/null; then
    echo "Stopping $PROCESS_NAME on port $PORT..."
    pkill -f "$PROCESS_NAME"
    sleep 2

    # Force kill if still running
    if pgrep -f "$PROCESS_NAME" > /dev/null; then
        echo "Force killing $PROCESS_NAME..."
        pkill -9 -f "$PROCESS_NAME"
    fi

    echo "Server stopped."
else
    echo "No $PROCESS_NAME process found running."
fi

# Verify port is free
if ss -tlnp | grep -q ":$PORT "; then
    echo "WARNING: Port $PORT is still in use!"
    ss -tlnp | grep ":$PORT "
else
    echo "Port $PORT is free."
fi

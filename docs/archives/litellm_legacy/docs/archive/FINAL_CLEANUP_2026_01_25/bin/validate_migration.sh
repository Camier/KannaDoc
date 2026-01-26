#!/usr/bin/env bash
#
# LiteLLM Migration Validation Script
#
# Validates migration from systemd to Docker deployment
#

set -euo pipefail

COMPOSE_DIR="/LAB/@litellm"
LITELLM_URL="http://127.0.0.1:4000"
MASTER_KEY="${LITELLM_MASTER_KEY:-}"

echo "=== LiteLLM Migration Validation ==="
echo ""

# Check .env file exists
echo "[1/6] Checking .env file..."
if [ -f "$COMPOSE_DIR/.env" ]; then
    echo "  ✅ .env exists"
else
    echo "  ❌ .env not found. Run: cp env.litellm .env.example && edit .env"
    exit 1
fi

# Check Docker is available
echo "[2/6] Checking Docker..."
if docker info >/dev/null 2>&1; then
    echo "  ✅ Docker is running"
else
    echo "  ❌ Docker is not available"
    exit 1
fi

# Check docker-compose syntax
echo "[3/6] Validating docker-compose.yml..."
cd "$COMPOSE_DIR"
if docker-compose config >/dev/null 2>&1; then
    echo "  ✅ docker-compose.yml is valid"
else
    echo "  ❌ docker-compose.yml has syntax errors"
    exit 1
fi

# Check ports are available
echo "[4/6] Checking port availability..."
for port in 4000 5434 6379; do
    if lsof -i ":$port" >/dev/null 2>&1; then
        echo "  ⚠️  Port $port is already in use"
        lsof -i ":$port" | head -2
    else
        echo "  ✅ Port $port is available"
    fi
done

# Check if services are already running (systemd)
echo "[5/6] Checking existing services..."
if systemctl --user is-active --quiet litellm.service; then
    echo "  ⚠️  litellm.service is running (will need to stop)"
else
    echo "  ✅ litellm.service is not running"
fi

# Verify .env has required variables
echo "[6/6] Checking .env configuration..."
if grep -q "^LITELLM_MASTER_KEY=CHANGE_ME" .env; then
    echo "  ❌ LITELLM_MASTER_KEY is not set"
    exit 1
else
    echo "  ✅ LITELLM_MASTER_KEY is configured"
fi

echo ""
echo "=== Validation Complete ==="
echo "Ready to proceed with migration:"
echo "  1. Stop systemd services: systemctl --user stop litellm.service"
echo "  2. Start Docker: docker-compose up -d"
echo "  3. Verify: bin/health_check_docker.sh"

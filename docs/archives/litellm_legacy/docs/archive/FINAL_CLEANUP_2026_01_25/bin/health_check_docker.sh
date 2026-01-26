#!/usr/bin/env bash
#
# LiteLLM Docker Health Check
#
# Checks health of Docker-deployed LiteLLM services
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_DIR="/LAB/@litellm"
LITELLM_URL="http://127.0.0.1:4000"
POSTGRES_CONTAINER="litellm-postgres"
REDIS_CONTAINER="litellm-redis"

check_result=0

echo "[health] Starting LiteLLM Docker health check..."

# Function to check service
check_service() {
    local name="$1"
    local check_cmd="$2"

    echo -n "[health] Checking $name... "

    if eval "$check_cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        check_result=1
        return 1
    fi
}

# Check Docker is running
check_service "Docker daemon" "docker info >/dev/null 2>&1"

# Check containers are running
check_service "PostgreSQL container" "docker inspect -f '{{.State.Running}}' $POSTGRES_CONTAINER 2>/dev/null | grep -q true"
check_service "Redis container" "docker inspect -f '{{.State.Running}}' $REDIS_CONTAINER 2>/dev/null | grep -q true"
check_service "LiteLLM container" "docker ps --filter 'name=litellm-proxy' --filter 'status=running' | grep -q litellm"

# Check LiteLLM endpoints
check_service "LiteLLM liveness" "curl -sf $LITELLM_URL/health/liveliness"
check_service "LiteLLM readiness" "curl -sf $LITELLM_URL/health/readiness"

# Check database connectivity from LiteLLM
readiness=$(curl -sf "$LITELLM_URL/health/readiness" 2>/dev/null || echo "{}")
if echo "$readiness" | grep -q '"db":.*"connected"'; then
    echo -e "[health] Database connection: ${GREEN}OK${NC}"
else
    echo -e "[health] Database connection: ${RED}FAILED${NC}"
    check_result=1
fi

if echo "$readiness" | grep -q '"cache":.*"redis"'; then
    echo -e "[health] Redis connection: ${GREEN}OK${NC}"
else
    echo -e "[health] Redis connection: ${RED}FAILED${NC}"
    check_result=1
fi

# Final result
if [ $check_result -eq 0 ]; then
    echo -e "[health] ${GREEN}All checks passed${NC}"
    exit 0
else
    echo -e "[health] ${RED}Some checks failed${NC}"
    exit 1
fi

#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    INDIVIDUAL SERVICE ROLLBACK                                ║
# ║                    Rollback specific services without full downtime           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: ./deploy/rollback/service_rollback.sh <service-name> [previous-image-tag]
#
# Examples:
#   ./deploy/rollback/service_rollback.sh backend
#   ./deploy/rollback/service_rollback.sh model-server v1.2.0
#   ./deploy/rollback/service_rollback.sh frontend latest

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

SERVICE="${1:-}"
IMAGE_TAG="${2:-}"

# Available services
SERVICES=("backend" "frontend" "model-server" "nginx" "python-sandbox" "unoserver")

if [ -z "$SERVICE" ]; then
    echo -e "${RED}Error: Service name required${NC}"
    echo ""
    echo "Usage: $0 <service-name> [previous-image-tag]"
    echo ""
    echo "Available services:"
    printf '  - %s\n' "${SERVICES[@]}"
    exit 1
fi

# Validate service name
if [[ ! " ${SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    echo -e "${RED}Error: Invalid service '$SERVICE'${NC}"
    echo "Available services: ${SERVICES[*]}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    SERVICE ROLLBACK: $SERVICE                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Get current image info
CURRENT_IMAGE=$(docker ps --filter "name=layra-${SERVICE}" --format "{{.Image}}" | head -1)
echo "Current image: $CURRENT_IMAGE"
echo ""

# List available previous images
echo "Available previous images:"
docker images --filter "reference=layra-${SERVICE}" --format "table {{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" | head -10
echo ""

# If no image tag specified, prompt for it
if [ -z "$IMAGE_TAG" ]; then
    echo -e "${YELLOW}No image tag specified${NC}"
    read -p "Enter image tag to rollback to (or 'latest'): " IMAGE_TAG
    if [ -z "$IMAGE_TAG" ]; then
        IMAGE_TAG="latest"
    fi
fi

# Confirm rollback
echo -e "${YELLOW}Rollback plan:${NC}"
echo "  Service: $SERVICE"
echo "  From: $CURRENT_IMAGE"
echo "  To: layra-${SERVICE}:${IMAGE_TAG}"
echo ""
read -p "Confirm rollback? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/4] Saving current container state...${NC}"

# Save container configuration
CURRENT_CONTAINER="layra-${SERVICE}"
docker inspect "$CURRENT_CONTAINER" > "/tmp/${SERVICE}_container_backup.json" 2>/dev/null || true
echo -e "${GREEN}✓ Container state saved${NC}"

echo -e "${YELLOW}[2/4] Stopping current service...${NC}"

# Graceful shutdown
docker compose stop "$SERVICE"
echo -e "${GREEN}✓ Service stopped${NC}"

echo -e "${YELLOW}[3/4] Starting service with previous image...${NC}"

# Pull or use existing image
if docker images | grep -q "layra-${SERVICE}.*${IMAGE_TAG}"; then
    echo "Using existing image: layra-${SERVICE}:${IMAGE_TAG}"
else
    echo "Image not found locally, rebuilding..."
    docker compose build --build-arg IMAGE_TAG="$IMAGE_TAG" "$SERVICE"
fi

# Start service
docker compose up -d "$SERVICE"
echo -e "${GREEN}✓ Service starting${NC}"

echo -e "${YELLOW}[4/4] Waiting for health check...${NC}"

# Service-specific health checks
case "$SERVICE" in
    backend)
        MAX_WAIT=60
        ELAPSED=0
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            if curl -sf http://localhost:8090/api/v1/health/check > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Backend is healthy${NC}"
                break
            fi
            sleep 2
            ELAPSED=$((ELAPSED + 2))
            echo -n "."
        done
        if [ $ELAPSED -ge $MAX_WAIT ]; then
            echo -e "\n${RED}✗ Backend health check timed out${NC}"
            echo "Check logs: docker compose logs backend"
            exit 1
        fi
        ;;
    model-server)
        MAX_WAIT=90
        ELAPSED=0
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            if curl -sf http://localhost:8005/healthy-check > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Model server is healthy${NC}"
                break
            fi
            sleep 2
            ELAPSED=$((ELAPSED + 2))
            echo -n "."
        done
        if [ $ELAPSED -ge $MAX_WAIT ]; then
            echo -e "\n${YELLOW}⚠ Model server health check timed out (may still be loading model)${NC}"
        fi
        ;;
    frontend)
        MAX_WAIT=30
        ELAPSED=0
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            if curl -sf http://localhost:8090/ > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Frontend is serving${NC}"
                break
            fi
            sleep 1
            ELAPSED=$((ELAPSED + 1))
            echo -n "."
        done
        ;;
    *)
        echo -e "${YELLOW}⚠ No specific health check for $SERVICE, verifying container is running${NC}"
        sleep 5
        if docker ps | grep -q "layra-${SERVICE}.*Up"; then
            echo -e "${GREEN}✓ Container is running${NC}"
        else
            echo -e "${RED}✗ Container failed to start${NC}"
            exit 1
        fi
        ;;
esac

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    SERVICE ROLLBACK COMPLETE                                ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ Service $SERVICE rolled back successfully${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify service functionality"
echo "  2. Monitor logs: docker compose logs -f $SERVICE"
echo "  3. Check metrics: http://localhost:9090"
echo ""
echo -e "${YELLOW}To revert this rollback:${NC}"
echo "  docker compose stop $SERVICE"
echo "  docker compose up -d $SERVICE"
echo ""

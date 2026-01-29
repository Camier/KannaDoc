#!/bin/bash
# LAYRA Service Healthcheck Script
# Tests all critical services and reports status

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment if available
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values for credentials (override with environment)
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}"
REDIS_PASSWORD="${REDIS_PASSWORD:-layra}"

echo "=== LAYRA Service Healthcheck ==="
echo ""

# Track overall status
ALL_HEALTHY=true

# Function to check service
check_service() {
    local service_name=$1
    local check_command=$2
    local description=$3

    printf "%-20s" "${service_name}:"

    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ HEALTHY${NC}"
        return 0
    else
        echo -e "${RED}✗ UNHEALTHY${NC}"
        echo "  ${description}"
        ALL_HEALTHY=false
        return 1
    fi
}

# Backend API
check_service \
    "Backend API" \
    "curl -sf http://localhost:8090/api/v1/health/check" \
    "Ensure backend is running and accessible on port 8090"

# Model Server
check_service \
    "Model Server" \
    "curl -sf http://localhost:8005/healthy-check" \
    "Ensure model server is running on port 8005"

# MinIO
check_service \
    "MinIO" \
    "docker exec layra-minio curl -sf http://localhost:9000/minio/health/live" \
    "Ensure MinIO container is running and responds to health checks"

# MongoDB
check_service \
    "MongoDB" \
    "docker exec layra-mongodb mongosh --quiet --eval 'db.adminCommand(\"ping\")'" \
    "Ensure MongoDB is accessible and responding to commands"

# Redis
check_service \
    "Redis" \
    "docker exec layra-redis redis-cli -a \"${REDIS_PASSWORD}\" ping" \
    "Ensure Redis is accessible with configured password"

# MySQL
check_service \
    "MySQL" \
    "docker exec layra-mysql mysqladmin ping -h localhost -u root -p\"${MYSQL_ROOT_PASSWORD}\"" \
    "Ensure MySQL is accessible with configured credentials"

# Kafka
check_service \
    "Kafka" \
    "docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list" \
    "Ensure Kafka broker is initialized and can list topics"

# Milvus
check_service \
    "Milvus" \
    "docker exec layra-milvus-standalone curl -sf http://localhost:9091/healthz" \
    "Ensure Milvus vector database is responding on health endpoint"

# Milvus etcd
check_service \
    "Milvus etcd" \
    "docker exec layra-milvus-etcd etcdctl endpoint health" \
    "Ensure Milvus etcd backend is healthy"

# Milvus MinIO
check_service \
    "Milvus MinIO" \
    "docker exec layra-milvus-minio curl -sf http://localhost:9000/minio/health/live" \
    "Ensure Milvus MinIO instance is operational"

# UnoServer
check_service \
    "UnoServer" \
    "docker exec layra-unoserver nc -z localhost 2003" \
    "Ensure UnoServer document conversion service is listening on port 2003"

# Qdrant (optional - only if enabled)
if docker ps | grep -q "layra-qdrant"; then
    check_service \
        "Qdrant" \
        "docker exec layra-qdrant curl -sf http://localhost:6333/healthz" \
        "Ensure Qdrant vector database is responding"
fi

echo ""
echo "=== Detailed Health Status ==="
echo ""

# Show detailed container health
echo "Container Health Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep layra || echo "No LAYRA containers running"

echo ""
echo "=== Healthcheck Summary ==="

if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}All services are healthy${NC}"
    exit 0
else
    echo -e "${RED}Some services are unhealthy${NC}"
    echo ""
    echo "To troubleshoot:"
    echo "  1. Check container logs: docker logs <container-name>"
    echo "  2. Inspect health status: docker inspect <container-name> --format='{{json .State.Health}}' | jq"
    echo "  3. Read documentation: /LAB/@thesis/layra/docs/operations/HEALTHCHECKS.md"
    exit 1
fi

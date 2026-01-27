# Service Healthchecks

## Overview

This document provides comprehensive documentation of all healthcheck endpoints across the LAYRA platform. Healthchecks are critical for monitoring service availability, orchestrating container startup dependencies, and troubleshooting deployment issues.

## Architecture Summary

LAYRA uses healthchecks at multiple layers:

- **Application-level**: HTTP endpoints that verify service logic
- **Container-level**: Docker healthcheck directives that monitor container state
- **Infrastructure-level**: Database and service native health probes

## Service Endpoints

### Backend API

**Endpoint**: `GET /api/v1/health/check`

**Implementation Location**: `/LAB/@thesis/layra/backend/app/api/endpoints/health.py`

**Response Format**:
```json
{
  "status": "UP",
  "details": "All systems operational"
}
```

**HTTP Status Codes**:
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is unhealthy (not implemented)

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/check"]
  interval: 30s
  start_period: 10s
  timeout: 5s
  retries: 10
```

**What it validates**:
- FastAPI application is running and responding
- Basic HTTP request handling is functional

**Known Limitations**:
- Does NOT validate database connections
- Does NOT validate external service dependencies
- Does NOT check disk space or memory

**Manual Testing**:
```bash
# From host (via nginx proxy)
curl -f http://localhost:8090/api/v1/health/check

# From within container
docker exec layra-backend curl -f http://localhost:8000/api/v1/health/check

# With verbose output
curl -v http://localhost:8090/api/v1/health/check
```

### Model Server

**Primary Endpoint**: `GET /healthy-check`

**Implementation Location**: `/LAB/@thesis/layra/model-server/model_server.py`

**Additional Endpoints**:
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe (checks if models loaded)

**Response Formats**:

Primary healthcheck:
```json
{
  "status": "UP"
}
```

Liveness probe:
```json
{
  "status": "ALIVE"
}
```

Readiness probe:
```json
{
  "status": "READY"
}
```

Or if not ready:
```json
{
  "status": "NOT_READY"
}
```

**HTTP Status Codes**:
- `200 OK`: Service is healthy/ready
- `503 Service Unavailable`: Service not ready (models not loaded)

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8005/healthy-check"]
  interval: 30s
  start_period: 30s
  timeout: 5s
  retries: 10
```

**What it validates**:
- `GET /healthy-check`: FastAPI application is running
- `GET /health/live`: Service process is alive
- `GET /health/ready`: Models are loaded and ready for inference

**Manual Testing**:
```bash
# Primary healthcheck
curl -f http://localhost:8005/healthy-check

# Liveness probe
curl http://localhost:8005/health/live

# Readiness probe
curl http://localhost:8005/health/ready

# From within container
docker exec layra-model-server curl -f http://localhost:8005/healthy-check
```

## Infrastructure Services

### MinIO (Object Storage)

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
  interval: 10s
  timeout: 5s
  retries: 10
```

**Endpoint**: `GET /minio/health/live`

**Manual Testing**:
```bash
# Main MinIO service
docker exec layra-minio curl -f http://localhost:9000/minio/health/live

# Milvus MinIO service
docker exec layra-milvus-minio curl -f http://localhost:9000/minio/health/live
```

### MongoDB

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
  interval: 10s
  timeout: 5s
  retries: 10
```

**What it validates**:
- MongoDB server is responding to commands
- Authentication is working

**Manual Testing**:
```bash
# From container
docker exec layra-mongodb mongosh --eval "db.adminCommand('ping')"

# Expected output: { ok: 1 }
```

### Redis

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "redis-cli -a \"${REDIS_PASSWORD}\" ping | grep -q PONG"]
  interval: 5s
  timeout: 3s
  retries: 5
```

**What it validates**:
- Redis server is responsive
- Authentication is working

**Manual Testing**:
```bash
# From container (password from environment)
docker exec layra-redis redis-cli -a "your_redis_password" ping

# Expected output: PONG
```

**Security Note**: Password is embedded in healthcheck command. This is acceptable for container-internal checks but should not be exposed externally.

### MySQL

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p$MYSQL_ROOT_PASSWORD"]
  interval: 10s
  timeout: 5s
  retries: 10
```

**What it validates**:
- MySQL server is running
- Root authentication is working

**Manual Testing**:
```bash
# From container
docker exec layra-mysql mysqladmin ping -h localhost -u root -p

# Or using mysql client
docker exec layra-mysql mysql -u root -p -e "SELECT 1"
```

### Qdrant (Vector Database - Alternative)

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl", "-f", "http://localhost:6333/healthz"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Endpoint**: `GET /healthz`

**Manual Testing**:
```bash
# From host
curl -f http://localhost:6333/healthz

# From container
docker exec layra-qdrant curl -f http://localhost:6333/healthz
```

**Note**: Qdrant is not active by default (VECTOR_DB=milvus is default).

### Milvus (Vector Database - Default)

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
  interval: 10s
  start_period: 30s
  timeout: 5s
  retries: 30
```

**Endpoint**: `GET /healthz` (internal port 9091)

**Manual Testing**:
```bash
# From container
docker exec layra-milvus-standalone curl -f http://localhost:9091/healthz
```

**Note**: Milvus has a longer startup period (30s) and more retries (30) due to initialization complexity.

### Kafka (Message Broker)

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "sh", "-c", "/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list"]
  interval: 15s
  timeout: 10s
  retries: 15
  start_period: 30s
```

**What it validates**:
- Kafka broker is running
- Can list topics (requires broker to be fully initialized)

**Manual Testing**:
```bash
# From container
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# Should list configured topics (e.g., workflow_events)
```

### Milvus etcd

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "etcdctl", "endpoint", "health"]
  interval: 10s
  timeout: 5s
  retries: 10
```

**Manual Testing**:
```bash
# From container
docker exec layra-milvus-etcd etcdctl endpoint health
```

### UnoServer

**Docker Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "2003"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 10s
```

**What it validates**:
- UnoServer port 2003 is listening
- Document conversion service is available

**Manual Testing**:
```bash
# From container
docker exec layra-unoserver nc -z localhost 2003

# Exit code 0 means healthy
```

## Testing Commands

### Full Stack Health Check

Test all critical services:

```bash
#!/bin/bash
# /LAB/@thesis/layra/scripts/check_all_health.sh

echo "=== LAYRA Service Healthcheck ==="
echo ""

# Backend API
echo -n "Backend API: "
if curl -sf http://localhost:8090/api/v1/health/check > /dev/null; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# Model Server
echo -n "Model Server: "
if curl -sf http://localhost:8005/healthy-check > /dev/null; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# MinIO
echo -n "MinIO: "
if docker exec layra-minio curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# MongoDB
echo -n "MongoDB: "
if docker exec layra-mongodb mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# Redis
echo -n "Redis: "
if docker exec layra-redis redis-cli -a "${REDIS_PASSWORD:-layra}" ping > /dev/null 2>&1; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# MySQL
echo -n "MySQL: "
if docker exec layra-mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD:-root}" > /dev/null 2>&1; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# Kafka
echo -n "Kafka: "
if docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

# Milvus
echo -n "Milvus: "
if docker exec layra-milvus-standalone curl -sf http://localhost:9091/healthz > /dev/null 2>&1; then
    echo "✓ HEALTHY"
else
    echo "✗ UNHEALTHY"
fi

echo ""
echo "=== Healthcheck Complete ==="
```

### Individual Service Tests

```bash
# Quick backend check
curl http://localhost:8090/api/v1/health/check | jq

# Quick model server check
curl http://localhost:8005/healthy-check | jq

# Docker health status overview
docker ps --format "table {{.Names}}\t{{.Status}}" | grep layra

# Detailed health status
docker inspect layra-backend --format='{{.State.Health.Status}}'
```

### Container Dependency Verification

```bash
# Check if backend dependencies are healthy
docker inspect layra-backend --format='{{json .State.Health}}' | jq

# View service startup order
docker compose ps -a --format "table {{.Name}}\t{{.State}}\t{{.Health}}"
```

## Response Format Reference

### Standard Success Response
```json
{
  "status": "UP"
}
```

### Backend Detailed Response
```json
{
  "status": "UP",
  "details": "All systems operational"
}
```

### Model Server Readiness States
```json
// Ready
{ "status": "READY" }

// Not ready (models loading)
{ "status": "NOT_READY" }

// Alive (liveness)
{ "status": "ALIVE" }
```

## Inconsistencies and Issues

### Naming Inconsistencies

1. **Backend vs Model Server**:
   - Backend uses: `/api/v1/health/check` (RESTful, conventional)
   - Model server uses: `/healthy-check` (non-standard)
   - **Impact**: No functional impact, but reduces API consistency
   - **Recommendation**: Standardize to `/health`, `/health/ready`, `/health/live`

2. **Response Format Inconsistencies**:
   - Backend returns: `{"status": "UP", "details": "..."}`
   - Model server returns: `{"status": "UP"}` (no details)
   - **Impact**: Minor, but complicates unified monitoring
   - **Recommendation**: Standardize response schema

### Coverage Gaps

1. **Backend Healthcheck Limitations**:
   - Does not validate database connectivity
   - Does not check external services (MinIO, Kafka, etc.)
   - Does not verify vector database (Milvus/Qdrant)
   - **Impact**: Backend may report healthy even if critical dependencies are down
   - **Recommendation**: Implement dependency health checks

2. **Missing Metrics Endpoint**:
   - Backend has `/api/v1/health/metrics` but not documented in main healthcheck flow
   - **Impact**: Metrics not included in standard monitoring
   - **Recommendation**: Document metrics endpoint usage

3. **No Deep Health Checks**:
   - No endpoint to validate full stack connectivity
   - No database query validation
   - No external service ping checks
   - **Impact**: Difficult to diagnose partial failures
   - **Recommendation**: Add `/health/deep` endpoint

### Startup Timing Issues

1. **Milvus Long Startup**:
   - Milvus requires 30s start period and 30 retries
   - **Impact**: Delays dependent services
   - **Current Mitigation**: Long retries configured

2. **Model Server Readiness**:
   - Models may take time to load
   - Readiness probe exists but may not be used in docker-compose
   - **Impact**: Backend may call model server before ready
   - **Recommendation**: Use `/health/ready` in docker-compose

### Security Considerations

1. **Credentials in Healthchecks**:
   - Redis password embedded in healthcheck command
   - MySQL password visible in docker-compose
   - **Impact**: Credentials visible in `docker inspect` output
   - **Mitigation**: Use Docker secrets for sensitive credentials

2. **No Authentication on Health Endpoints**:
   - Health endpoints are publicly accessible
   - **Impact**: Information disclosure, potential DoS
   - **Recommendation**: Require authentication for detailed health info

## Troubleshooting

### Common Issues

#### 1. Backend Shows Healthy But Can't Connect to Database

**Symptom**: `curl /api/v1/health/check` returns 200, but application logs show database errors

**Cause**: Healthcheck doesn't validate database connectivity

**Resolution**:
```bash
# Check database directly
docker exec layra-mysql mysqladmin ping

# Check backend database config
docker exec layra-backend env | grep DB_URL

# Test database connection from backend container
docker exec layra-backend python -c "
from app.db.mysql_session import mysql
import asyncio
asyncio.run(mysql.connect())
print('Database connection successful')
"
```

#### 2. Model Server Returns NOT_READY

**Symptom**: `curl /health/ready` returns 503 or `{"status": "NOT_READY"}`

**Cause**: Models not fully loaded

**Resolution**:
```bash
# Check model server logs
docker logs layra-model-server --tail 50

# Check if model weights are accessible
docker exec layra-model-server ls -la /model_weights

# Verify GPU availability
docker exec layra-model-server nvidia-smi

# Wait and retry
for i in {1..10}; do
  if curl -sf http://localhost:8005/health/ready | grep -q READY; then
    echo "Model server is ready"
    break
  fi
  echo "Waiting for model server... ($i/10)"
  sleep 5
done
```

#### 3. Healthcheck Fails Due to Missing curl

**Symptom**: Container health shows "unhealthy" but service is running

**Cause**: `curl` not installed in container

**Resolution**:
```bash
# Check if curl is available
docker exec layra-backend which curl

# If missing, install in Dockerfile
# RUN apt-get update && apt-get install -y curl
```

#### 4. Intermittent Healthcheck Failures

**Symptom**: Service health flips between healthy/unhealthy

**Cause**: Healthcheck timeout too short, service overloaded

**Resolution**:
```bash
# Check current healthcheck settings
docker inspect layra-backend --format='{{json .State.Health}}' | jq

# Increase timeout in docker-compose.yml
# timeout: 5s -> timeout: 10s

# Check service resource usage
docker stats layra-backend --no-stream
```

#### 5. Dependency Services Not Starting in Order

**Symptom**: Backend starts before database is ready

**Cause**: Missing `condition: service_healthy` dependencies

**Resolution**:
```bash
# Verify dependencies in docker-compose.yml
docker compose config | grep -A 5 "depends_on"

# Ensure services use health conditions:
# depends_on:
#   mysql:
#     condition: service_healthy
```

### Debug Mode Healthchecks

Enable verbose healthcheck logging:

```yaml
# In docker-compose.yml, add to service definition:
healthcheck:
  test: ["CMD-SHELL", "curl -v http://localhost:8000/api/v1/health/check 2>&1 | tee /tmp/health.log"]
  interval: 10s
```

### Health Check Log Analysis

```bash
# View healthcheck history
docker inspect layra-backend --format='{{range .State.Health.Log}}{{.Start}} - {{.ExitCode}} - {{.Output}}{{end}}'

# Monitor health status in real-time
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Check health failure reasons
docker inspect layra-backend --format='{{json .State.Health}}' | jq '.Log[-1]'
```

## Best Practices

### For Development

1. **Use short intervals** during development for faster feedback
2. **Monitor startup order** to catch dependency issues early
3. **Test health endpoints manually** before committing changes

### For Production

1. **Use appropriate intervals**:
   - Core services: 10-30s
   - External dependencies: 30-60s
   - Avoid aggressive polling to prevent false positives

2. **Set proper timeouts**:
   - HTTP checks: 5s
   - Database checks: 5s
   - Complex checks: 10s

3. **Configure retries appropriately**:
   - Fast-starting services: 3-5 retries
   - Complex services (Milvus): 20-30 retries

4. **Add deep health checks**:
   - Database query validation
   - External service connectivity
   - Disk space verification
   - Memory threshold checks

### For Monitoring Integration

```bash
# Prometheus healthcheck metrics
curl http://localhost:8090/api/v1/health/metrics

# JSON output for monitoring systems
curl -s http://localhost:8090/api/v1/health/check | jq -c '{status, timestamp: now}'
```

## Related Documentation

- [Docker Compose Configuration](/LAB/@thesis/layra/docker-compose.yml)
- [Service Registry](/LAB/@thesis/layra/docs/ssot/stack.yaml)
- [Operations Runbook](/LAB/@thesis/layra/docs/operations/RUNBOOK.md)
- [Troubleshooting Guide](/LAB/@thesis/layra/docs/operations/TROUBLESHOOTING.md)

## Revision History

- 2026-01-27: Initial documentation created (Task #7)
- Documents current state of healthchecks as of commit 33a0277

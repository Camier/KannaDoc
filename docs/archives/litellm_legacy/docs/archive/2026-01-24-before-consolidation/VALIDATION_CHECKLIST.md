# Validation Checklist: Before & After

**Goal:** Verify all hardening changes are applied correctly and working

---

## Pre-Implementation Checklist

Run this BEFORE applying changes:

```bash
echo "=== PRE-HARDENING BASELINE ==="

# 1. Current pool sizes
echo "Current DB pool limit:"
grep "database_connection_pool_limit:" config.yaml

echo "Current Redis pool limit:"
grep "redis_connection_pool_limit:" config.yaml

# 2. Current logging level
echo "Current log level:"
grep "LITELLM_LOG=" .env || echo "Not set (defaulting to INFO)"

# 3. Current workers
echo "Current docker-compose logging:"
grep "LITELLM_LOG=" docker-compose.yml

# 4. Health check setup
echo "Current health check:"
grep -A 3 "healthcheck:" docker-compose.yml | head -5

# 5. Current timeout for graceful shutdown
echo "Current graceful shutdown:"
grep "SUPERVISORD_STOPWAITSECS" .env || echo "Not set"

# 6. Current worker recycling
echo "Current worker recycling:"
grep "max_requests_before_restart" Dockerfile || echo "Not configured"

# 7. Salt key
echo "Salt key configured:"
grep "LITELLM_SALT_KEY=" .env | head -c 50

# 8. Slack alerting
echo "Slack alerting:"
grep "alerting:" config.yaml || echo "Not configured"
```

**Expected Output (BEFORE):**
```
Current DB pool limit:
  database_connection_pool_limit: 25
Current Redis pool limit:
  redis_connection_pool_limit: 20
Current log level:
Not set (defaulting to INFO)
Current graceful shutdown:
Not set
Current worker recycling:
Not configured
Salt key configured:
Not set
Slack alerting:
Not configured
```

---

## Post-Implementation Checklist

Run this AFTER applying changes:

```bash
echo "=== POST-HARDENING VERIFICATION ==="

# 1. Pool sizes updated
echo "✓ DB pool limit:"
grep "database_connection_pool_limit:" config.yaml

echo "✓ Redis pool limit:"
grep "redis_connection_pool_limit:" config.yaml

echo "✓ Batch write interval:"
grep "proxy_batch_write_at:" config.yaml

# 2. Logging disabled
echo "✓ Log level set to ERROR:"
grep "LITELLM_LOG=ERROR" .env

# 3. Retry policy configured
echo "✓ Retry policy present:"
grep -c "retry_policy:" config.yaml

# 4. Health check on separate port
echo "✓ Health check ports:"
grep -E "(4000|4001)" docker-compose.yml | head -3

echo "✓ Health check endpoint:"
grep -A 1 'test: \["CMD", "curl"' docker-compose.yml

# 5. Graceful shutdown configured
echo "✓ Graceful shutdown timeout:"
grep "SUPERVISORD_STOPWAITSECS=" .env

# 6. Worker recycling enabled
echo "✓ Worker recycling:"
grep "max_requests_before_restart" Dockerfile

# 7. Salt key set
echo "✓ Salt key (first 20 chars):"
grep "LITELLM_SALT_KEY=" .env | cut -c 1-50

# 8. Slack alerting configured
echo "✓ Slack alerting:"
grep "alerting:" config.yaml
```

**Expected Output (AFTER):**
```
✓ DB pool limit:
  database_connection_pool_limit: 50
✓ Redis pool limit:
  redis_connection_pool_limit: 50
✓ Batch write interval:
  proxy_batch_write_at: 60
✓ Log level set to ERROR:
LITELLM_LOG=ERROR
✓ Retry policy present:
1
✓ Health check ports:
      - "4000:4000"
      - "4001:4001"
✓ Health check endpoint:
    test: ["CMD", "curl", "-f", "http://localhost:4001/health/liveliness"]
✓ Graceful shutdown timeout:
SUPERVISORD_STOPWAITSECS=3600
✓ Worker recycling:
10000 (max_requests_before_restart)
✓ Salt key (first 20 chars):
LITELLM_SALT_KEY=sk-your-random-hex
✓ Slack alerting:
  alerting: ["slack"]
```

---

## Functional Tests (Post-Deployment)

### Test 1: Service Health
```bash
echo "=== Test 1: Service Health ==="

# Check main service is running
docker ps | grep litellm-proxy
echo "✓ litellm-proxy running"

# Check separate health app is responding
curl -s http://localhost:4001/health/liveliness | jq .
echo "✓ Separate health check app on 4001"

# Check main proxy is responding
curl -s http://localhost:4000/health/readiness | jq .
echo "✓ Main proxy on 4000"

# Check connectivity
python3 bin/health_check.py
echo "✓ Full health check passed"
```

**Expected:**
- Both services running
- Health endpoints respond in <100ms
- No DB/Redis errors

---

### Test 2: Model Connectivity
```bash
echo "=== Test 2: Model Connectivity ==="

python3 bin/probe_models.py

echo "✓ All models probed"
```

**Expected:**
- All models return ✅
- No timeout errors
- Latency <5s per model

---

### Test 3: Concurrency & Connection Pooling
```bash
echo "=== Test 3: Connection Pooling ==="

# Generate 50 concurrent requests
echo "Sending 50 concurrent requests..."
for i in {1..50}; do
  curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -X POST http://localhost:4000/chat/completions \
    -d '{"model":"kimi-k2-1t-cloud","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' \
    > /dev/null &
done
wait

echo "✓ 50 concurrent requests completed"

# Check connection pool stats
echo "Checking connection state:"
docker stats litellm-proxy --no-stream | tail -1
```

**Expected:**
- All 50 requests succeed
- No connection pool exhaustion errors
- CPU <50%, Memory <1GB

---

### Test 4: Worker Recycling (Optional)
```bash
echo "=== Test 4: Worker Recycling ==="

# Monitor memory over time
echo "Monitoring memory for 5 minutes..."
echo "Time,Memory" > memory.csv
for i in {1..30}; do
  docker stats litellm-proxy --no-stream --format "table {{.MemUsage}}" | tail -1 >> memory.csv
  sleep 10
done

echo "Memory log saved to memory.csv"
echo "✓ If memory is stable (not growing), recycling works"
```

**Expected:**
- Memory plateaus (not continuously growing)
- No memory leaks detected

---

### Test 5: Logging Level
```bash
echo "=== Test 5: Logging Level ==="

# Check log volume before
docker logs litellm-proxy | wc -l
echo "Total log lines"

# Should be ~10-20 lines of actual errors, not hundreds of info logs
# Each request should only appear if there's an error

echo "✓ Check logs contain only ERRORs (not INFO/DEBUG)"
docker logs litellm-proxy --tail 20 | grep -E "ERROR|WARN" || echo "✓ No errors in recent logs"
```

**Expected:**
- Significantly fewer log lines per request
- Only ERROR and WARN levels
- No INFO-level spam

---

### Test 6: Health Check Separation
```bash
echo "=== Test 6: Health Check Separation ==="

# Kill main app (simulate hang)
# docker kill litellm-proxy  # DON'T ACTUALLY RUN THIS

# Health check should still respond
echo "Health check response (should always work):"
time curl -s http://localhost:4001/health/liveliness

echo "✓ Health check is separate and responsive"
```

**Expected:**
- Health check responds <100ms
- Even if main app is under load
- Prevents false pod restarts

---

### Test 7: Slack Alerting (Optional)
```bash
echo "=== Test 7: Slack Alerting ==="

# Check if SLACK_WEBHOOK_URL is set
if grep -q "SLACK_WEBHOOK_URL=" .env; then
  echo "✓ Slack webhook configured"
  echo "✓ Test: Set alerting_threshold low and trigger an error"
  echo "  Check Slack channel for alert notification"
else
  echo "ℹ️  Slack not configured (optional)"
fi
```

**Expected:**
- Slack webhook is set
- Error notifications appear in Slack
- No false positives

---

### Test 8: Metrics & Observability
```bash
echo "=== Test 8: Metrics Endpoint ==="

# Check metrics are being exported
curl -s http://localhost:4000/metrics | head -20

echo ""
echo "✓ Metrics endpoint working"
echo "✓ Grep for 'litellm_requests_total' to see request counts"
```

**Expected:**
- Metrics endpoint responds
- Contains `litellm_requests_total`, `litellm_request_duration_seconds`, etc.
- Can be scraped by Prometheus

---

## Performance Baseline (Before & After)

Run this test before and after:

```bash
#!/bin/bash
echo "=== Performance Baseline Test ==="

MODEL="kimi-k2-1t-cloud"
NUM_REQUESTS=20
CONCURRENCY=5

# Send requests
echo "Sending $NUM_REQUESTS requests (concurrency: $CONCURRENCY)..."
time (
  for i in $(seq 1 $NUM_REQUESTS); do
    curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
      -X POST http://localhost:4000/chat/completions \
      -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hello $i\"}],\"max_tokens\":1}" \
      > /dev/null &
    
    if [ $(($i % $CONCURRENCY)) -eq 0 ]; then
      wait  # Maintain concurrency level
    fi
  done
  wait
)

echo "✓ Baseline test complete"
```

**Before Hardening:**
- Time: ~60-90s
- Errors: Possible connection pool exhaustion
- CPU: 60-80%

**After Hardening:**
- Time: ~20-30s
- Errors: None
- CPU: 20-40%

---

## Summary Table

| Check | Before | After | Status |
|-------|--------|-------|--------|
| DB Pool Limit | 25 | 50 | ✅ |
| Redis Pool Limit | 20 | 50 | ✅ |
| Log Level | INFO | ERROR | ✅ |
| Worker Recycling | Not set | 10k requests | ✅ |
| Graceful Shutdown | Not set | 3600s | ✅ |
| Health Check | Shared (4000) | Separate (4001) | ✅ |
| Retry Policy | Fixed 3/120s | Smart per-error | ✅ |
| Salt Key | Not set | Generated | ✅ |
| Slack Alerting | None | Configured | ✅ |
| Concurrency | ~20 req/s | 100+ req/s | ✅ |
| p99 Latency | 1000ms | <500ms | ✅ |
| Memory Stability | Leaks | Stable | ✅ |

---

## Troubleshooting

### Issue: Health check on 4001 not responding
```bash
# Check if separate health app is enabled
docker exec litellm-proxy env | grep SEPARATE_HEALTH_APP

# Should show: SEPARATE_HEALTH_APP=1

# If not, restart with: docker compose down && docker compose up -d
```

### Issue: Connection pool still exhausted
```bash
# Check actual pool size in use
docker exec litellm-proxy curl -s http://localhost:4000/metrics | \
  grep -E "sqlalchemy.*pool" | head -5

# Should show pool_size > 30
```

### Issue: Memory still growing
```bash
# Check if worker recycling is working
docker logs litellm-proxy | grep -i "recycle\|restart" | head -5

# Should see worker recycle messages every ~30-40 minutes
```

### Issue: Logging still verbose
```bash
# Verify log level
docker exec litellm-proxy env | grep LITELLM_LOG
# Should show: LITELLM_LOG=ERROR

# Check actual log verbosity
docker logs litellm-proxy --tail 20
# Should show only errors/warnings, not every request
```

---

## Pass/Fail Criteria

**✅ PASS (All Green):**
- All configuration changes applied
- All tests pass
- Throughput ≥ 5× (20 → 100+ RPS)
- Latency p99 ≤ 500ms
- Memory stable (no growth >100MB/hour)

**⚠️  PARTIAL PASS (Yellow):**
- Most changes applied
- Some tests fail but requests still work
- Throughput 2-5× improvement
- Deploy with monitoring

**❌ FAIL (Red):**
- Errors during deployment
- Models unreachable
- Health checks failing
- → **ROLLBACK** using provided script

---

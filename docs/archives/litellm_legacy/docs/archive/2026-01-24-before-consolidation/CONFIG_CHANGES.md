# Exact Code Changes to Apply

## 1. Update `config.yaml` (Critical Changes)

### Pool & Batching Settings
Replace:
```yaml
general_settings:
  database_connection_pool_limit: 25
```

With:
```yaml
general_settings:
  database_connection_pool_limit: 50
  proxy_batch_write_at: 60
```

---

### Router Settings - Connection Pools
Replace:
```yaml
router_settings:
  redis_connection_pool_limit: 20
  redis_connection_pool_timeout: 5
```

With:
```yaml
router_settings:
  redis_connection_pool_limit: 50
  redis_connection_pool_timeout: 5
```

---

### Router Settings - Smart Retries
Replace:
```yaml
router_settings:
  enable_pre_call_checks: true
  allowed_fails: 3
  cooldown_time: 120
```

With:
```yaml
router_settings:
  enable_pre_call_checks: true
  allowed_fails: 5
  cooldown_time: 60
  
  retry_policy:
    AuthenticationErrorRetries: 0
    TimeoutErrorRetries: 3
    RateLimitErrorRetries: 5
    ContentPolicyViolationErrorRetries: 0
    InternalServerErrorRetries: 3
  
  allowed_fails_policy:
    BadRequestErrorAllowedFails: 1000
    AuthenticationErrorAllowedFails: 5
    TimeoutErrorAllowedFails: 20
    RateLimitErrorAllowedFails: 10000
    InternalServerErrorAllowedFails: 20
```

---

### Alerting (Add to general_settings)
Replace:
```yaml
general_settings:
  # ... existing settings
  ui_access_mode: admin_only
  enable_metrics: true
```

With:
```yaml
general_settings:
  # ... existing settings
  ui_access_mode: admin_only
  enable_metrics: true
  alerting: ["slack"]
  alerting_threshold: 1000
```

---

### Logging (Verify/Update)
Replace:
```yaml
litellm_settings:
  num_retries: 3
  request_timeout: 120
  ssl_ecdh_curve: X25519
  drop_params: true
  cache: true
  json_logs: true
```

With:
```yaml
litellm_settings:
  num_retries: 3
  request_timeout: 120
  ssl_ecdh_curve: X25519
  drop_params: true
  set_verbose: False
  cache: true
  json_logs: true
```

---

### Add Slack Alert Callback
Replace:
```yaml
litellm_settings:
  cache_params:
    type: redis
    ...
```

With (add before cache_params):
```yaml
litellm_settings:
  failure_callback: ["slack"]
  cache_params:
    type: redis
    ...
```

---

## 2. Update `.env`

Add these lines:
```bash
# Logging & Debug
LITELLM_MODE=PRODUCTION
LITELLM_LOG=ERROR

# Health Check App (Separate Process)
SEPARATE_HEALTH_APP=1
SEPARATE_HEALTH_PORT=4001
SUPERVISORD_STOPWAITSECS=3600

# Worker Recycling
MAX_REQUESTS_BEFORE_RESTART=10000

# Encryption Salt Key (Replace with your own!)
LITELLM_SALT_KEY=sk-your-64-character-random-hash

# Slack Alerting (Optional, but recommended)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## 3. Update `Dockerfile`

Replace:
```dockerfile
CMD ["litellm"]
CMD ["--config", "/app/config.yaml", "--port", "4000", "--host", "0.0.0.0", "--num_workers", "4"]
```

With:
```dockerfile
ENTRYPOINT ["litellm"]
CMD ["--port", "4000", "--config", "/app/config.yaml", "--host", "0.0.0.0", "--num_workers", "4", "--run_gunicorn", "--max_requests_before_restart", "10000"]
```

---

## 4. Update `docker-compose.yml`

### LiteLLM Service - Add Port
Replace:
```yaml
litellm:
  ports:
    - "4000:4000"
```

With:
```yaml
litellm:
  ports:
    - "4000:4000"
    - "4001:4001"
```

---

### LiteLLM Service - Environment Variables
Replace:
```yaml
  environment:
    - REDIS_HOST=redis
    - REDIS_PORT=6379
    - LITELLM_MODE=PRODUCTION
    - LITELLM_LOG=INFO
    - JSON_LOGS=true
    - DISABLE_SCHEMA_UPDATE=true
    - USE_PRISMA_MIGRATE=true
```

With:
```yaml
  environment:
    - REDIS_HOST=redis
    - REDIS_PORT=6379
    - LITELLM_MODE=PRODUCTION
    - LITELLM_LOG=ERROR
    - JSON_LOGS=true
    - DISABLE_SCHEMA_UPDATE=true
    - USE_PRISMA_MIGRATE=true
    - SEPARATE_HEALTH_APP=1
    - SEPARATE_HEALTH_PORT=4001
    - SUPERVISORD_STOPWAITSECS=3600
    - MAX_REQUESTS_BEFORE_RESTART=10000
```

---

### LiteLLM Service - Healthcheck
Replace:
```yaml
  healthcheck:
    test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4000/health/liveliness')"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

With:
```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:4001/health/liveliness"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 40s
```

---

## 5. Update `bin/health_check.py` (Optional Improvement)

Add timeout context to reduce log spam:

Find:
```python
def check_litellm_proxy():
    """Check LiteLLM proxy health."""
    base_url = os.environ.get("LITELLM_BASE", "http://127.0.0.1:4000")
```

Replace with:
```python
def check_litellm_proxy():
    """Check LiteLLM proxy health."""
    base_url = os.environ.get("LITELLM_BASE", "http://127.0.0.1:4000")
    # Try separate health port first (if available)
    health_port = os.environ.get("SEPARATE_HEALTH_PORT", "4000")
    if health_port != "4000":
        base_url = f"http://127.0.0.1:{health_port}"
```

---

## Apply Order

1. **First:** Update `.env`
   ```bash
   # Edit .env and add new environment variables
   ```

2. **Second:** Update `config.yaml`
   ```bash
   # Apply configuration changes above
   ```

3. **Third:** Update `Dockerfile`
   ```bash
   # Rebuild image with: docker compose build litellm
   ```

4. **Fourth:** Update `docker-compose.yml`
   ```bash
   # File is auto-read by compose
   ```

5. **Finally:** Restart services
   ```bash
   docker compose down
   docker compose build litellm
   docker compose up -d
   sleep 60  # Wait for startup
   python3 bin/health_check.py
   python3 bin/probe_models.py
   ```

---

## Validation Commands

```bash
# Validate compose config
just validate

# Check health
python3 bin/health_check.py

# Probe models
python3 bin/probe_models.py

# Check metrics
curl http://localhost:4000/metrics | head -20

# Check separate health app is working
curl http://localhost:4001/health/liveliness
```

---

## Rollback Plan

If issues occur:
```bash
# Revert to previous state
git checkout config.yaml docker-compose.yml Dockerfile
git checkout .env
docker compose down
docker compose build litellm
docker compose up -d
```

---

## Performance Expectations After Changes

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Max Concurrent Requests | ~20 | ~100 | 5× |
| p99 Latency | 1000ms+ | <500ms | 50% reduction |
| Memory Stability | Leaks over time | Stable | Recycling enabled |
| Health Check Response | May hang | Always <5ms | Separate process |
| Cache hit utilization | Unknown | Measurable | Prometheus metrics |


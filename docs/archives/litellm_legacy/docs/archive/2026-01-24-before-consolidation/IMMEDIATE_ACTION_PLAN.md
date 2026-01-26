# Immediate Action Plan: Production Hardening (LiteLLM Docs-Based)

**Based on Official LiteLLM Best Practices** | Priority: HIGH
Last Updated: 2026-01-23

---

## 🔴 CRITICAL (Week 1)

### 1. Fix Connection Pool Bottleneck
**Current State:** 25 DB, 20 Redis connections → ~20 max concurrent requests
**Target:** 100-200 concurrent requests

**Action:** Update `config.yaml`
```yaml
general_settings:
  # BEFORE: database_connection_pool_limit: 25
  # AFTER: Scale with instances
  database_connection_pool_limit: 50  # For single instance
  # Formula: MAX_DB_CONNECTIONS / (instances × workers)
  # Example: 200 total / (1 instance × 4 workers) = 50 per worker
  
  proxy_batch_write_at: 60  # Batch DB writes every 60s (from default 10)

router_settings:
  # BEFORE: redis_connection_pool_limit: 20
  # AFTER: Increase capacity
  redis_connection_pool_limit: 50
  redis_connection_pool_timeout: 5
```

**Impact:** ✅ Enables ~50-100 concurrent requests (vs 20 now)

---

### 2. Add Graceful Shutdown & Worker Recycling
**Problem:** Current Dockerfile has no worker management → memory leaks under sustained load
**Solution:** Kubernetes-ready configuration

**Action:** Update `Dockerfile` CMD
```dockerfile
# BEFORE:
CMD ["--config", "/app/config.yaml", "--port", "4000"]

# AFTER:
CMD ["--port", "4000", "--config", "/app/config.yaml", "--num_workers", "4", "--run_gunicorn", "--max_requests_before_restart", "10000"]
```

**Environment:** Add to `.env`
```bash
SUPERVISORD_STOPWAITSECS=3600  # Graceful shutdown: 1 hour max wait
MAX_REQUESTS_BEFORE_RESTART=10000
```

**Impact:** ✅ Prevents memory leaks, enables graceful deploys

---

### 3. Disable Debug Logging in Production
**Current State:** `LITELLM_LOG` not set → defaults to INFO (verbose)
**Target:** ERROR level only

**Action:** Update `.env`
```bash
# ADD:
LITELLM_MODE=PRODUCTION
LITELLM_LOG=ERROR  # Only log errors, not every request
```

**Action:** Update `config.yaml`
```yaml
litellm_settings:
  set_verbose: False  # Already set, verify it's False
  json_logs: true     # Keep (already enabled)
```

**Impact:** ✅ 30-50% CPU reduction, cleaner logs

---

### 4. Smart Error Retries (Adaptive Circuit Breaker)
**Current State:** Fixed 3 failures → 120s cooldown (too aggressive)
**Target:** Error-type-aware retries

**Action:** Update `router_settings` in `config.yaml`
```yaml
router_settings:
  # BEFORE: allowed_fails: 3, cooldown_time: 120
  # AFTER: Granular retry policy
  
  allowed_fails: 5  # More lenient for transient errors
  cooldown_time: 60  # Shorter initial cooldown
  
  retry_policy:
    AuthenticationErrorRetries: 0  # Don't retry auth errors
    TimeoutErrorRetries: 3          # Retry timeouts 3x
    RateLimitErrorRetries: 5        # Retry rate limits aggressively
    ContentPolicyViolationErrorRetries: 0  # Don't retry policy
    InternalServerErrorRetries: 3
  
  allowed_fails_policy:
    BadRequestErrorAllowedFails: 1000     # Ignore bad request spam
    AuthenticationErrorAllowedFails: 5    # Cool down after 5 auth fails
    TimeoutErrorAllowedFails: 20          # Lenient on timeouts
    RateLimitErrorAllowedFails: 10000     # Very lenient on rate limits
    InternalServerErrorAllowedFails: 20
```

**Impact:** ✅ Fewer false circuit breaker trips, better fallback utilization

---

## 🟡 HIGH PRIORITY (Week 1-2)

### 5. Implement Separate Health Check App
**Problem:** Health checks share main process → may hang under load
**Solution:** Dedicated health check endpoint on separate port

**Action:** Update `.env`
```bash
SEPARATE_HEALTH_APP=1           # Enable separate health app
SEPARATE_HEALTH_PORT=4001       # Health endpoints on port 4001
SUPERVISORD_STOPWAITSECS=3600   # Upper bound graceful shutdown
```

**Action:** Update `docker-compose.yml` for litellm service
```yaml
litellm:
  ports:
    - "4000:4000"  # Main proxy
    - "4001:4001"  # Health check app
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:4001/health/liveliness"]
    interval: 30s
    timeout: 5s    # Reduced timeout (separate app is faster)
    retries: 3
    start_period: 40s
  environment:
    - SEPARATE_HEALTH_APP=1
    - SEPARATE_HEALTH_PORT=4001
```

**Impact:** ✅ Health checks always responsive, prevents unnecessary pod restarts

---

### 6. Fix Redis Configuration (Performance)
**Problem:** Current setup might use slower `redis_url` internally
**Solution:** Explicit host/port/password (80 RPS faster per official docs)

**Action:** Verify in `config.yaml` (should already be correct)
```yaml
router_settings:
  # ✅ CORRECT (current setup):
  redis_host: os.environ/REDIS_HOST
  redis_port: os.environ/REDIS_PORT
  redis_password: os.environ/REDIS_PASSWORD
  
  # ❌ WRONG (don't do this):
  # redis_url: os.environ/REDIS_URL  # 80 RPS slower!

litellm_settings:
  cache_params:
    type: redis
    host: os.environ/REDIS_HOST
    port: os.environ/REDIS_PORT
    password: os.environ/REDIS_PASSWORD
```

**Impact:** ✅ 80 RPS faster (small but real gain)

---

### 7. Configure Slack Alerting
**Problem:** No alerts on failures/slowdowns
**Solution:** Slack webhook for operational visibility

**Action:** Update `.env`
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Action:** Update `config.yaml`
```yaml
general_settings:
  alerting: ["slack"]
  alerting_threshold: 1000  # Alert after 1000 errors
  
litellm_settings:
  failure_callback: ["slack"]  # Log all failures to Slack
```

**Impact:** ✅ Real-time alerts on outages

---

### 8. Set Encryption Salt Key
**Problem:** API keys in DB aren't encrypted with unique salt
**Action:** Generate and set salt key in `.env`
```bash
LITELLM_SALT_KEY=sk-your-64-character-random-hash  # Use 1password.com/password-generator
```

**Action:** Add to `docker-compose.yml` litellm service
```yaml
environment:
  - LITELLM_SALT_KEY=os.environ/LITELLM_SALT_KEY
```

**Impact:** ✅ Encrypted credential storage

---

## 🟢 MEDIUM PRIORITY (Week 2-3)

### 9. Increase Machine Specs (if available)
**Current:** 4 vCPU, 8GB RAM (minimum spec)
**Recommended for 100+ RPS:** 8 vCPU, 16GB RAM

**Why:** 
- Handles 2× concurrent requests without queuing
- Better CPU utilization for JSON parsing, caching
- Smoother tail latencies (p95, p99)

**Action:** (If using cloud)
- Scale pod/instance to 8 vCPU, 16GB
- Docker Compose: Increase host machine capacity

---

### 10. Advanced Caching Tuning
**Current:** TTL 600s, cache enabled
**Target:** Optimize hit rate per workload

**Action:** Analyze cache behavior (add monitoring)
```yaml
litellm_settings:
  cache_params:
    ttl: 1800  # Increase to 30 min if low hit rate (default 600s)
    mode: default_off  # Force opt-in per request
    supported_call_types:
      - "acompletion"      # Chat completions only
      # Disable embeddings caching (expensive)
```

**Monitor:** Check `/metrics` endpoint
```bash
curl http://localhost:4000/metrics | grep "cache_hits_total"
```

**Target:** >30% hit rate for batch workloads, >10% for production

---

### 11. Enable Prometheus Metrics
**Action:** Add to `config.yaml`
```yaml
general_settings:
  enable_metrics: true
  
litellm_settings:
  service_callbacks: ["prometheus"]  # Send infrastructure metrics
```

**Scrape Config (if you have Prometheus):**
```yaml
scrape_configs:
  - job_name: 'litellm'
    static_configs:
      - targets: ['localhost:4000']
    metrics_path: '/metrics'
```

**Impact:** ✅ Real-time cost/latency/availability tracking

---

## 📋 IMPLEMENTATION CHECKLIST

### Week 1 (CRITICAL)
- [ ] Update `database_connection_pool_limit` to 50
- [ ] Add `proxy_batch_write_at: 60` for batch writes
- [ ] Update Redis pool to 50 connections
- [ ] Add `--run_gunicorn --max_requests_before_restart` to Dockerfile
- [ ] Set `LITELLM_LOG=ERROR` in `.env`
- [ ] Add `LITELLM_MODE=PRODUCTION` to `.env`
- [ ] Update retry policy (granular per error type)
- [ ] Test with load: `just probe` should complete faster

### Week 2 (HIGH)
- [ ] Enable `SEPARATE_HEALTH_APP=1` in `.env`
- [ ] Update docker-compose healthcheck to port 4001
- [ ] Set `SLACK_WEBHOOK_URL` for alerting
- [ ] Add `LITELLM_SALT_KEY` to `.env`
- [ ] Verify Redis config (should already be correct)
- [ ] Run health check: `python3 bin/health_check.py`

### Week 3 (MEDIUM)
- [ ] Increase machine to 8 vCPU, 16GB (if possible)
- [ ] Analyze cache hit rate: `curl http://localhost:4000/metrics`
- [ ] Adjust TTL based on hit rate
- [ ] Enable Prometheus scraping
- [ ] Set up monitoring dashboard (Grafana)

---

## 🚀 TESTING & VALIDATION

**Before applying:**
```bash
just validate  # Validate Docker Compose config
```

**After applying config changes:**
```bash
just restart
just check     # Run health checks
just probe     # Test all models
```

**Load testing (simple):**
```bash
# Generate 100 requests across all models
for i in {1..100}; do
  curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -X POST http://localhost:4000/chat/completions \
    -d '{"model":"kimi-k2-1t-cloud","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' &
done
wait
```

**Expected improvements:**
- ✅ Latency: p99 <500ms (from 1000ms+)
- ✅ Throughput: 100+ RPS (from 20 RPS)
- ✅ Error rate: <0.5% (from ~2%)
- ✅ Memory: Stable under sustained load (no leaks)

---

## 📊 MONITORING TARGETS

**Metrics to watch after changes:**
```
litellm_requests_total{model="*"}           # RPS per model
litellm_request_duration_seconds{quantile="0.99"}  # p99 latency
litellm_cache_hits_total                    # Cache hit count
litellm_rate_limit_exceeded                 # Rate limit triggers
process_resident_memory_bytes                # Memory usage
```

**Thresholds for alerts:**
- p99 latency > 1000ms → Investigate pool exhaustion
- Memory growth > 100MB/hour → Check for leaks
- Cache hit rate < 5% → Increase TTL
- Error rate > 2% → Check provider health

---

## 🔗 REFERENCES
- [LiteLLM Best Practices](https://docs.litellm.ai/docs/proxy/prod)
- [Configuration Reference](https://docs.litellm.ai/docs/proxy/config_settings)
- [Benchmarks](https://docs.litellm.ai/docs/benchmarks)

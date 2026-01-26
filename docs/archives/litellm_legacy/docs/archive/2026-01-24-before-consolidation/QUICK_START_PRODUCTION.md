# Quick Start: Production-Ready LiteLLM Proxy

**Status:** ✅ Aligned with [Official LiteLLM Production Best Practices](https://docs.litellm.ai/docs/proxy/prod)  
**Last Updated:** 2026-01-24

---

## What Changed?

Your LiteLLM proxy configuration has been updated to follow **official production best practices**. All changes are documented in `OFFICIAL_DOCS_ALIGNMENT.md`.

### Key Improvements:

✅ **Database optimization** - Connection pool reduced from 200 to 40 (optimal for 4 workers)  
✅ **Worker management** - 4 workers with Gunicorn + worker recycling  
✅ **Timeout fixes** - Increased from 120s to 600s (prevents reasoning model errors)  
✅ **Circuit breaker tuning** - Faster recovery (30s vs 60s)  
✅ **Granular retry policies** - Different strategies per error type  
✅ **Security** - Salt key for DB encryption (CRITICAL)  
✅ **Reliability** - Separate health check app prevents false restarts  
✅ **Monitoring** - Slack alerting infrastructure ready  

---

## First Time Setup

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Generate Secure Secrets

```bash
# Generate secure random values
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo "LITELLM_MASTER_KEY=sk-$(openssl rand -base64 32)"
echo "LITELLM_SALT_KEY=sk-$(openssl rand -base64 32)"
```

### 3. Edit .env File

Replace the placeholders in `.env`:

```bash
# Required - Infrastructure
POSTGRES_PASSWORD=<from step 2>
REDIS_PASSWORD=<from step 2>
DATABASE_URL=postgresql://litellm:<POSTGRES_PASSWORD>@postgres:5432/litellm

# Required - LiteLLM
LITELLM_MASTER_KEY=<from step 2>
LITELLM_SALT_KEY=<from step 2>  # ⚠️ NEVER CHANGE THIS AFTER FIRST USE

# Required - Provider API Keys
OLLAMA_API_KEY=sk-ollama-...  # Get from https://ollama.com
GEMINI_API_KEY=...            # Get from https://aistudio.google.com/
VOYAGE_API_KEY=...            # Get from https://www.voyageai.com/

# Optional - Slack Alerting
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 4. Start Services

```bash
docker-compose up -d
```

### 5. Verify Deployment

```bash
# Check health (should return 200 OK)
curl http://localhost:4001/health/liveliness

# Check main API (should return 200 OK)
curl http://localhost:4000/health

# View logs
docker-compose logs -f litellm

# Test chat completion
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "model": "llama3.1-test",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Existing Deployment Migration

### ⚠️ CRITICAL: Set Salt Key Before Migrating

If you're migrating an existing deployment **without a salt key**, you must:

1. **Set LITELLM_SALT_KEY in .env** (generate new random value)
2. **Re-add all models/credentials** (old encrypted data won't work with new key)

```bash
# Generate salt key
echo "LITELLM_SALT_KEY=sk-$(openssl rand -base64 32)" >> .env

# Restart services
docker-compose down
docker-compose up -d
```

### If You Already Have a Salt Key

Just restart:

```bash
docker-compose down
docker-compose up -d
```

---

## Configuration Summary

### Production Settings (docker-compose.yml)

```yaml
environment:
  - LITELLM_MODE=PRODUCTION              # Disable load_dotenv()
  - LITELLM_LOG=ERROR                    # Minimal logging
  - SEPARATE_HEALTH_APP=1                # Reliable health checks
  - SEPARATE_HEALTH_PORT=4001            # Dedicated health port
  - MAX_REQUESTS_BEFORE_RESTART=10000    # Worker recycling
  - USE_PRISMA_MIGRATE=true              # Production migrations

command:
  - --num_workers 4                      # Match CPU count
  - --run_gunicorn                       # Stable worker management
  - --max_requests_before_restart 10000  # Prevent memory leaks
```

### Key Settings (config.yaml)

```yaml
general_settings:
  database_connection_pool_limit: 10     # Per worker (40 total with 4 workers)
  proxy_batch_write_at: 60               # Batch DB writes
  disable_error_logs: true               # Reduce DB load

litellm_settings:
  request_timeout: 600                   # Sufficient for reasoning models
  set_verbose: false                     # Disable debug logging
  json_logs: true                        # Structured logging

router_settings:
  routing_strategy: simple-shuffle       # Best performance
  allowed_fails: 3                       # Fast failure detection
  cooldown_time: 30                      # Quick recovery
```

---

## Monitoring

### Health Checks

- **Main API:** http://localhost:4000/health
- **Separate Health App:** http://localhost:4001/health/liveliness (used by K8s probes)
- **Readiness:** http://localhost:4001/health/readiness

### Logs

```bash
# View all logs
docker-compose logs -f

# View only LiteLLM logs
docker-compose logs -f litellm

# View only errors (production mode)
docker-compose logs -f litellm | grep ERROR
```

### Metrics

LiteLLM exposes Prometheus metrics at:

```
http://localhost:4000/metrics
```

---

## Optional: Slack Alerting

### 1. Create Slack Webhook

1. Go to https://api.slack.com/messaging/webhooks
2. Create a new webhook for your workspace
3. Copy the webhook URL

### 2. Enable Alerting

Add to `.env`:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Uncomment in `config.yaml`:

```yaml
litellm_settings:
  failure_callback: ["slack"]  # Uncomment this line
```

Restart:

```bash
docker-compose restart litellm
```

### What You'll Get Alerts For:

- LLM exceptions (API errors, timeouts)
- Budget alerts (if budget limits are set)
- Slow LLM responses (based on `alerting_threshold`)

---

## Performance Expectations

Based on [official benchmarks](https://docs.litellm.ai/docs/benchmarks):

| Configuration | Expected RPS | P99 Latency |
|---------------|--------------|-------------|
| 4 workers, 40 DB conns | 100+ | <500ms |
| With Redis cache | 200+ | <300ms |

**Your configuration matches official recommendations for:**

- 4 vCPU
- 8 GB RAM
- Single instance deployment

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs litellm

# Common issues:
# - Missing .env file → Copy from .env.example
# - Invalid DATABASE_URL → Check password matches POSTGRES_PASSWORD
# - Missing API keys → Add OLLAMA_API_KEY, GEMINI_API_KEY to .env
```

### Health Check Fails

```bash
# Check if separate health app is running
curl http://localhost:4001/health/liveliness

# If fails, check environment variables
docker-compose exec litellm env | grep SEPARATE_HEALTH
# Should show SEPARATE_HEALTH_APP=1 and SEPARATE_HEALTH_PORT=4001
```

### Models Timeout

```bash
# Check request_timeout in config.yaml
grep request_timeout config.yaml
# Should show 600 (not 120)

# For specific models, you can override in litellm_params:
# litellm_params:
#   timeout: 900  # 15 minutes for ultra-slow reasoning models
```

### Connection Pool Exhausted

```bash
# Check current settings
grep database_connection_pool_limit config.yaml
# Should show 10 (per worker)

# Check worker count
docker-compose exec litellm ps aux | grep gunicorn
# Should show 4 worker processes

# Total connections = 10 × 4 = 40 (optimal for single instance)
```

---

## Next Steps

1. ✅ **Deploy to production** - Configuration is production-ready
2. 🔧 **Set up monitoring** - Add Prometheus + Grafana for metrics
3. 📊 **Enable Slack alerts** - Get notified of issues
4. 🔄 **Scale horizontally** - Add more instances if needed (adjust connection pool)

---

## References

- [Official Production Best Practices](https://docs.litellm.ai/docs/proxy/prod)
- [Configuration Settings Reference](https://docs.litellm.ai/docs/proxy/config_settings)
- [Detailed Alignment Report](./OFFICIAL_DOCS_ALIGNMENT.md)

---

## Support

**Official LiteLLM Support:**
- Docs: https://docs.litellm.ai/
- GitHub: https://github.com/BerriAI/litellm
- Calendar: https://calendly.com/d/4mp-gd3-k5k/litellm-1-1-onboarding-chat

**Configuration Issues:**
- Review `OFFICIAL_DOCS_ALIGNMENT.md` for detailed explanations
- Check official docs for latest recommendations
- All settings include inline comments with doc references

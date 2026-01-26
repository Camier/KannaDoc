#!/bin/bash
# Quick Start: Production Hardening in 10 Minutes
# Applies all critical changes automatically

set -e

echo "=== LiteLLM Production Hardening (Quick Start) ==="
echo ""

# Backup originals
echo "[1/5] Backing up original files..."
cp config.yaml config.yaml.backup.$(date +%s)
cp .env .env.backup.$(date +%s)
cp docker-compose.yml docker-compose.yml.backup.$(date +%s)
cp Dockerfile Dockerfile.backup.$(date +%s)
echo "✓ Backups created"
echo ""

# Generate random salt key
SALT_KEY="sk-$(openssl rand -hex 32)"

# Update .env
echo "[2/5] Updating .env..."
cat >> .env <<EOF

# === Production Hardening ($(date +%Y-%m-%d)) ===
# Logging & Debug
LITELLM_MODE=PRODUCTION
LITELLM_LOG=ERROR

# Health Check App (Separate Process)
SEPARATE_HEALTH_APP=1
SEPARATE_HEALTH_PORT=4001
SUPERVISORD_STOPWAITSECS=3600

# Worker Recycling
MAX_REQUESTS_BEFORE_RESTART=10000

# Encryption Salt Key
LITELLM_SALT_KEY=$SALT_KEY

# Slack Alerting (OPTIONAL: Set your webhook URL)
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EOF
echo "✓ .env updated (salt key: ${SALT_KEY:0:20}...)"
echo ""

# Update config.yaml - Pool limits
echo "[3/5] Updating config.yaml..."

# 1. Fix database_connection_pool_limit
sed -i.bak 's/database_connection_pool_limit: 25/database_connection_pool_limit: 50/' config.yaml

# 2. Add proxy_batch_write_at if not exists
if ! grep -q "proxy_batch_write_at" config.yaml; then
  sed -i.bak '/database_connection_pool_limit: 50/a\  proxy_batch_write_at: 60' config.yaml
fi

# 3. Fix redis_connection_pool_limit
sed -i.bak 's/redis_connection_pool_limit: 20/redis_connection_pool_limit: 50/' config.yaml

# 4. Fix cooldown_time
sed -i.bak 's/cooldown_time: 120/cooldown_time: 60/' config.yaml

# 5. Add retry policy if not exists
if ! grep -q "retry_policy:" config.yaml; then
  cat >> config.yaml <<'RETRY_POLICY'

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
RETRY_POLICY
fi

# 6. Fix logging level
sed -i.bak 's/set_verbose: True/set_verbose: False/' config.yaml 2>/dev/null || true

# 7. Add failure callback
if ! grep -q "failure_callback" config.yaml; then
  sed -i.bak '/litellm_settings:/a\  failure_callback: ["slack"]' config.yaml
fi

# 8. Add alerting to general_settings if not exists
if ! grep -q "alerting:" config.yaml; then
  sed -i.bak '/enable_metrics: true/a\  alerting: ["slack"]\n  alerting_threshold: 1000' config.yaml
fi

echo "✓ config.yaml updated (pools 50, retries granular, logging ERROR)"
echo ""

# Update Dockerfile
echo "[4/5] Updating Dockerfile..."
sed -i.bak 's|CMD \["litellm"\]|ENTRYPOINT ["litellm"]|' Dockerfile
sed -i.bak 's|CMD \["--config"|CMD ["--port", "4000", "--config"|' Dockerfile
if ! grep -q "run_gunicorn" Dockerfile; then
  sed -i.bak 's|--config", "/app/config.yaml", "--port", "4000"|--port", "4000", "--config", "/app/config.yaml", "--num_workers", "4", "--run_gunicorn", "--max_requests_before_restart", "10000"|' Dockerfile
fi
echo "✓ Dockerfile updated (gunicorn + worker recycling)"
echo ""

# Update docker-compose.yml
echo "[5/5] Updating docker-compose.yml..."

# 1. Add 4001 port
if ! grep -q '4001:4001' docker-compose.yml; then
  sed -i.bak '/- "4000:4000"/a\      - "4001:4001"' docker-compose.yml
fi

# 2. Update environment variables
sed -i.bak 's/- LITELLM_LOG=INFO/- LITELLM_LOG=ERROR/' docker-compose.yml
# Add new vars after existing LITELLM_LOG
sed -i.bak '/- LITELLM_LOG=ERROR/a\      - SEPARATE_HEALTH_APP=1\n      - SEPARATE_HEALTH_PORT=4001\n      - SUPERVISORD_STOPWAITSECS=3600\n      - MAX_REQUESTS_BEFORE_RESTART=10000' docker-compose.yml

# 3. Update healthcheck
sed -i.bak 's|test: \["CMD", "python3"|test: ["CMD", "curl", "-f", "http://localhost:4001/health/liveliness"|' docker-compose.yml
sed -i.bak 's|timeout: 10s|timeout: 5s|' docker-compose.yml

echo "✓ docker-compose.yml updated (health check on 4001, env vars added)"
echo ""

# Done
echo "=== Summary ==="
echo "✅ Pool limits: 20 → 50 connections"
echo "✅ Worker recycling: Enabled (10k requests)"
echo "✅ Logging: INFO → ERROR (less spam)"
echo "✅ Health check: Separate app on port 4001"
echo "✅ Retry policy: Smart per-error-type"
echo "✅ Graceful shutdown: 3600s timeout"
echo ""
echo "=== Next Steps ==="
echo "1. Review changes: git diff config.yaml .env docker-compose.yml Dockerfile"
echo "2. Rebuild: docker compose build litellm"
echo "3. Restart: docker compose down && docker compose up -d"
echo "4. Wait: sleep 60"
echo "5. Test: python3 bin/health_check.py && python3 bin/probe_models.py"
echo ""
echo "=== Rollback (if needed) ==="
echo "# Find backup files:"
echo "ls -la config.yaml.backup.* .env.backup.* docker-compose.yml.backup.* Dockerfile.backup.*"
echo "# Restore:"
echo "cp config.yaml.backup.XXXXX config.yaml  # Replace XXXXX with latest timestamp"
echo ""

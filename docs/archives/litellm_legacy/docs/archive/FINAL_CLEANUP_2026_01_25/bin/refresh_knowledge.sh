#!/bin/bash
# LiteLLM Knowledge Refresh Script
# Updates model documentation and capabilities from running proxy

set -euo pipefail

# Configuration
PROXY_URL="${LITELLM_REFRESH_URL:-http://127.0.0.1:4000}"
API_KEY="${LITELLM_MASTER_KEY:-}"
GENERATED_DIR="/LAB/@litellm/docs/generated"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_PREFIX="[LiteLLM-Knowledge-Refresh]"

# Logging function
log() {
    echo "${LOG_PREFIX} $*" >&2
}

error() {
    echo "${LOG_PREFIX} ERROR: $*" >&2
    exit 1
}

# Ensure generated directory exists
mkdir -p "${GENERATED_DIR}"

# Health check first with retries
log "Checking proxy health at ${PROXY_URL}..."
HEALTH_CHECKS=5
WAIT_SEC=3

for i in $(seq 1 $HEALTH_CHECKS); do
    if curl -sf "${PROXY_URL}/health" >/dev/null 2>&1; then
        log "Proxy is healthy"
        break
    fi
    if [[ $i -eq $HEALTH_CHECKS ]]; then
        log "WARNING: Proxy not healthy after ${HEALTH_CHECKS} attempts - creating minimal report"
        # Create minimal timestamp report
        cat > "${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md" <<EOF
# Model Inventory Report

**Generated:** ${TIMESTAMP}
**Status:** Proxy unavailable - could not fetch model data

The LiteLLM proxy at ${PROXY_URL} was not responding. This report will be
updated automatically when the proxy is available.

*Last successful refresh: See .last_refresh file*
EOF
        echo "${TIMESTAMP}" > "${GENERATED_DIR}/.last_refresh_attempt"
        log "Created placeholder report"
        exit 0  # Exit gracefully - timer will retry
    fi
    log "Attempt ${i}/${HEALTH_CHECKS} failed, waiting ${WAIT_SEC}s..."
    sleep $WAIT_SEC
done

# Fetch model list
log "Fetching model list..."
AUTH_HEADER=""
if [[ -n "${API_KEY}" ]]; then
    AUTH_HEADER="-H \"Authorization: Bearer ${API_KEY}\""
fi

MODEL_INFO=$(curl -s ${AUTH_HEADER} "${PROXY_URL}/model/info" 2>/dev/null) || {
    error "Failed to fetch model info from ${PROXY_URL}/model/info"
}

# Validate we got JSON
if ! echo "${MODEL_INFO}" | jq empty 2>/dev/null; then
    error "Invalid JSON response from proxy"
fi

# Count models
MODEL_COUNT=$(echo "${MODEL_INFO}" | jq '.data | length' 2>/dev/null || echo "0")
log "Retrieved ${MODEL_COUNT} models"

# Update model inventory report
cat > "${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md" <<EOF
# Model Inventory Report

**Generated:** ${TIMESTAMP}
**Source:** ${PROXY_URL}/model/info
**Total Models:** ${MODEL_COUNT}

## Quick Reference

EOF

# Add model table
echo "${MODEL_INFO}" | jq -r '
.data[] |
"- **\(.model_name)**: \(.litellm_params.provider // "unknown") provider, mode: \(.model_info.mode // "unknown")"
' >> "${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md" 2>/dev/null || true

# Add detailed section
cat >> "${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md" <<EOF

## Detailed Model List

EOF

echo "${MODEL_INFO}" | jq -r '
.data[] |
{
  name: .model_name,
  provider: .litellm_params.provider,
  mode: (.model_info.mode // "unknown"),
  supports_vision: (.litellm_params.vision // false),
  supports_function_calling: (.litellm_params.drop_params // true)
} |
"### \(.name)

- **Provider:** \(.provider)
- **Mode:** \(.mode)
- **Vision Support:** \(.supports_vision)
- **Function Calling:** \(.supports_function_calling)

"
' >> "${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md" 2>/dev/null || {
    echo "# Error parsing model details" >> "${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md"
}

log "Updated ${GENERATED_DIR}/MODEL_INVENTORY_REPORT.md"

# Create simple capabilities summary
cat > "${GENERATED_DIR}/MODEL_CAPABILITIES.md" <<EOF
# Model Capabilities Summary

**Generated:** ${TIMESTAMP}
**Source:** Auto-generated from running proxy

EOF

echo "${MODEL_INFO}" | jq -r '
.data[] |
select(.model_info.mode == "chat" or .model_info.mode == "completion") |
"## \(.model_name)

\(.model_info.description // "No description")

**Type:** \(.model_info.mode // "unknown") |
**Provider:** \(.litellm_params.provider // "unknown")

"
' 2>/dev/null | head -100 >> "${GENERATED_DIR}/MODEL_CAPABILITIES.md" || true

log "Updated ${GENERATED_DIR}/MODEL_CAPABILITIES.md"

# Update timestamp file
echo "${TIMESTAMP}" > "${GENERATED_DIR}/.last_refresh"

log "Knowledge refresh complete"
exit 0

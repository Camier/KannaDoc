#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# LAYRA Startup Script (clean-compose wrapper)
# ==============================================================================
# Root cause we want to eliminate:
#   - Docker Compose variable interpolation prefers exported host env vars over
#     values in `.env`, so a "polluted shell" can silently break the deployment.
#
# Solution:
#   - Always run Compose via `./compose-clean` (env -i allowlist + --env-file .env)
# ==============================================================================

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$script_dir"

if [[ ! -x ./compose-clean ]]; then
  echo "❌ Missing executable ./compose-clean in repo root." >&2
  echo "   Fix: chmod +x ./compose-clean" >&2
  echo "   Then run: ./compose-clean up -d --build" >&2
  exit 1
fi

echo "✅ Using ./compose-clean (sanitized env) to start LAYRA."

# 2. Check for .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one from .env.example."
    exit 1
fi

# 3. Start Services (Clean Slate)
echo "🚀 Starting LAYRA services..."
# --force-recreate ensures containers are recreated with the clean env vars
# --remove-orphans cleans up any old containers from previous configs
./compose-clean up -d --build --force-recreate --remove-orphans

echo ""
echo "=============================================================================="
echo "🎉 LAYRA Deployment Successful (Isolated Environment)!"
echo "=============================================================================="

server_ip="$(grep -E '^SERVER_IP=' .env | head -n 1 | cut -d'=' -f2- | tr -d '\r' || true)"
server_ip="${server_ip#http://}"
server_ip="${server_ip#https://}"
server_ip="${server_ip%%/*}"
server_host="${server_ip%%:*}"
server_host="${server_host:-localhost}"

echo "👉 Frontend: http://${server_host}:8090"
echo "👉 Backend:  http://${server_host}:8090/api/v1/health/check"
echo ""
echo "🛠️  Verification:"
echo "   Checking backend configuration..."
BACKEND_MODEL="$(./compose-clean exec -T backend printenv EMBEDDING_MODEL 2>/dev/null || echo 'Error reading env')"
echo "   - Backend Model: $BACKEND_MODEL (Should be 'local_colqwen')"
echo ""
echo "Useful commands:"
echo "  - Logs:    ./compose-clean logs -f backend"
echo "  - Stop:    ./compose-clean stop"
echo "  - Restart: ./start_layra.sh"
echo "=============================================================================="

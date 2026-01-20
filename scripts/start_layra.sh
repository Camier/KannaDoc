#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# LAYRA Startup Script (clean-compose wrapper)
# ==============================================================================

# Resolve project root (assuming script is in scripts/ directory)
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
project_root="$(dirname "$script_dir")"
cd "$project_root"

if [[ ! -x ./scripts/compose-clean ]]; then
  echo "❌ Missing executable ./scripts/compose-clean in repo root." >&2
  echo "   Fix: chmod +x ./scripts/compose-clean" >&2
  exit 1
fi

echo "✅ Using ./scripts/compose-clean (sanitized env) to start LAYRA."

# 2. Check for .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one from .env.example."
    exit 1
fi

# 3. Start Services (Clean Slate)
echo "🚀 Starting LAYRA services..."
./scripts/compose-clean up -d --build --force-recreate --remove-orphans

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
BACKEND_MODEL="$(./scripts/compose-clean exec -T backend printenv EMBEDDING_MODEL 2>/dev/null || echo 'Error reading env')"
echo "   - Backend Model: $BACKEND_MODEL (Should be 'local_colqwen')"
echo ""
echo "Useful commands:"
echo "  - Logs:    ./scripts/compose-clean logs -f backend"
echo "  - Stop:    ./scripts/compose-clean stop"
echo "  - Restart: ./scripts/start_layra.sh"
echo "=============================================================================="
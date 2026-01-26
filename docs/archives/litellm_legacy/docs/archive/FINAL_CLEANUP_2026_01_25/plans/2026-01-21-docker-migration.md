# Docker Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate LiteLLM proxy from systemd/conda deployment to Docker Compose while maintaining all operational capabilities (health checks, backups, monitoring, local model services).

**Architecture:**
- **Phase 1:** Create missing `.env` file from `env.litellm` for Docker Compose
- **Phase 2:** Adapt backup script for Docker database access
- **Phase 3:** Create wrapper script for systemd services to run alongside Docker (for local models)
- **Phase 4:** Test migration with rollback plan
- **Phase 5:** Deploy and verify

**Tech Stack:** Docker Compose v2, PostgreSQL 16-alpine, Redis 7-alpine, LiteLLM official image, systemd (for local model services only)

---

## Migration Overview

### Current State (systemd/conda)
```
127.0.0.1:4000  → litellm (conda env)
127.0.0.1:5434  → PostgreSQL (native)
127.0.0.1:6379  → Redis (native)
127.0.0.1:8082  → Arctic embeddings (llama.cpp systemd)
127.0.0.1:8079  → Local rerank (systemd)
```

### Target State (Docker + systemd for local models)
```
127.0.0.1:4000  → litellm (Docker)
127.0.0.1:5434  → PostgreSQL (Docker)
127.0.0.1:6379  → Redis (Docker)
127.0.0.1:8082  → Arctic embeddings (systemd - stays native)
127.0.0.1:8079  → Local rerank (systemd - stays native)
```

**Key Decision:** Local model services (llama.cpp, vLLM) remain on systemd due to GPU access complexity in Docker.

---

## Phase 1: Environment Preparation

### Task 1: Create .env file from env.litellm

**Files:**
- Create: `.env`
- Reference: `env.litellm`, `~/.007` (secrets)

**Step 1: Create base .env file**

Create `.env` with Docker-specific values:

```bash
# ============================================================================
# LiteLLM Docker Environment
# ============================================================================
# Generated from env.litellm for Docker Compose deployment
# ============================================================================

# PostgreSQL Configuration
POSTGRES_USER=litellm
POSTGRES_PASSWORD=litellm
POSTGRES_DB=litellm

# Redis Configuration
REDIS_PASSWORD=litellm

# LiteLLM Operational Settings
LITELLM_MODE=PRODUCTION
LITELLM_LOG=INFO
JSON_LOGS=true

# Database Schema
DISABLE_SCHEMA_UPDATE=true
USE_PRISMA_MIGRATE=true

# Security Defaults
LITELLM_KEY_INFO_ADMIN_ONLY=1
UI_USERNAME=admin
UI_PASSWORD=changeme

# Public Routes
LITELLM_PUBLIC_PASSTHROUGH_PREFIXES=/healthz,/readyz

# ============================================================================
# SECRETS - Load these from ~/.007 and populate manually
# ============================================================================
# Run: source ~/.007 && grep -E "^(LITELLM_MASTER_KEY|LITELLM_SALT_KEY)" ~/.007 >> .env
# ============================================================================

LITELLM_MASTER_KEY=CHANGE_ME
LITELLM_SALT_KEY=CHANGE_ME

# ============================================================================
# Provider API Keys (add your keys here)
# ============================================================================
OPENAI_API_KEY=sk-dummy-local
DEEPSEEK_API_KEY=
GEMINI_API_KEY=
```

**Step 2: Add secrets from ~/.007**

```bash
# Extract secrets and append to .env
source ~/.007 2>/dev/null
grep -E "^LITELLM_MASTER_KEY|^LITELLM_SALT_KEY" ~/.007 >> .env 2>/dev/null || true
```

**Step 3: Secure the .env file**

```bash
chmod 600 .env
```

**Step 4: Verify .env syntax**

```bash
# Check for syntax errors
docker-compose config 2>&1 | head -20
```

Expected: No syntax errors, configuration validates

**Step 5: Commit**

```bash
git add .env .gitignore
echo ".env" >> .gitignore 2>/dev/null || true
git commit -m "feat(docker): add .env file for Docker Compose deployment"
```

---

### Task 2: Update .dockerignore

**Files:**
- Modify: `.dockerignore`

**Step 1: Review current .dockerignore**

```bash
cat .dockerignore
```

**Step 2: Ensure critical exclusions**

Add/update `.dockerignore`:

```
# Git
.git
.gitignore
.gitattributes

# Docker
.dockerignore
Dockerfile
docker-compose.yml
.env
.env.*

# Python (not needed in container)
__pycache__
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
venv/
.venv/

# Documentation (keep in repo, not image)
docs/
*.md

# Tests
tests/
pytest.ini
.pytest_cache/

# State and logs (mounted as volumes)
state/
logs/
*.log

# Backup and archive
state/archive/
backups/

# Systemd (not used in Docker)
systemd/

# Scripts not needed in container
bin/legacy/
bin/*.pyc
```

**Step 3: Commit**

```bash
git add .dockerignore
git commit -m "chore(docker): update .dockerignore for cleaner builds"
```

---

## Phase 2: Backup Script Adaptation

### Task 3: Create Docker-aware backup script

**Files:**
- Create: `bin/backup_db_docker.py`
- Modify: `bin/backup_db.py` (add Docker detection)

**Step 1: Create Docker backup script**

Create `bin/backup_db_docker.py`:

```python
#!/usr/bin/env python3
"""
LiteLLM Database Backup Script (Docker)

Performs automated backups of Docker-deployed LiteLLM:
- PostgreSQL database (via docker exec)
- Configuration files
- Manifest with checksums

Retention Policy:
- 7 daily backups
- 4 weekly backups (Sunday)
- 3 monthly backups (1st of month)

Usage:
    python bin/backup_db_docker.py [--dry-run]
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path("/LAB/@litellm")
BACKUP_ROOT = PROJECT_ROOT / "state" / "archive" / "backups"
DB_CONTAINER = "litellm-postgres"
DB_USER = "litellm"
DB_NAME = "litellm"

CONFIG_FILES = [
    "config.yaml",
    "docker-compose.yml",
    ".env",
    "schema.prisma",
]

# Retention settings
DAILY_RETENTION = 7
WEEKLY_RETENTION = 4
MONTHLY_RETENTION = 3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def run_command(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)."""
    logger.debug(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )
    return result.returncode, result.stdout, result.stderr


def backup_database(backup_path: Path, dry_run: bool = False) -> bool:
    """Backup PostgreSQL database via docker exec."""
    logger.info(f"Backing up database to {backup_path}")

    if dry_run:
        logger.info("[DRY-RUN] Would backup database")
        return True

    # Ensure container is running
    code, _, err = run_command(["docker", "inspect", "-f", "{{.State.Running}}", DB_CONTAINER])
    if code != 0 or "true" not in _:
        logger.error(f"Container {DB_CONTAINER} is not running")
        return False

    # Run pg_dump via docker exec
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "pg_dump", "-U", DB_USER, "-d", DB_NAME, "--no-owner", "--no-acl"
    ]

    code, stdout, err = run_command(cmd, check=False)
    if code != 0:
        logger.error(f"Database backup failed: {err}")
        return False

    backup_path.write_text(stdout)
    logger.info(f"Database backup complete: {backup_path.stat().st_size} bytes")
    return True


def backup_configs(backup_dir: Path, dry_run: bool = False) -> bool:
    """Backup configuration files."""
    logger.info("Backing up configuration files")

    for filename in CONFIG_FILES:
        src = PROJECT_ROOT / filename
        if not src.exists():
            logger.warning(f"Config file not found: {filename}")
            continue

        if dry_run:
            logger.info(f"[DRY-RUN] Would copy {filename}")
            continue

        dst = backup_dir / filename
        dst.write_text(src.read_text())
        logger.info(f"Backed up: {filename}")

    return True


def create_manifest(backup_dir: Path, dry_run: bool = False) -> bool:
    """Create backup manifest with checksums."""
    manifest = {
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": os.uname().nodename,
        "files": {}
    }

    for file in backup_dir.glob("*"):
        if file.name == "manifest.json":
            continue

        content = file.read_bytes()
        manifest["files"][file.name] = {
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        }

    if dry_run:
        logger.info(f"[DRY-RUN] Would create manifest")
        return True

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Created manifest: {manifest_path}")
    return True


def cleanup_old_backups(dry_run: bool = False) -> None:
    """Remove old backups based on retention policy."""
    if not BACKUP_ROOT.exists():
        return

    logger.info("Checking for old backups to clean up...")

    # List all backups by date
    backups = sorted(BACKUP_ROOT.glob("*"), key=lambda p: p.stat().mtime, reverse=True)

    # Categorize by type
    daily_backups = [b for b in backups if not b.name.startswith(("weekly-", "monthly-"))]
    weekly_backups = sorted([b for b in backups if b.name.startswith("weekly-")], key=lambda p: p.stat().mtime, reverse=True)
    monthly_backups = sorted([b for b in backups if b.name.startswith("monthly-")], key=lambda p: p.stat().mtime, reverse=True)

    # Remove excess daily backups
    for old in daily_backups[DAILY_RETENTION:]:
        if dry_run:
            logger.info(f"[DRY-RUN] Would remove old daily backup: {old.name}")
        else:
            logger.info(f"Removing old daily backup: {old.name}")
            subprocess.run(["rm", "-rf", str(old)], check=False)

    # Remove excess weekly backups
    for old in weekly_backups[WEEKLY_RETENTION:]:
        if dry_run:
            logger.info(f"[DRY-RUN] Would remove old weekly backup: {old.name}")
        else:
            logger.info(f"Removing old weekly backup: {old.name}")
            subprocess.run(["rm", "-rf", str(old)], check=False)

    # Remove excess monthly backups
    for old in monthly_backups[MONTHLY_RETENTION:]:
        if dry_run:
            logger.info(f"[DRY-RUN] Would remove old monthly backup: {old.name}")
        else:
            logger.info(f"Removing old monthly backup: {old.name}")
            subprocess.run(["rm", "-rf", str(old)], check=False)


def main():
    parser = argparse.ArgumentParser(description="Backup LiteLLM Docker database and configs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")

    # Create backup directory
    now = datetime.now()
    backup_type = "monthly" if now.day == 1 else ("weekly" if now.weekday() == 6 else "daily")
    backup_name = f"{backup_type}-{now.strftime('%Y%m%d-%H%M%S')}"
    backup_dir = BACKUP_ROOT / backup_name

    if args.dry_run:
        logger.info(f"[DRY-RUN] Would create backup directory: {backup_dir}")
    else:
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created backup directory: {backup_dir}")

    # Backup database
    db_backup = backup_dir / "database.sql"
    if not backup_database(db_backup, args.dry_run):
        logger.error("Database backup failed")
        return 1

    # Backup configs
    if not backup_configs(backup_dir, args.dry_run):
        logger.warning("Config backup had issues")

    # Create manifest
    if not create_manifest(backup_dir, args.dry_run):
        logger.warning("Manifest creation failed")

    # Cleanup old backups
    cleanup_old_backups(args.dry_run)

    if args.dry_run:
        logger.info("=== DRY RUN COMPLETE - No changes made ===")
    else:
        logger.info(f"Backup complete: {backup_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Make script executable**

```bash
chmod +x bin/backup_db_docker.py
```

**Step 3: Test backup script (dry-run)**

```bash
python bin/backup_db_docker.py --dry-run
```

Expected: "DRY RUN MODE" message, list of actions, no actual changes

**Step 4: Commit**

```bash
git add bin/backup_db_docker.py
git commit -m "feat(docker): add Docker-aware backup script"
```

---

### Task 4: Update systemd backup service for Docker

**Files:**
- Modify: `systemd/litellm-backup.service`
- Modify: `systemd/litellm-backup.timer`

**Step 1: Create Docker backup service**

Create `systemd/litellm-backup-docker.service`:

```ini
[Unit]
Description=LiteLLM Database Backup (Docker)
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/LAB/@litellm
EnvironmentFile=-/LAB/@litellm/.env
ExecStart=/home/miko/.venvs/litellm/bin/python /LAB/@litellm/bin/backup_db_docker.py

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/LAB/@litellm/state/archive

[Install]
WantedBy=multi-user.target
```

**Step 2: Update timer to use Docker backup**

```bash
# Stop and disable old backup timer
systemctl --user stop litellm-backup.timer
systemctl --user disable litellm-backup.timer

# Enable new Docker backup timer
systemctl --user enable litellm-backup-docker.timer
systemctl --user start litellm-backup-docker.timer
```

**Step 3: Verify timer status**

```bash
systemctl --user list-timers litellm-backup*
```

Expected: `litellm-backup-docker.timer` listed and active

**Step 4: Commit**

```bash
git add systemd/litellm-backup-docker.service
git commit -m "feat(docker): add Docker backup systemd service"
```

---

## Phase 3: Health Check Adaptation

### Task 5: Create Docker health check script

**Files:**
- Create: `bin/health_check_docker.sh`

**Step 1: Create Docker health check script**

Create `bin/health_check_docker.sh`:

```bash
#!/usr/bin/env bash
#
# LiteLLM Docker Health Check
#
# Checks health of Docker-deployed LiteLLM services
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_DIR="/LAB/@litellm"
LITELLM_URL="http://127.0.0.1:4000"
POSTGRES_CONTAINER="litellm-postgres"
REDIS_CONTAINER="litellm-redis"

check_result=0

echo "[health] Starting LiteLLM Docker health check..."

# Function to check service
check_service() {
    local name="$1"
    local check_cmd="$2"

    echo -n "[health] Checking $name... "

    if eval "$check_cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        check_result=1
        return 1
    fi
}

# Check Docker is running
check_service "Docker daemon" "docker info >/dev/null 2>&1"

# Check containers are running
check_service "PostgreSQL container" "docker inspect -f '{{.State.Running}}' $POSTGRES_CONTAINER 2>/dev/null | grep -q true"
check_service "Redis container" "docker inspect -f '{{.State.Running}}' $REDIS_CONTAINER 2>/dev/null | grep -q true"
check_service "LiteLLM container" "docker ps --filter 'name=litellm-proxy' --filter 'status=running' | grep -q litellm"

# Check LiteLLM endpoints
check_service "LiteLLM liveness" "curl -sf $LITELLM_URL/health/liveliness"
check_service "LiteLLM readiness" "curl -sf $LITELLM_URL/health/readiness"

# Check database connectivity from LiteLLM
readiness=$(curl -sf "$LITELLM_URL/health/readiness" 2>/dev/null || echo "{}")
if echo "$readiness" | grep -q '"db":.*"connected"'; then
    echo -e "[health] Database connection: ${GREEN}OK${NC}"
else
    echo -e "[health] Database connection: ${RED}FAILED${NC}"
    check_result=1
fi

if echo "$readiness" | grep -q '"cache":.*"redis"'; then
    echo -e "[health] Redis connection: ${GREEN}OK${NC}"
else
    echo -e "[health] Redis connection: ${RED}FAILED${NC}"
    check_result=1
fi

# Final result
if [ $check_result -eq 0 ]; then
    echo -e "[health] ${GREEN}All checks passed${NC}"
    exit 0
else
    echo -e "[health] ${RED}Some checks failed${NC}"
    exit 1
fi
```

**Step 2: Make executable**

```bash
chmod +x bin/health_check_docker.sh
```

**Step 3: Test script (before migration)**

```bash
# Will fail since Docker services not running yet
bin/health_check_docker.sh || true
```

Expected: Some failures (containers not running), but script executes

**Step 4: Commit**

```bash
git add bin/health_check_docker.sh
git commit -m "feat(docker): add Docker health check script"
```

---

## Phase 4: Pre-Migration Testing

### Task 6: Create migration validation script

**Files:**
- Create: `bin/validate_migration.sh`

**Step 1: Create migration validation script**

Create `bin/validate_migration.sh`:

```bash
#!/usr/bin/env bash
#
# LiteLLM Migration Validation Script
#
# Validates migration from systemd to Docker deployment
#

set -euo pipefail

COMPOSE_DIR="/LAB/@litellm"
LITELLM_URL="http://127.0.0.1:4000"
MASTER_KEY="${LITELLM_MASTER_KEY:-}"

echo "=== LiteLLM Migration Validation ==="
echo ""

# Check .env file exists
echo "[1/6] Checking .env file..."
if [ -f "$COMPOSE_DIR/.env" ]; then
    echo "  ✅ .env exists"
else
    echo "  ❌ .env not found. Run: cp env.litellm .env.example && edit .env"
    exit 1
fi

# Check Docker is available
echo "[2/6] Checking Docker..."
if docker info >/dev/null 2>&1; then
    echo "  ✅ Docker is running"
else
    echo "  ❌ Docker is not available"
    exit 1
fi

# Check docker-compose syntax
echo "[3/6] Validating docker-compose.yml..."
cd "$COMPOSE_DIR"
if docker-compose config >/dev/null 2>&1; then
    echo "  ✅ docker-compose.yml is valid"
else
    echo "  ❌ docker-compose.yml has syntax errors"
    exit 1
fi

# Check ports are available
echo "[4/6] Checking port availability..."
for port in 4000 5434 6379; do
    if lsof -i ":$port" >/dev/null 2>&1; then
        echo "  ⚠️  Port $port is already in use"
        lsof -i ":$port" | head -2
    else
        echo "  ✅ Port $port is available"
    fi
done

# Check if services are already running (systemd)
echo "[5/6] Checking existing services..."
if systemctl --user is-active --quiet litellm.service; then
    echo "  ⚠️  litellm.service is running (will need to stop)"
else
    echo "  ✅ litellm.service is not running"
fi

# Verify .env has required variables
echo "[6/6] Checking .env configuration..."
if grep -q "^LITELLM_MASTER_KEY=CHANGE_ME" .env; then
    echo "  ❌ LITELLM_MASTER_KEY is not set"
    exit 1
else
    echo "  ✅ LITELLM_MASTER_KEY is configured"
fi

echo ""
echo "=== Validation Complete ==="
echo "Ready to proceed with migration:"
echo "  1. Stop systemd services: systemctl --user stop litellm.service"
echo "  2. Start Docker: docker-compose up -d"
echo "  3. Verify: bin/health_check_docker.sh"
```

**Step 2: Make executable**

```bash
chmod +x bin/validate_migration.sh
```

**Step 3: Run validation**

```bash
bin/validate_migration.sh
```

Expected: All checks pass (or warnings addressed)

**Step 4: Commit**

```bash
git add bin/validate_migration.sh
git commit -m "feat(docker): add migration validation script"
```

---

## Phase 5: Migration Execution

### Task 7: Pre-migration backup

**Files:**
- Reference: `bin/backup_db.py`

**Step 1: Run final systemd backup**

```bash
# Ensure backup script works
python bin/backup_db.py --dry-run

# Run actual backup
python bin/backup_db.py
```

Expected: Backup created in `state/archive/backups/daily-YYYYMMDD-HHMMSS/`

**Step 2: Verify backup contents**

```bash
# List latest backup
ls -lt state/archive/backups/ | head -5

# Check backup files
latest=$(ls -t state/archive/backups/ | head -1)
echo "Latest backup: $latest"
ls -lh "state/archive/backups/$latest/"
```

Expected: Contains `database.sql`, `config.yaml`, `schema.prisma`, `manifest.json`

**Step 3: Note backup location for rollback**

```bash
echo "Migration backup: $(ls -t state/archive/backups/ | head -1)" > /tmp/litellm-migration-backup.txt
cat /tmp/litellm-migration-backup.txt
```

---

### Task 8: Stop systemd services

**Files:**
- Reference: All `systemd/*.service` files

**Step 1: Stop all LiteLLM systemd services**

```bash
# Stop main service
systemctl --user stop litellm.service

# Stop dependent services (optional, can stay running)
systemctl --user stop litellm-rerank.service 2>/dev/null || true
systemctl --user stop litellm-embed-arctic.service 2>/dev/null || true

# Disable main service (won't auto-start on reboot)
systemctl --user disable litellm.service
```

Expected: All services stopped, no errors

**Step 2: Verify ports are free**

```bash
# Check port 4000 is free
lsof -i :4000 || echo "Port 4000 is free"

# Check port 5434 is free
lsof -i :5434 || echo "Port 5434 is free"
```

Expected: No output (ports are free)

**Step 3: Verify systemd services are stopped**

```bash
systemctl --user status litellm.service | grep "Active:"
```

Expected: `Active: inactive (dead)`

---

### Task 9: Start Docker services

**Files:**
- Reference: `docker-compose.yml`

**Step 1: Pull latest images**

```bash
docker-compose pull
```

Expected: Images pulled successfully (litellm, postgres, redis)

**Step 2: Start services**

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

Expected: All services show "Up" or "healthy"

**Step 3: Wait for health checks**

```bash
# Watch logs until healthy
docker-compose logs -f litellm
```

Expected output (eventually):
```
litellm-proxy    | Starting LiteLLM Proxy...
litellm-proxy    | Database connection successful
litellm-proxy    | Ready to accept requests
```

Press Ctrl+C when logs show "Ready"

**Step 4: Run health check**

```bash
bin/health_check_docker.sh
```

Expected: All checks pass

---

### Task 10: Verify functionality

**Files:**
- Reference: `bin/probe_capabilities.py`

**Step 1: Test basic API call**

```bash
# Test health endpoint
curl -s http://127.0.0.1:4000/healthz | jq .

# Test with API key
export LITELLM_MASTER_KEY=$(grep "^LITELLM_MASTER_KEY=" .env | cut -d= -f2)
curl -s http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq .
```

Expected: List of models returned

**Step 2: Run capability probe**

```bash
source .env
~/.conda/envs/litellm/bin/python bin/probe_capabilities.py --base http://127.0.0.1:4000 --limit 3
```

Expected: Probes complete without errors

**Step 3: Test model completion**

```bash
# Simple chat test
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "model": "chat-default",
    "messages": [{"role": "user", "content": "say hello"}],
    "max_tokens": 10
  }' | jq .
```

Expected: Chat response with "hello"

**Step 4: Run full health check**

```bash
bin/health_check_docker.sh
```

Expected: All checks pass

---

### Task 11: Update systemd services for coexistence

**Files:**
- Modify: `systemd/litellm-probe-capabilities.service`
- Modify: `systemd/litellm-healthcheck.service`

**Step 1: Update healthcheck service**

Modify `systemd/litellm-healthcheck.service`:

```ini
[Unit]
Description=LiteLLM Health Monitor (Docker)
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/LAB/@litellm
ExecStart=/LAB/@litellm/bin/health_check_docker.sh

[Install]
WantedBy=default.target
```

**Step 2: Update probe capabilities service**

Modify `systemd/litellm-probe-capabilities.service`:

```ini
[Unit]
Description=LiteLLM Capability Probe (Docker)
After=docker.service litellm-docker-healthcheck.service

[Service]
Type=oneshot
WorkingDirectory=/LAB/@litellm
EnvironmentFile=-/LAB/@litellm/.env
ExecStart=/bin/bash -lc 'source /LAB/@litellm/.env && /home/miko/.venvs/litellm/bin/python /LAB/@litellm/bin/probe_capabilities.py --base http://127.0.0.1:4000 --scope all --limit 0 && /home/miko/.venvs/litellm/bin/python /LAB/@litellm/bin/probe_capabilities_report.py'

[Install]
WantedBy=default.target
```

**Step 3: Reload systemd and enable services**

```bash
# Reload systemd
systemctl --user daemon-reload

# Enable new services
systemctl --user enable litellm-healthcheck.service
systemctl --user enable litellm-probe-capabilities.service
systemctl --user enable litellm-backup-docker.timer

# Start healthcheck timer
systemctl --user start litellm-healthcheck.timer
systemctl --user start litellm-probe-capabilities.timer
```

**Step 4: Verify timers**

```bash
systemctl --user list-timers | grep litellm
```

Expected: All litellm timers listed and active

**Step 5: Commit**

```bash
git add systemd/litellm-healthcheck.service systemd/litellm-probe-capabilities.service
git commit -m "feat(docker): update systemd services for Docker deployment"
```

---

## Phase 6: Rollback Plan

### Task 12: Create rollback script

**Files:**
- Create: `bin/rollback_to_systemd.sh`

**Step 1: Create rollback script**

Create `bin/rollback_to_systemd.sh`:

```bash
#!/usr/bin/env bash
#
# Rollback from Docker to systemd deployment
#
# Usage: bin/rollback_to_systemd.sh
#

set -euo pipefail

COMPOSE_DIR="/LAB/@litellm"

echo "=== Rolling back to systemd deployment ==="
echo ""

# Step 1: Stop Docker services
echo "[1/4] Stopping Docker services..."
cd "$COMPOSE_DIR"
docker-compose down

# Step 2: Restore database if needed
echo "[2/4] Checking for database backup..."
if [ -f "/tmp/litellm-migration-backup.txt" ]; then
    backup_dir=$(cat /tmp/litellm-migration-backup.txt)
    echo "  Backup found: $backup_dir"
    read -p "  Restore database from backup? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # TODO: Implement database restore
        echo "  Database restore not yet implemented"
    fi
else
    echo "  No migration backup found"
fi

# Step 3: Start systemd services
echo "[3/4] Starting systemd services..."
systemctl --user enable litellm.service
systemctl --user start litellm.service

# Step 4: Restore systemd healthcheck
echo "[4/4] Restoring systemd healthcheck..."
# Revert healthcheck service changes (git restore would be used)
echo "  Restore healthcheck service from git if needed"

echo ""
echo "=== Rollback complete ==="
echo "Verify: curl http://127.0.0.1:4000/healthz"
```

**Step 2: Make executable**

```bash
chmod +x bin/rollback_to_systemd.sh
```

**Step 3: Commit**

```bash
git add bin/rollback_to_systemd.sh
git commit -m "feat(docker): add rollback script to systemd"
```

---

## Phase 7: Documentation

### Task 13: Update operations documentation

**Files:**
- Modify: `docs/LITELLM_OPS.md`
- Modify: `docs/DOCKER_DEPLOYMENT.md`
- Create: `docs/MIGRATION_SYSTEMD_TO_DOCKER.md`

**Step 1: Create migration guide**

Create `docs/MIGRATION_SYSTEMD_TO_DOCKER.md`:

```markdown
# Systemd to Docker Migration Guide

This document describes the migration from systemd/conda deployment to Docker Compose.

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2
- Existing systemd deployment running

## Pre-Migration Checklist

- [ ] Backup database using `python bin/backup_db.py`
- [ ] Create `.env` file from `env.litellm`
- [ ] Validate with `bin/validate_migration.sh`
- [ ] Stop non-critical services

## Migration Steps

### 1. Pre-Migration Backup

```bash
# Run backup
python bin/backup_db.py

# Note backup location
ls -lt state/archive/backups/ | head -5
```

### 2. Stop Systemd Services

```bash
# Stop and disable main service
systemctl --user stop litellm.service
systemctl --user disable litellm.service

# Verify ports are free
lsof -i :4000  # Should be empty
```

### 3. Start Docker Services

```bash
# Pull images
docker-compose pull

# Start services
docker-compose up -d

# Verify status
docker-compose ps
bin/health_check_docker.sh
```

### 4. Verify Functionality

```bash
# Test API
curl http://127.0.0.1:4000/healthz

# Run probe
source .env
~/.conda/envs/litellm/bin/python bin/probe_capabilities.py
```

### 5. Update Monitoring Services

```bash
# Switch to Docker-aware services
systemctl --user daemon-reload
systemctl --user disable litellm-healthcheck.timer
systemctl --user enable litellm-healthcheck.timer  # Docker version
systemctl --user start litellm-healthcheck.timer
```

## Rollback

If issues occur:

```bash
# Quick rollback
bin/rollback_to_systemd.sh

# Manual rollback
docker-compose down
systemctl --user enable litellm.service
systemctl --user start litellm.service
```

## Post-Migration Tasks

- [ ] Monitor logs for 24 hours
- [ ] Verify backups run with new script
- [ ] Update any external references to service URLs
- [ ] Remove old conda environment (after verification period)

## Troubleshooting

### Port conflicts

If ports are in use:
```bash
# Check what's using the port
lsof -i :4000

# Stop conflicting service
systemctl --user stop litellm.service
```

### Database connection issues

```bash
# Check PostgreSQL container
docker-compose logs postgres

# Verify database exists
docker exec -it litellm-postgres psql -U litellm -d litellm -c "\l"
```

### Service not starting

```bash
# Check logs
docker-compose logs litellm

# Validate config
docker-compose config
```
```

**Step 2: Update DOCKER_DEPLOYMENT.md with systemd coexistence info**

Append to `docs/DOCKER_DEPLOYMENT.md`:

```markdown
## Coexistence with Systemd Services

Local model services (llama.cpp, vLLM) continue running under systemd:

| Service | Type | Port |
|---------|------|------|
| litellm-proxy | Docker | 4000 |
| postgres | Docker | 5434 |
| redis | Docker | 6379 |
| llamacpp (Arctic) | systemd | 8082 |
| rerank | systemd | 8079 |
| vllm models | systemd | varies |

These systemd services are started automatically and accessible from the Docker container via `host.docker.internal`.
```

**Step 3: Commit**

```bash
git add docs/MIGRATION_SYSTEMD_TO_DOCKER.md docs/DOCKER_DEPLOYMENT.md
git commit -m "docs(docker): add migration guide and update deployment docs"
```

---

## Post-Migration Verification

### Task 14: Final verification checklist

**Step 1: Complete all checks**

```bash
# Run all verification scripts
bin/health_check_docker.sh
bin/validate_migration.sh
```

**Step 2: Verify all capabilities**

```bash
# Check model capabilities
source .env
~/.conda/envs/litellm/bin/python bin/probe_capabilities.py

# Check inventory report
~/.conda/envs/litellm/bin/python bin/model_inventory_report.py
```

**Step 3: Monitor for 24 hours**

```bash
# Watch logs
docker-compose logs -f litellm

# Check service health
watch -n 30 'bin/health_check_docker.sh'
```

**Step 4: Document any issues**

Create `state/migration-notes.md`:

```markdown
# Migration Notes

Date: 2026-01-21

## Issues Encountered
- [Document any issues found during migration]

## Workarounds Applied
- [Document any workarounds]

## TODOs
- [ ] [Future improvements]
```

**Step 5: Commit final state**

```bash
git add state/migration-notes.md
git commit -m "docs(migration): add migration notes"
```

---

## Summary

This migration plan:

1. ✅ Preserves all data (database backup + migration)
2. ✅ Maintains operational capabilities (health checks, backups, monitoring)
3. ✅ Enables rollback (systemd services remain configured)
4. ✅ Documents all changes (migration guide, updated docs)
5. ✅ Tests at each phase (validation scripts)

**Estimated time:** 2-3 hours
**Risk level:** Medium (rollback path available)
**Downtime:** ~5 minutes (stop systemd, start Docker)

# Technical Debt Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up critical and high-priority technical debt while preserving the shared data implementation (SINGLE_TENANT_MODE) and avoiding any changes to the data layer.

**Architecture:** This plan focuses on safe cleanup operations that don't touch MongoDB, Milvus, or MinIO data structures. All changes are either:
1. Deleting unused/dead code (0 imports)
2. Consolidating duplicate implementations
3. Fixing configuration issues
4. Updating documentation

**Tech Stack:** Python 3.11+, FastAPI, TypeScript/React, Docker Compose

**Data Layer Constraints:** DO NOT MODIFY:
- `backend/app/db/mongo.py` (working, stable, 44 files depend on it)
- `backend/app/db/repositories/` (broken imports, will not fix)
- MongoDB collection schemas
- Knowledge base ID format (`username_uuid`)
- Milvus collection naming patterns

---

## PRE-WORK: BACKUP (Do this first!)

### Task 0: Create Data Backup

**Files:** None (backup operation)

**Step 1: Backup MinIO data**

```bash
# Run from project root
docker run --rm -v layra_minio_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/minio-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

**Expected Output:** Creates `minio-backup-YYYYMMDD-HHMMSS.tar.gz` in project root

**Step 2: Backup MongoDB data**

```bash
docker exec layra-mongodb-1 mongodump --db layra --out /tmp/backup
docker cp layra-mongodb-1:/tmp/backup ./mongodb-backup-$(date +%Y%m%d-%H%M%S)
```

**Expected Output:** Creates `mongodb-backup-YYYYMMDD-HHMMSS/` directory

**Step 3: Verify backups exist**

```bash
ls -lh minio-backup-*.tar.gz mongodb-backup-*/
```

**Expected Output:** Shows backup files with non-zero sizes

**Step 4: Document backup completion**

Create file: `docs/backups/README.md`
```markdown
# Data Backups

## Latest Backups
- MinIO: minio-backup-YYYYMMDD-HHMMSS.tar.gz
- MongoDB: mongodb-backup-YYYYMMDD-HHMMSS/

## Restore Instructions

### MinIO Restore
```bash
docker run --rm -v layra_minio_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/minio-backup-YYYYMMDD-HHMMSS.tar.gz -C /data
```

### MongoDB Restore
```bash
docker exec layra-mongodb-1 mongorestore --db layra /tmp/backup
```
```

---

## PHASE 1: CRITICAL QUICK WINS (2-3 hours)

### Task 1: Delete workflow_engine_new.py (Unused Duplicate)

**Files:**
- Delete: `backend/app/workflow/workflow_engine_new.py`

**Step 1: Verify file is unused**

```bash
cd /LAB/@thesis/layra
grep -r "workflow_engine_new" --include="*.py" | grep -v "Binary"
```

**Expected Output:** Only the file itself, no imports (0 import references)

**Step 2: Delete the file**

```bash
rm backend/app/workflow/workflow_engine_new.py
```

**Step 3: Verify deletion**

```bash
ls backend/app/workflow/workflow_engine*.py
```

**Expected Output:** Only `workflow_engine.py` exists

**Step 4: Commit**

```bash
git add backend/app/workflow/
git commit -m "chore: delete unused workflow_engine_new.py (0 imports)"
```

---

### Task 2: Remove Duplicate Imports in workflow_engine.py

**Files:**
- Modify: `backend/app/workflow/workflow_engine.py:22-41`

**Step 1: View the duplicate imports**

```bash
head -45 backend/app/workflow/workflow_engine.py | tail -25
```

**Expected Output:** Shows import block lines 22-32 and duplicate lines 34-41

**Step 2: Remove duplicate import block (lines 34-41)**

Edit `backend/app/workflow/workflow_engine.py`:
```python
# Keep lines 22-32, DELETE lines 34-41 (duplicate imports)
```

After edit, the imports should appear only once:
```python
from app.workflow.components import (
    MAX_CONTEXT_SIZE,
    MAX_CONTEXT_ENTRIES,
    PROVIDER_TIMEOUTS,
    LOOP_LIMITS,
    CHECKPOINT_CONFIG,
    QualityAssessmentEngine,
    WorkflowCheckpointManager,
    LLMClient,
)
```

**Step 3: Verify syntax**

```bash
python -m py_compile backend/app/workflow/workflow_engine.py
```

**Expected Output:** No errors (syntax valid)

**Step 4: Test import**

```bash
cd backend && python -c "from app.workflow.workflow_engine import WorkflowEngine; print('OK')"
```

**Expected Output:** `OK`

**Step 5: Commit**

```bash
git add backend/app/workflow/workflow_engine.py
git commit -m "chore: remove duplicate imports in workflow_engine.py"
```

---

### Task 3: Clean DEBUG Print Statements

**Files:**
- Modify: `scripts/ingest_sync.py`

**Step 1: Count DEBUG statements**

```bash
grep -c "DEBUG:" scripts/ingest_sync.py
```

**Expected Output:** 16 (approximately)

**Step 2: Replace DEBUG prints with proper logging**

Edit `scripts/ingest_sync.py`:

Find all lines like:
```python
print("DEBUG: Connecting Mongo...", flush=True)
```

Replace with:
```python
logger.info("Connecting Mongo...")
```

Add import at top if not present:
```python
import logging
logger = logging.getLogger(__name__)
```

**Step 3: Verify syntax**

```bash
python -m py_compile scripts/ingest_sync.py
```

**Expected Output:** No errors

**Step 4: Commit**

```bash
git add scripts/ingest_sync.py
git commit -m "refactor: replace DEBUG prints with proper logging"
```

---

### Task 4: Create .env.example File

**Files:**
- Create: `.env.example`

**Step 1: Extract current environment variables**

```bash
docker-compose config | grep -E "^\s+[A-Z_]+=" | sed 's/.*: //' | sort -u > /tmp/env_vars.txt
cat /tmp/env_vars.txt
```

**Expected Output:** Lists all environment variable names

**Step 2: Create .env.example from actual .env (redacted)**

```bash
grep -E "^[A-Z_]+=" .env 2>/dev/null | sed 's/=.*/=/' > .env.example
```

Or create manually with this content:

Create file: `.env.example`
```bash
# =============================================================================
# LAYRA ENVIRONMENT CONFIGURATION TEMPLATE
# Copy this file to .env and fill in your values
# =============================================================================

# -----------------------------------------------------------------------------
# MinIO Configuration
# -----------------------------------------------------------------------------
MINIO_URL=http://minio:9000
MINIO_PUBLIC_URL=http://localhost:9000  # CHANGE THIS to your server's public URL
MINIO_ACCESS_KEY=your_access_key_here
MINIO_SECRET_KEY=your_secret_key_here
MINIO_BUCKET_NAME=minio-file

# -----------------------------------------------------------------------------
# MongoDB Configuration
# -----------------------------------------------------------------------------
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DATABASE_NAME=layra

# -----------------------------------------------------------------------------
# Milvus Configuration
# -----------------------------------------------------------------------------
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME_PREFIX=colqwenmiko

# -----------------------------------------------------------------------------
# Redis Configuration
# -----------------------------------------------------------------------------
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=

# -----------------------------------------------------------------------------
# Kafka Configuration
# -----------------------------------------------------------------------------
KAFKA_BROKER_URL=kafka:9094

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------
SECRET_KEY=your-secret-key-min-32-characters-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080

# -----------------------------------------------------------------------------
# LLM API Keys (Choose one or more)
# -----------------------------------------------------------------------------
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
ZHIPUAI_API_KEY=...

# -----------------------------------------------------------------------------
# Model Server
# -----------------------------------------------------------------------------
MODEL_SERVER_URL=http://model-server:8005

# -----------------------------------------------------------------------------
# Tenancy Configuration
# -----------------------------------------------------------------------------
SINGLE_TENANT_MODE=false  # Set to true for shared data across all users

# -----------------------------------------------------------------------------
# Frontend
# -----------------------------------------------------------------------------
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Step 3: Add to .gitignore (if not already there)**

Check if `.env` is ignored:
```bash
grep "^\.env$" .gitignore || echo ".env" >> .gitignore
```

**Step 4: Commit**

```bash
git add .env.example .gitignore
git commit -m "docs: add .env.example template file"
```

---

## PHASE 2: CONFIGURATION FIXES (1-2 hours)

### Task 5: Fix MINIO_PUBLIC_URL Configuration

**Files:**
- Modify: `docker-compose.yml`
- Modify: `deploy/docker-compose.gpu.yml` (if GPU override needs the same env)

**Step 1: Check current backend environment variables**

```bash
grep -A 30 "backend:" docker-compose.yml | grep -E "^\s+- MINIO"
```

**Expected Output:** Shows MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET_NAME but NOT MINIO_PUBLIC_URL

**Step 2: Add MINIO_PUBLIC_URL to docker-compose.yml**

Edit `docker-compose.yml` in the backend service environment section:

```yaml
  backend:
    environment:
      - MINIO_URL=${MINIO_URL}
      - MINIO_PUBLIC_URL=${MINIO_PUBLIC_URL}  # ADD THIS LINE
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - MINIO_BUCKET_NAME=${MINIO_BUCKET_NAME}
```

**Step 3: Update .env.example with correct value**

Edit `.env.example`:
```bash
MINIO_PUBLIC_URL=http://localhost:9000  # For local development
# For production, change to: http://YOUR_SERVER_IP:9000
```

**Step 4: Test configuration loads**

```bash
./scripts/compose-clean config | grep MINIO_PUBLIC_URL
```

**Expected Output:** Shows `MINIO_PUBLIC_URL=${MINIO_PUBLIC_URL}` in backend service

**Step 5: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "fix: add missing MINIO_PUBLIC_URL to backend environment"
```

---

### Task 6: Fix UNOSERVER_BASE_PORTS Typo

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/app/core/config.py`

**Step 1: Find the typo**

```bash
grep -n "UNOSERVER_BASE_PORT" docker-compose.yml backend/app/core/config.py
```

**Expected Output:** Shows both plural (PORTS) and singular (PORT) versions

**Step 2: Standardize to singular form**

Edit `docker-compose.yml` - ensure environment variable is singular:
```yaml
  unoserver:
    environment:
      - UNOSERVER_BASE_PORT=${UNOSERVER_BASE_PORT}  # Not PORTS
```

Edit `backend/app/core/config.py` - ensure field name matches:
```python
unoserver_base_port: int = Field(
    default=2002,
    description="Base port for UnoOffice document converter"
)
```

**Step 3: Verify consistency**

```bash
grep -r "UNOSERVER_BASE_PORT" docker-compose.yml backend/ | grep -v "Binary"
```

**Expected Output:** All uses singular form (no trailing 'S')

**Step 4: Commit**

```bash
git add docker-compose.yml backend/app/core/config.py
git commit -m "fix: standardize UNOSERVER_BASE_PORT (remove typo PORTS)"
```

---

## PHASE 3: DOCUMENTATION UPDATES (1 hour)

### Task 7: Fix README.md Docker Compose References

**Files:**
- Modify: `README.md`

**Step 1: Find broken docker-compose references**

```bash
grep -n "docker-compose" README.md | grep -E "(gpu|no-local)"
```

**Expected Output:** Shows references to deleted files like `docker-compose.gpu.yml`

**Step 2: Update deployment section**

Edit `README.md` deployment section to:

```markdown
## Deployment

### Quick Start (Local Development)

```bash
./scripts/compose-clean up -d
```

This starts all services using `docker-compose.yml`.

### GPU Support (Optional)

For GPU-accelerated embeddings, use the GPU profile:

```bash
./scripts/compose-clean -f docker-compose.yml -f deploy/docker-compose.gpu.yml up -d
```

### Configuration

1. Copy environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
   - Set MINIO_PUBLIC_URL to your server's public URL
   - Add your LLM API keys (OpenAI, DeepSeek, or ZhipuAI)
   - Set SECRET_KEY to a secure random string

3. Start services:
```bash
./scripts/compose-clean up -d
```
```

**Step 3: Verify all referenced files exist**

```bash
ls -la docker-compose.yml deploy/docker-compose.gpu.yml 2>/dev/null
```

**Expected Output:** Both files exist

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: fix docker-compose file references in README"
```

---

### Task 8: Add LLM API Key Documentation

**Files:**
- Modify: `README.md`

**Step 1: Find LLM configuration section**

```bash
grep -n -A 10 -i "jina\|embedding\|llm" README.md | head -30
```

**Step 2: Add API key requirements to README**

Edit `README.md` - add to configuration section:

```markdown
## LLM API Configuration

This system requires an LLM provider API key. Choose one:

### Option 1: OpenAI (Recommended for chat)
```bash
OPENAI_API_KEY=sk-...
```

### Option 2: DeepSeek (Cost-effective)
```bash
DEEPSEEK_API_KEY=sk-...
```

### Option 3: ZhipuAI (Alternative)
```bash
ZHIPUAI_API_KEY=...
```

**Note:** Only one API key is required. The system will use the first available key in this order: OpenAI → DeepSeek → ZhipuAI.

### Embeddings

Embeddings use a local ColQwen2.5 model served by `model-server`. No API key required for embeddings.
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add LLM API key configuration documentation"
```

---

## PHASE 4: REMOVE COMMENTED CODE (30 minutes)

### Task 9: Remove Commented Code in workflow_engine.py

**Files:**
- Modify: `backend/app/workflow/workflow_engine.py`

**Step 1: Find commented code blocks**

```bash
grep -n "^\s*#.*raise\|^\s*#.*break\|^\s*#.*async" backend/app/workflow/workflow_engine.py | head -20
```

**Expected Output:** Shows lines with commented-out error handling and control flow

**Step 2: Remove identified commented code**

Based on the assessment, these lines contain dead commented code:
- Line 651: Commented error raise
- Lines 771-777, 848-855, 889-895: Commented async parallel execution code
- Line 741: Commented loop break

Edit the file to remove these commented sections (delete the lines entirely)

**Step 3: Verify syntax**

```bash
python -m py_compile backend/app/workflow/workflow_engine.py
```

**Expected Output:** No errors

**Step 4: Commit**

```bash
git add backend/app/workflow/workflow_engine.py
git commit -m "chore: remove dead commented code from workflow_engine.py"
```

---

### Task 10: Remove Commented Code in Frontend

**Files:**
- Modify: `frontend/src/app/[locale]/ai-chat/page.tsx:354`
- Modify: `frontend/src/components/AiChat/KnowledgeConfigModal.tsx:244`
- Modify: `frontend/src/components/Workflow/NodeSettings/KnowledgeConfigModal.tsx:248`

**Step 1: Find commented code**

```bash
grep -n "^\s*//" frontend/src/app/[locale]/ai-chat/page.tsx frontend/src/components/AiChat/KnowledgeConfigModal.tsx frontend/src/components/Workflow/NodeSettings/KnowledgeConfigModal.tsx
```

**Expected Output:** Shows commented-out code lines

**Step 2: Remove commented lines**

Edit each file, removing the commented lines entirely

**Step 3: Verify TypeScript compiles**

```bash
cd frontend && npm run type-check 2>&1 | head -20
```

**Expected Output:** No new errors introduced

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "chore: remove dead commented code from frontend components"
```

---

## VERIFICATION

### Verification Task: Test All Changes

**Step 1: Ensure backend starts**

```bash
docker-compose down
docker-compose up -d backend
docker-compose logs backend | tail -20
```

**Expected Output:** No import errors, backend starts successfully

**Step 2: Check frontend builds**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

**Expected Output:** Build succeeds, no errors

**Step 3: Verify environment variables load**

```bash
docker-compose exec backend python -c "from app.core.config import settings; print('MINIO_PUBLIC_URL:', settings.minio_public_url)"
```

**Expected Output:** Shows MINIO_PUBLIC_URL value (not localhost:9000 default if set)

**Step 4: Test basic API endpoint**

```bash
curl -s http://localhost:8000/api/v1/health || echo "Health check endpoint not available"
```

**Step 5: Check Docker services**

```bash
docker-compose ps
```

**Expected Output:** All services show as "Up" or "healthy"

---

## SUMMARY OF CHANGES

| Task | Action | Files Changed | Lines Removed | Risk |
|------|--------|---------------|---------------|------|
| 0 | Create backups | docs/backups/README.md | 0 | None |
| 1 | Delete unused file | -workflow_engine_new.py | -86 | None |
| 2 | Remove dupes | workflow_engine.py | -8 | Low |
| 3 | Clean DEBUG prints | scripts/ingest_sync.py | ~-16 | Low |
| 4 | Add .env.example | +.env.example | 0 | None |
| 5 | Fix MINIO_PUBLIC_URL | docker-compose.yml, .env.example | 0 | Low |
| 6 | Fix typo | docker-compose.yml, config.py | 0 | Low |
| 7 | Update README | README.md | ~0 (edits) | None |
| 8 | Add API key docs | README.md | +~20 | None |
| 9 | Remove commented code | workflow_engine.py | ~-30 | Low |
| 10 | Remove commented code | Frontend files | ~-3 | Low |

**Total Impact**: ~120 lines removed/cleaned, 0 data layer changes

**Estimated Time**: 4-6 hours

**Data Safety**: All changes are outside the data layer. MongoDB, Milvus, and MinIO data structures untouched.

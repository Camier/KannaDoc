# Layra Troubleshooting Guide

**Last Updated:** 2026-01-26
**Version:** 2.0.0

> Quick reference for diagnosing and resolving common Layra issues.

---

## Quick Reference: Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Login 404 | Nginx double-prefix routing | Remove rewrite rule in nginx.conf |
| Auth 500 | Corrupted password hash | Re-generate using app Python environment |
| Empty KB list | Missing `last_modify_at` field | Run MongoDB update to backfill |
| MinIO URL fails | Server IP instead of MinIO endpoint | Use `minio_public_url` (split-horizon) |
| Model server crash | GPU OOM (resolution too high) | Reduce `shortest_edge` to 768 |
| Duplicate KB entries | No idempotency controls | Use Redis-based duplicate detection |

---

## Current System Status

**Status:** ✅ **Fully Operational**

**Deployment:**
- URL: `http://localhost:8090`
- User: `thesis`
- Knowledge Base: "Thesis Corpus"
- Documents: 129 files
- Vectors: ~3.5 Million (768D, ColQwen 2.5)

**Recent Fixes (2026-01-25):**
- Fixed Nginx double-prefix routing (`404` → `200`)
- Repaired corrupted password hash for thesis user
- Executed full atomic re-ingestion via `ingest_sync.py`
- Implemented MinIO split-horizon networking (`minio_public_url`)
- Added idempotency controls to prevent duplicate ingestion

---

## Incident Reports

### 2026-01-25: Knowledge Base Corruption

**Status:** ✅ **RESOLVED**

**Problem:**
- 114 duplicate file entries in MongoDB
- Empty KB list in frontend (missing `last_modify_at` field)
- MongoDB/Milvus desynchronization

**Root Cause:**
Multiple failed ingestion retries without idempotency controls. Each retry appended duplicate entries instead of checking for existing files.

**Timeline:**
1. **Jan 21-22:** Initial ingestion - only 19/129 completed, 110 stuck
2. **AI Agent #1:** Created `reingest_corpus.py` without idempotency checks
3. **Duplication Cascade:** 114 duplicate entries created across 129 documents
4. **Frontend Bug:** Manual sync script omitted `last_modify_at` → 500 error
5. **Jan 23-25:** Full atomic re-ingestion via `ingest_sync.py`

**Resolution:**
```python
# Wiped and rebuilt atomically
db.knowledge_bases.delete_many({})
db.files.delete_many({})
milvus_client.drop_collection(...)
# Re-created collection, re-uploaded PDFs, re-embedded, synced metadata
```

**Preventive Measures Added:**
- Redis-based idempotency keys (24h TTL)
- Metadata validation enforcing `last_modify_at`
- Atomic operations pattern in `ingest_sync.py`
- Kafka Dead Letter Queue for failed tasks

---

### 2026-01-24: Model Server OOM & Network Issues

**Status:** ✅ **RESOLVED**

**Problems:**
1. `layra-model-server` crash loop (GPU OOM)
2. Intermittent connectivity to LiteLLM proxy
3. Workflow DNS resolution failures

**Resolution 1 - GPU OOM:**
```python
# model-server/colbert_service.py
# Old (required >15GB VRAM):
size={"shortest_edge": 56 * 56, "longest_edge": 28 * 28 * 768}
# New (Conservative, ~3GB VRAM):
size={"shortest_edge": 768, "longest_edge": 1536}
```

**Resolution 2 - Network:**
- Identified Docker network isolation between services
- Note: LiteLLM proxy now removed in v2.0.0 (direct provider integration)

---

## Known Issues & Fixes

### Fix 1: MinIO Presigned URLs (Split-Horizon)

**File:** `backend/app/db/miniodb.py`

**Problem:**
```python
# WRONG - uses app server IP instead of MinIO endpoint
async def create_presigned_url(self, file_name: str, expires: int = 3153600000):
    async with self.session.client(
        "s3",
        endpoint_url=settings.server_ip,  # ❌
        ...
    ) as client:
```

**Solution:**
```python
# CORRECT
endpoint_url=settings.minio_public_url,  # ✅
```

**Status:** ✅ Fixed in v2.0.0

---

### Fix 2: SQLAlchemy Logging in Production

**File:** `backend/app/db/mysql_session.py`

**Problem:**
```python
# WRONG - logs ALL SQL queries to stdout
engine = create_async_engine(
    settings.db_url,
    echo=True,  # ❌ Security risk, performance hit
)
```

**Solution:**
```python
# CORRECT - conditional on debug mode
echo=settings.debug_mode,  # ✅
```

**Status:** ✅ Fixed in v2.0.0

---

### Fix 3: Nginx Double-Prefix Routing

**File:** `frontend/nginx.conf`

**Problem:**
```
# Frontend sends: /api/v1/auth/login
# Nginx rewrites: /api/v1/v1/auth/login
# Result: 404
```

**Solution:**
Remove the rewrite rule. Nginx now proxies `/api/` directly to backend.

**Status:** ✅ Fixed in v2.0.0

---

### Fix 4: Missing KB Metadata Field

**File:** MongoDB `knowledge_bases` collection

**Problem:**
```python
# Manual sync script omitted required field
kb_document = {
    "knowledge_base_id": kb_id,
    "username": username,
    # Missing: "last_modify_at"
}
# Backend endpoint throws KeyError → 500 error
```

**Solution:**
```python
kb_document = {
    "knowledge_base_id": kb_id,
    "username": username,
    "last_modify_at": datetime.utcnow(),  # ✅ Required
    ...
}
```

**Status:** ✅ Fixed in v2.0.0

---

### Fix 5: Password Hash Corruption

**File:** Database User Record

**Problem:**
```bash
# Shell variable expansion corrupts bcrypt hash
docker exec layra-mongodb mongosh ...
# $2b$12$... → expands to "b12$..." → Invalid hash
```

**Solution:**
```python
# Use app Python environment to generate hash
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash = pwd_context.hash("thesis_deploy_b20f1508a2a983f6")
# Update with single-quoted SQL to prevent expansion
```

**Status:** ✅ Fixed in v2.0.0

---

### Fix 6: Empty Chat / Z.ai Key Mismatch

**Symptoms:**
- Chat interface returns empty responses immediately
- Backend logs show `ZhipuAI API key format` errors

**Problem:**
Using a Z.ai API key (no dots) with the ZhipuAI provider (expects `id.secret` format), or vice versa.
This happens when `ZAI_API_KEY` is not set, causing auto-detection to fallback to `zhipu-coding`.

**Solution:**
1. Ensure `ZAI_API_KEY` is set in `.env` for Z.ai models (`glm-4.7`, etc.)
2. Use `ZHIPUAI_API_KEY` only for ZhipuAI models (`glm-4-plus`, etc.)
3. Restart backend to pick up new variables

**Status:** ✅ Fixed in v2.1.1 (Auto-detection + Safety Checks)

---

## Health Check Procedures

Run these checks after system restart or major changes:

### A. MongoDB Duplicate Check
```bash
docker exec layra-mongodb mongosh -u root -p <password> --eval '
  use chat_mongodb;
  db.knowledge_bases.aggregate([
    {$unwind: "$files"},
    {$group: {_id: {kb_id: "$knowledge_base_id", file_id: "$files.file_id"}, count: {$sum: 1}}},
    {$match: {count: {$gt: 1}}}
  ]);
'
# Expected: Empty array (0 duplicates)
```

### B. Metadata Field Validation
```bash
docker exec layra-mongodb mongosh -u root -p <password> --eval '
  use chat_mongodb;
  db.knowledge_bases.find({last_modify_at: {$exists: false}}).count();
'
# Expected: 0
```

### C. MongoDB/Milvus Sync Check
```python
mongo_count = await mongo.files.count_documents({"knowledge_db_id": kb_id})
milvus_stats = milvus_client.get_collection_stats(collection_name)
assert mongo_count == 129
assert milvus_stats["row_count"] > 3_000_000
```

### D. Frontend Access Test
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8090/api/v1/knowledge_bases
# Should return array with "Thesis Corpus"
```

### E. Idempotency Verification
```bash
# Check Redis keys exist during ingestion
docker exec layra-redis redis-cli -a <password> KEYS "ingestion:*"
```

---

## Code Quality Fixes (Pending)

### Priority 2: High
| Issue | File | Action |
|-------|------|--------|
| Unused APIKeyHeader import | `backend/app/core/security.py` | Remove import |
| Unused dependency | `backend/requirements.txt` | Remove `databases[mysql]` |
| Inconsistent response models | `backend/app/api/endpoints/chat.py` | Use Pydantic models |

### Priority 3: Medium
| Issue | File | Action |
|-------|------|--------|
| Silent exception handlers | Multiple files | Add `logger.error()` |
| No response model schemas | `backend/app/api/endpoints/` | Create `schemas/` |

---

## Recovery Tools

### Atomic Re-Ingestion
```bash
python scripts/ingest_sync.py
```
Wipes MongoDB/Milvus and re-ingests entire corpus atomically.

### Duplicate Detection
```python
# backend/app/api/endpoints/chat.py
duplicate_key = f"ingestion:{file_id}"
if await redis_client.exists(duplicate_key):
    return {"status": "already_processing"}
```

### MongoDB Inspection
```bash
python scripts/inspect_milvus.py
python scripts/inspect_data.py
```

---

## Related Documentation

- **Operations:** [operations/RUNBOOK.md](RUNBOOK.md) - Restart procedures
- **Configuration:** [core/CONFIGURATION.md](../core/CONFIGURATION.md) - Environment variables
- **Architecture:** [architecture/DEEP_ANALYSIS.md](../architecture/DEEP_ANALYSIS.md) - System design
- **Changelog:** [operations/CHANGE_LOG.md](CHANGE_LOG.md) - Version history

---

**Document Status:** ✅ Active
**Last Review:** 2026-01-26
**Next Review:** 2026-02-02

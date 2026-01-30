# Session Handoff - 2026-01-30

## Project
- **Repo:** `/LAB/@thesis/layra`
- **Remote:** `https://github.com/liweiphys/layra.git`
- **Branch:** `main`
- **Status:** 67+ commits ahead of origin/main (push pending - auth issue)

---

## What Was Completed

### 1. KB Consolidation (Major)

**Problem:** Multiple duplicate KBs with data quality issues
- `thesis_fbd5d3a6...` — 4.3M vectors, 396 file docs (3x duplicated), schema drift
- `miko_e6643365...` — 3.56M vectors, 129 file docs, clean metadata

**Solution:** Consolidated to single canonical KB

| Action | Result |
|--------|--------|
| Soft deleted thesis_fbd KB | `is_delete: true` |
| Hard deleted thesis_fbd KB | MongoDB KB + 396 file docs removed |
| Dropped thesis Milvus collection | 4.3M vectors removed |
| Dropped empty miko_0ecb collection | Smoke test artifact |
| Deleted MinIO thesis/ prefix | 129 duplicate PDFs removed |
| Preserved shared images | 5,732 images kept |
| Verified RAG pipeline | embed: 0.64s, search: 7.4s, LLM: 200 OK |

**Current State:**
- **1 Milvus collection:** `colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653` (3.56M vectors)
- **1 Active KB:** `miko_e6643365-8b03_4bea-a69b_7a1df00ec653` (129 files)
- **MinIO:** 5,862 objects (129 PDFs + 5,733 images)

### 2. Bug Fixes (Previous Session)

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Zhipu GLM-4.7 API Error 1210 | Wrong endpoint stored in MongoDB | Updated `model_config` to use `/api/coding/paas/v4` |
| Zhipu stream_options error | API doesn't support `stream_options` | Conditional skip in `chat_service.py:456-464` |
| Milvus HNSW ef>=k error | `ef(100) should be larger than k(200)` | Dynamic `ef_value = max(search_limit, rag_ef_min)` in `milvus.py:187` |

### 3. RAG Pipeline Optimization

**New Settings (env-configurable):**
```python
rag_max_query_vecs: int = 48        # Max query vectors to Milvus
rag_search_limit_cap: int = 120     # Max ANN limit per vector
rag_candidate_images_cap: int = 120 # Max candidates for rerank
rag_search_limit_min: int = 50      # Min ANN limit per vector
rag_ef_min: int = 100               # Min HNSW ef param
rag_load_collection_once: bool = True
```

### 4. Documentation Updated

| File | Changes |
|------|---------|
| `docs/operations/RUNBOOK.md` | Updated KB state, consolidation history |
| `docs/SSOT_CLEAN.md` | Full rewrite with consolidated data |
| `docs/ssot/stack.md` | Version 3.3.0, removed Qdrant, KB notes |
| `docs/reports/2026-01-25-kb-corruption.md` | Updated current state |

---

## Current State

### Services
```
layra-backend: Up (healthy)
layra-milvus-standalone: Up (healthy)
layra-minio: Up (healthy)
+ 15 other services running
```

### Milvus Collections (Consolidated)
| Collection | Vectors | Status |
|------------|---------|--------|
| colqwenmiko_e6643365... | 3,562,057 | ACTIVE |

### MongoDB Knowledge Bases
| KB ID | Files | Status |
|-------|-------|--------|
| miko_e6643365... | 129 | ACTIVE |
| miko_0ecb4105... | 0 | Empty (smoke test) |

### User Credentials
- **thesis** / `thesis123` (password reset this session)

---

## Pending Tasks

### Immediate
1. **Push to origin** - Requires fixing GitHub auth
2. **Test hybrid search** - `sparse_vector` field exists but unused

### Future Enhancements
1. **Hybrid Search** - Enable dense+sparse retrieval
2. **Multi-modal Queries** - Support image+text queries
3. **Monitoring** - Grafana dashboards for RAG metrics

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/operations/RUNBOOK.md` | KB state, verification commands |
| `docs/SSOT_CLEAN.md` | Data inventory, consistency checks |
| `docs/ssot/stack.md` | Full system architecture |
| `backend/app/core/config.py` | RAG tuning knobs (lines 110-115) |
| `backend/app/db/milvus.py` | Milvus search with caps + cache |

---

## Quick Commands

```bash
# Check Milvus collections
docker exec layra-backend python3 -c "
from pymilvus import MilvusClient
c = MilvusClient('http://milvus-standalone:19530')
for col in c.list_collections():
    print(f'{col}: {c.get_collection_stats(col)}')"

# Check MongoDB KBs
docker exec layra-mongodb mongosh 'mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@localhost:27017/chat_mongodb?authSource=admin' --quiet --eval '
db.knowledge_bases.find({}, {knowledge_base_id:1, is_delete:1}).forEach(printjson)'

# Check RAG latency
docker logs layra-backend 2>&1 | grep "RAG timings" | tail -5

# Verify backend health
curl http://localhost:8090/api/v1/health/check

# Test RAG (requires auth)
# Login: POST /api/v1/auth/login with thesis/thesis123
# Then use token for /api/v1/sse/chat
```

---

## Continuation Prompt

```
Continue LAYRA session from 2026-01-30.

## Context
- Project: /LAB/@thesis/layra
- Branch: main, 67+ commits ahead of origin/main
- Backend: Running and healthy

## Completed This Session
1. KB Consolidation: Single active KB (miko_e6643365...)
2. Deleted legacy thesis_fbd KB (4.3M vectors, 396 files)
3. Deleted duplicate MinIO objects (129 PDFs)
4. Updated all documentation
5. Verified RAG pipeline working

## Current Data State
- Milvus: 1 collection, 3.56M vectors
- MongoDB: 1 active KB, 129 files
- MinIO: 5,862 objects (PDFs + images)
- thesis user: password is thesis123

## Key Files
- docs/operations/RUNBOOK.md (KB state)
- docs/SSOT_CLEAN.md (data inventory)
- docs/ssot/stack.md (architecture v3.3.0)

## Next Steps
1. Push commits (fix auth: Camier vs liweiphys)
2. Optional: Enable hybrid dense+sparse search
3. Optional: Add monitoring dashboards
```

---

**Session Date:** 2026-01-30
**Duration:** ~1 hour (consolidation session)
**Agent:** Sisyphus (antigravity-claude-opus-4-5-thinking)

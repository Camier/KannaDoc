# Session Handoff - 2026-01-30

## Project
- **Repo:** `/LAB/@thesis/layra`
- **Remote:** `https://github.com/liweiphys/layra.git`
- **Branch:** `main`
- **Status:** 67 commits ahead of origin/main (push pending - auth issue)

---

## What Was Completed

### 1. Bug Fixes

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Zhipu GLM-4.7 API Error 1210 | Wrong endpoint stored in MongoDB | Updated `model_config` to use `/api/coding/paas/v4` |
| Zhipu stream_options error | API doesn't support `stream_options` | Conditional skip in `chat_service.py:456-464` |
| Milvus HNSW ef>=k error | `ef(100) should be larger than k(200)` | Dynamic `ef_value = max(search_limit, rag_ef_min)` in `milvus.py:187` |

### 2. RAG Pipeline Optimization

**Files Modified:**
- `backend/app/core/config.py` - Added 6 RAG tuning knobs
- `backend/app/core/embeddings.py` - Added `downsample_multivector()` helper
- `backend/app/core/llm/chat_service.py` - Applied downsampling + extended logging
- `backend/app/db/milvus.py` - Settings caps + load_collection cache

**New Settings (env-configurable):**
```python
rag_max_query_vecs: int = 48        # Max query vectors to Milvus
rag_search_limit_cap: int = 120     # Max ANN limit per vector
rag_candidate_images_cap: int = 120 # Max candidates for rerank
rag_search_limit_min: int = 50      # Min ANN limit per vector
rag_ef_min: int = 100               # Min HNSW ef param
rag_load_collection_once: bool = True
```

**Expected Impact:**
- Before: `search_s ~12-15s` with 100+ query vectors
- After: Significant reduction with capped vectors/limits

### 3. Docker Build Optimization

| Issue | Fix |
|-------|-----|
| Build took 5+ minutes, timed out | Deleted 7.9GB `backend/embeddings_output/` (debug artifacts) |
| Large context copied to Docker | Created `backend/.dockerignore` to exclude large dirs |
| Build now completes in ~30s | ✅ |

### 4. Workspace Cleanup

**Gitignored:**
- `.sisyphus/`, `.opencode/` (agent workspaces)
- `model_weights/`, `embeddings_output/`, `tmp/`
- `test_*.py`, `verify_*.py`
- `pyrightconfig.json`

**Removed from repo:**
- 127 tracked `embeddings_output/*.json` files (were accidentally committed)
- Old `.sisyphus/` tracked files

---

## Current State

### Services
```
layra-backend: Up (healthy)
layra-milvus-standalone: Up (healthy)
layra-minio: Up (healthy)
+ 12 other services running
```

### Milvus Collections (Intact)
| Collection | Vectors |
|------------|---------|
| colqwenthesis_* | 4,304,352 |
| colqwenmiko_* | 3,562,057 |

### Commits (Unpushed)
```
dd88f9a chore: add RAG env vars to compose, add backend .dockerignore
7724d76 chore: update gitignore for agent workspaces and temp files
9129161 perf(backend): optimize RAG retrieval latency
+ 64 earlier commits
```

---

## Pending Tasks

### Immediate
1. **Push to origin** - Requires fixing GitHub auth (currently authenticated as `Camier`, remote is `liweiphys/layra`)
2. **Verify RAG latency** - Send test query, check `docker logs layra-backend | grep "RAG timings"`

### Future Enhancements
1. **Hybrid Search** - Enable dense+sparse retrieval (`sparse_vector` field exists but unused)
2. **Multi-modal Queries** - Support image+text queries (embed_image infrastructure exists)
3. **Monitoring** - Grafana dashboards for RAG metrics

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | RAG tuning knobs (lines 110-115) |
| `backend/app/core/embeddings.py` | `downsample_multivector()` helper |
| `backend/app/core/llm/chat_service.py` | Query downsampling applied |
| `backend/app/db/milvus.py` | Milvus search with caps + cache |
| `docker-compose.yml` | RAG env vars (lines 311-317) |
| `backend/.dockerignore` | Excludes large dirs from build |

---

## Quick Commands

```bash
# Check RAG latency after query
docker logs layra-backend 2>&1 | grep "RAG timings" | tail -5

# Verify backend health
curl http://localhost:8090/api/v1/health/check

# Check Milvus collections
docker exec layra-backend python3 -c "
from pymilvus import MilvusClient
c = MilvusClient('http://milvus-standalone:19530')
for col in c.list_collections():
    print(f'{col}: {c.get_collection_stats(col)}')"

# Rebuild backend (fast now)
./scripts/compose-clean build backend && ./scripts/compose-clean up -d backend

# Git status
git log --oneline origin/main..HEAD | wc -l  # 67 commits ahead
git status --short  # should be clean
```

---

## Continuation Prompt

```
Continue LAYRA session from 2026-01-30.

## Context
- Project: /LAB/@thesis/layra
- Branch: main, 67 commits ahead of origin/main
- Backend: Running and healthy with RAG optimizations

## Completed This Session
1. Fixed Zhipu GLM-4.7 endpoint + stream_options
2. Fixed Milvus HNSW ef>=k error
3. Implemented RAG latency optimization (query downsampling, caps)
4. Cleaned 7.9GB debug artifacts, added .dockerignore
5. Updated docs/ssot/QUICK_REF.md with RAG troubleshooting

## Uncommitted Work
None - working tree clean

## Key Files
- backend/app/core/config.py (RAG knobs lines 110-115)
- backend/app/db/milvus.py (search caps + cache)
- docker-compose.yml (RAG env vars lines 311-317)

## Next Steps
1. Push 67 commits (fix auth: Camier vs liweiphys)
2. Verify RAG latency with test query
3. Optional: Enable hybrid dense+sparse search
```

---

**Session Date:** 2026-01-30  
**Duration:** ~2 hours  
**Agent:** Sisyphus (antigravity-claude-opus-4-5-thinking)

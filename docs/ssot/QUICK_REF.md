# LAYRA Quick Reference Card

> **One-page reference for common tasks**
> **Version:** 2.3.0
> **Last Updated:** 2026-01-30

---

## 🚀 Access

**URL:** http://localhost:8090  
**User:** `<username>`  
**Password:** `<password>`  
**API Key:** `<api_key>`

---

## 🐳 Docker Commands

### Start System
```bash
cd /LAB/@thesis/layra
./scripts/compose-clean up -d --build
```

### Stop System
```bash
./scripts/compose-clean down
```

### View Logs
```bash
docker logs layra-backend --tail 50 -f
docker logs layra-milvus-standalone --tail 50
```

### Container Status
```bash
docker ps --filter "name=layra" --format "table {{.Names}}\t{{.Status}}"
```

### Health Check
```bash
curl http://localhost:8090/api/v1/health/check
```

---

## 🗄️ Services

| Service | Port | Purpose |
|---------|------|---------|
| **Nginx** | 8090 | Web access |
| **Backend** | 8000 (internal) | API |
| **Frontend** | 3000 (internal) | UI |
| **MySQL** | 3306 (internal) | Auth DB |
| **MongoDB** | 27017 (internal) | Chat DB |
| **Redis** | 6379 (internal) | Cache |
| **Kafka** | 9094 (internal) | Queue |
| **MinIO** | 9000 (internal) | Files |
| **Milvus** | 19530 (internal) | Vectors |

**Total:** 18 services (base compose) + optional dev-only tools via `docker-compose.override.yml`

---

## 🔑 Environment Variables

**Critical Settings (`.env`):**

```bash
# Server
SERVER_IP=http://localhost:8090

# LLM Providers
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=your-zai-api-key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini

# Database
DB_URL=mysql+asyncmy://<db_user>:<db_password>@mysql:3306/layra_db
MONGODB_URL=mongodb:27017
MONGODB_DB=chat_mongodb  # Model config database
REDIS_URL=redis:6379

# Storage
MINIO_URL=http://minio:9000
MILVUS_URI=http://milvus-standalone:19530

# Messaging
KAFKA_BROKER_URL=kafka:9094
```

---

## 🤖 LLM Providers

| Provider | Models | Endpoint | Notes |
|----------|--------|----------|-------|
| DeepSeek | deepseek-chat, deepseek-r1 | https://api.deepseek.com | Working |
| Z.ai | glm-4.5, glm-4.6, glm-4.7 | https://api.z.ai/api/paas/v4 | GLM provider SSOT |
| OpenAI | gpt-4o, gpt-4o-mini | https://api.openai.com | Default |

**Provider Auto-Detection:**
- `glm-*` → Z.ai
- `deepseek-*` → DeepSeek
- `gpt-*` → OpenAI

---

## 🛠️ Common Tasks

### Re-ingest Documents
```bash
docker exec -it layra-backend python3 scripts/ingest_sync.py
```

### Create User
```bash
docker exec -it layra-backend python3 scripts/change_credentials.py
```

### Database Migration
```bash
docker exec -it layra-backend alembic upgrade head
```

### Clean Milvus (Reset Vectors)
```bash
./scripts/compose-clean down
docker volume rm layra_milvus_data layra_milvus_etcd
docker volume create layra_milvus_data
docker volume create layra_milvus_etcd
./scripts/compose-clean up -d
```

### View Backend Config
```bash
docker exec layra-backend env | grep -E "DB_|REDIS_|MONGO|MINIO|KAFKA|MILVUS"
```

---

## 💻 Frontend Development

### Rebuild Frontend After Changes
```bash
# Quick rebuild (uses Docker cache)
./scripts/compose-clean up -d --build frontend && ./scripts/compose-clean restart nginx

# Full rebuild (no cache - use when changes don't appear)
./scripts/compose-clean build --no-cache frontend && ./scripts/compose-clean up -d frontend && ./scripts/compose-clean restart nginx
```

### Dark Mode
- Config: `frontend/tailwind.config.ts` → `darkMode: "class"`
- Activation: `frontend/src/app/[locale]/layout.tsx` → `<html className="dark">`
- See: `docs/FRONTEND_THEMING.md` for patterns

### Key Directories
| Path | Purpose |
|------|---------|
| `frontend/src/app/[locale]/` | Page routes |
| `frontend/src/components/` | React components |
| `frontend/src/stores/` | Zustand state stores |
| `frontend/tailwind.config.ts` | Tailwind config |

### Troubleshooting
- **Changes not visible**: Use `--no-cache` build, then Ctrl+Shift+R
- **Style issues**: Check for missing `dark:` variants
- **Build fails**: Check `./scripts/compose-clean logs frontend`

---

## 📊 Resource Usage

| Component | RAM | Notes |
|-----------|-----|-------|
| Backend | 834MB | Main app |
| MySQL | 459MB | Database |
| Kafka | 339MB | Queue |
| Milvus | 139MB | Vectors |
| Others | ~500MB | Combined |
| **Total** | **~2.3GB** | Idle state |

---

## 🐛 Quick Fixes

### Milvus Won't Start
**Symptom:** `panic: dirty recovery info`
```bash
./scripts/compose-clean down
docker volume rm layra_milvus_data layra_milvus_etcd
docker volume create layra_milvus_data layra_milvus_etcd
./scripts/compose-clean up -d
```

### Backend Connection Error
```bash
# Check backend logs
docker logs layra-backend --tail 50

# Restart backend
docker restart layra-backend
```

### API 502 / Can't Login
**Symptom:** Frontend loads, but `/api/*` returns 502 (login fails) even though backend is healthy.

**Cause:** Nginx can cache upstream container IPs; after `backend` restarts, the old IP may be stale.

```bash
# Verify backend health
curl -i http://localhost:8090/api/v1/health/check

# Restart nginx (forces upstream refresh)
./scripts/compose-clean restart nginx
```

**Config:** `frontend/nginx.conf` uses Docker DNS (`resolver 127.0.0.11`) and variable-based `proxy_pass` to re-resolve upstreams.

### RAG Retrieval Returns 0 Hits
**Symptom:** Queries embed successfully, but retrieval returns 0 hits and backend logs show Milvus errors.

**Common Milvus errors:**
- `multiple anns_fields exist` (collection has multiple vector fields)
- `invalid max query result window` (offset + limit > 16384)

**Fix references:**
- `backend/app/db/milvus.py` uses `anns_field="vector"` for search.
- `backend/app/db/milvus.py` uses `query_iterator` (avoid offset window limits).

### Frontend Not Loading
```bash
# Check nginx
docker logs layra-nginx

# Check frontend build
docker logs layra-frontend
```

### Models Not Appearing in Dropdown
```bash
# Check MongoDB model_config schema
docker exec layra-mongodb mongosh \
  "mongodb://<user>:<password>@localhost:27017/chat_mongodb?authSource=admin" \
  --eval "db.model_config.findOne({username: 'your_username'})"
```

### RAG Search Too Slow (>10s)
**Symptom:** `search_s` in logs shows 10-15+ seconds.

**Cause:** Too many query vectors sent to Milvus ANN search.

**Fix:** Tune RAG parameters in `.env` or docker-compose:
```bash
RAG_MAX_QUERY_VECS=48        # Max query vectors (default: 48)
RAG_SEARCH_LIMIT_CAP=120     # Max ANN results per vector (default: 120)
RAG_CANDIDATE_IMAGES_CAP=120 # Max candidates for rerank (default: 120)
RAG_EF_MIN=100               # Min HNSW ef param (default: 100)
```

**Verify:** Check logs after query:
```bash
docker logs layra-backend 2>&1 | grep "RAG timings" | tail -5
# Look for: nq_before=X nq_after=48 search_s=<should be lower>
```

### Milvus HNSW ef Error
**Symptom:** `ef(100) should be larger than k(200)`

**Cause:** HNSW search param `ef` must be >= `limit` (k).

**Fix:** Already handled in code - `ef_value = max(search_limit, settings.rag_ef_min)`.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[ssot/stack.md](stack.md)** | ⭐ **Primary Reference** |
| **[START_HERE.md](../getting-started/START_HERE.md)** | Quick onboarding |
| **[QUICKSTART.md](../getting-started/QUICKSTART.md)** | Deployment guide |
| **[ANTI_COMPLEXITY.md](../ANTI_COMPLEXITY.md)** | Complexity prevention |
| **[CHANGES_20260125.md](../CHANGES_20260125.md)** | v2.0.0 changelog |

---

## 🔍 System Info

**Version:** 2.2.0
**Mode:** Standard (single-tenant optional)
**Services:** 18
**Networks:** 1 (layra-net)
**LLM:** Direct provider APIs (OpenAI, DeepSeek, Zhipu, Zhipu Coding)
**Embedding:** Local ColQwen or Jina (no-GPU)

---

## 📞 Emergency

**System broken?**
1. Check logs: `docker logs layra-backend --tail 100`
2. Check health: `curl localhost:8090/api/v1/health/check`
3. Full restart: `./scripts/compose-clean down && ./scripts/compose-clean up -d`
4. Consult: [CONSOLIDATED_REPORT.md](../CONSOLIDATED_REPORT.md)

**Data lost?**
- Volumes persist through restarts
- Check: `docker volume ls | grep layra`
- Backup `.env` and MySQL/MinIO volumes

---

**Last Updated:** 2026-01-30  
**For detailed info:** See [stack.md](stack.md)

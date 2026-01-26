# Repo Map (LAYRA)

Scope: Repository map for `/LAB/@thesis/layra`, excluding `driftedlayra/`.
Note: `.env` exists but was **not** read (secrets safety).

---

## 1) Top-level layout

- `backend/` — FastAPI backend service (Gunicorn/Uvicorn)
- `frontend/` — Next.js 15 UI (React 19)
- `model-server/` — local embedding server (FastAPI)
- `docs/` — Docusaurus documentation site
- `init-db/` — model weights initialization container
- `init-kafka/` — Kafka topic init container
- `unoserver/` — document conversion service
- `sandbox/` — restricted Python sandbox image
- `assets/` — logos/screenshots
- `docker-compose.yml` — main deployment (Mode A)
- `docker-compose-no-local-embedding.yml` — Mode B (Jina API)
- `.env.example` — Environment template (copy to `.env`)
- `Makefile` — Development shortcuts
- `.github/` — CI/workflows (not expanded here)

---

## 2) Entrypoints / Executables

### Docker Compose
- `docker-compose.yml` (primary, Mode A)
- `docker-compose-no-local-embedding.yml` (Mode B)
- `scripts/compose-clean` — wrapper script to sanitize environment

### Development Tools
- `Makefile` — Quick commands for development (recommended)
  ```bash
  make up          # Start services
  make logs        # View logs
  make health      # Check API health
  make reset       # Fresh restart
  ```

### Services
- Backend: `backend/entrypoint.sh` → `gunicorn app.main:app`
- Model server: `model-server/model_server.py` (FastAPI, port 8005)
- Frontend: `frontend/package.json` → `next start`
- Nginx: `frontend/nginx.conf` (routes `/`, `/api/`, `/minio-file/`)
- Kafka init: `init-kafka/init-kafka.sh`
- Model weights init: `init-db/init_models.sh`
- Unoserver: `unoserver/start_unoservers.sh`

---

## 3) Build/Run Scripts

### Makefile (Recommended)
```bash
make up           # Start all services
make down         # Stop all services
make restart      # Restart all services
make logs         # Follow logs
make logs-backend # Backend logs only
make reset        # Full reset (deletes data!)
make clean        # Remove everything
make health       # Check API health
make status       # Show service status
make build        # Rebuild all images
make ssh-backend  # SSH into backend
make ssh-model    # SSH into model server
```

### Frontend (`frontend/package.json`)
- `dev`: `next dev --turbopack`
- `build`: `next build`
- `start`: `next start`
- `lint`: `next lint`

### Docs (`docs/package.json`)
- `start`: `docusaurus start`
- `build`: `docusaurus build`
- `deploy`: `docusaurus deploy`
- `serve`, `clear`, `typecheck`, etc.

---

## 4) Config & Infra Files

- `.env` (secrets, not read)
- `.env.example` — Template with all environment variables documented
- `backend/alembic.ini` (DB migrations)
- `frontend/nginx.conf` (reverse proxy)
- `docker-compose*.yml` (service topology)
- `backend/app/core/config.py` — Pydantic settings
- `Makefile` — Development shortcuts

---

## 5) Service Inventory (Mode A)

### Application
- **backend** (FastAPI + Gunicorn) — Port 8000
- **frontend** (Next.js) — Port 3000
- **nginx** (Reverse proxy) — Port 8090
- **model-server** (local embeddings) — Port 8005
- **python-sandbox** (restricted execution)
- **unoserver** (document conversion) — Port 2003+

### Data / Infra
- **mysql** (relational DB) — Port 3306
- **mongodb** (chat/history) — Port 27017
- **redis** (tokens/tasks/locks) — Port 6379
- **kafka** + **kafka-init** (task queue) — Port 9092
- **minio** (object storage) — Port 9000
- **milvus** (vector DB: etcd + minio + standalone) — Port 19530
- **model-weights-init** (ColQwen downloads)

---

## 6) Ports and Routing

### Exposed (host)
- **8090** → Nginx (UI + API + MinIO proxy)

### Internal (containers)
| Service | Port | Protocol |
|---------|------|----------|
| frontend | 3000 | HTTP |
| backend | 8000 | HTTP |
| model-server | 8005 | HTTP |
| minio | 9000 | HTTP |
| minio console | 9001 | HTTP (internal) |
| milvus-standalone | 19530 | gRPC |
| milvus health | 9091 | HTTP |
| mysql | 3306 | TCP |
| mongodb | 27017 | TCP |
| redis | 6379 | TCP |
| kafka | 9092 | TCP |

### Kafka Topics
| Topic | Partitions | Retention | Purpose |
|-------|------------|-----------|---------|
| `task_generation` | 10 | 7 days | Main task queue |
| `task_generation_dlq` | 3 | 30 days | Dead Letter Queue for failed messages |
| unoserver | 2003+ | XML-RPC |

---

## 7) Dependencies (high level)

### Backend (Python)
- FastAPI, SQLAlchemy (async), Alembic, Redis, MongoDB (motor), Kafka (aiokafka)
- Milvus (pymilvus), MinIO (aioboto3), PDF/image tooling
- MCP client, OpenAI SDK

### Model Server (Python)
- ColPali / ColBERT stack (see `model-server/requirements.txt`)

### Frontend (Node)
- Next.js 15, React 19, Tailwind, Zustand, XYFlow

### Docs (Node)
- Docusaurus 3.8.x

---

## 8) Persistent Volumes

| Volume | Purpose |
|--------|---------|
| mysql_data | User authentication data |
| mongo_data | Chat history, workflows |
| redis_data | Caching, task state |
| kafka_data | Message queue persistence |
| minio_data | Object storage (documents) |
| milvus_etcd | Milvus metadata |
| milvus_minio | Milvus internal storage |
| milvus_data | Vector embeddings |
| model_weights | ColQwen2.5 model files |
| layra_sandbox_volume | Shared code execution files |
| mysql_migrations | Alembic migration snapshots |

---

## 9) Deployment Docs

- `README.md` — main deploy instructions
- `docs/docs/intro.md` — quick start & verification
- `docs/docs/RAG-Chat.md` — LLM config guidance
- `docs/LAYRA_DEEP_ANALYSIS.md` — technical deep dive
- `docs/RUNBOOK_COMPOSE_CLEAN.md` — compose-clean usage
- `.env.example` — environment template for `.env`
- `Makefile` — development command shortcuts

---

## 10) Fixed Issues (2024-01-20)

### Security
- ✅ Sandbox: `restricted_user` → `1000:1000` (numeric UID)
- ✅ Code scanner: Added regex patterns, forbidden imports
- ✅ MCP tools: Proper exception handling, type hints
- ✅ Fixed missing `await` on `scalars().first()` in security.py

### Code Quality
- ✅ Graph.py: Removed debug prints, fixed bare except
- ✅ Config.py: Fixed `Field` import, removed hardcoded paths
- ✅ Entrypoint.sh: Fixed Alembic migration (rm -rf migrations)
- ✅ Fixed typo: `messgae_type` → `message_type`
- ✅ Translated Chinese comments to English
- ✅ Fixed MinIO default port (9110 → 9000)
- ✅ Fixed model path (`/home/liwei/ai/` → `/model_weights/`)

### Infrastructure
- ✅ Added missing Milvus services to docker-compose.yml
- ✅ Enabled Kafka consumer in main.py
- ✅ Cleaned up old Docker containers/volumes
- ✅ Added backend healthcheck to docker-compose.yml
- ✅ Added `Makefile` with development shortcuts
- ✅ Created `.env.example` template

### Kafka Hardening (Critical)
- ✅ **Fixed commit order**: Process THEN commit (prevents data loss)
- ✅ **Added retry with exponential backoff**: 3 retries, 1s→2s→4s
- ✅ **Added Dead Letter Queue**: `task_generation_dlq` topic
- ✅ **Added idempotency**: Redis-based duplicate detection (24h TTL)
- ✅ **Added message validation**: Pydantic BaseModel schemas
- ✅ **Added concurrency control**: Max 5 concurrent tasks
- ✅ **Added metrics tracking**: processed, failed, dlq_sent, avg_time
- ✅ **Added health check**: Consumer health status endpoint
- ✅ **Updated init-kafka.sh**: Creates DLQ topic (3 partitions, 30-day retention)

### Critical Fixes (2026-01-21)
- ✅ **Removed Simple Auth**: Deleted anti-pattern auth module, endpoints, and configs. Enforced strict database auth.
- ✅ **Deduplication**: Cleaned up 30+ duplicate files in Knowledge Base.
- ✅ **GPU Optimization**: Reduced DPI from 200 to 150 to prevent VRAM OOM on large PDFs.
- ✅ **Neo4j Fix**: Resolved `UnknownHostException` via `extra_hosts` config.
- ✅ **Bulk Ingestion**: Optimized 129-file ingestion with batching and pauses.

---

## 11) Known Issues (Tech Debt)

### High Priority
- [ ] Redis keys not namespaced by user
- [ ] No rate limiting on API endpoints
- [ ] Sandbox network isolation needed

### Medium Priority
- [ ] Many type hint errors remain in workflow_engine.py
- [ ] No unit tests for core modules
- [ ] No CI/CD pipeline

### Low Priority
- [ ] docker-compose.gpu.yml has deprecated `device_requests`
- [ ] Missing API documentation (Swagger)
- [ ] No Prometheus metrics

---

## 12) Quick Commands

### Makefile (Recommended)
```bash
make up              # Start all services
make down            # Stop all services
make restart         # Restart all services
make logs            # View logs (follow mode)
make logs-backend    # Backend logs only
make logs-frontend   # Frontend logs only
make health          # Check API health
make status          # Show service status
make reset           # Full reset (WARNING: deletes data!)
make clean           # Remove all containers, volumes, images
make build           # Rebuild all images
make build-backend   # Rebuild backend only
make build-frontend  # Rebuild frontend only
make ssh-backend     # SSH into backend container
make ssh-model       # SSH into model server container
```

### Compose-clean (Original)
```bash
# Start all services
./scripts/compose-clean up -d

# Check status
./scripts/compose-clean ps

# View logs
./scripts/compose-clean logs -f backend

# Reset everything
./scripts/compose-clean down -v
./scripts/compose-clean up -d

# Check API health
curl http://localhost:8000/api/v1/health/check
```

### First Time Setup
```bash
# 1. Copy environment template
cp .env.example .env

# 2. (Optional) Edit .env with your values

# 3. Start LAYRA
make up

# 4. Check health
make health
```

---

## 13) Artifacts from this scan

- `docs/LAYRA_DEEP_ANALYSIS.md` — comprehensive technical analysis
- `docs/CHANGE_LOG.md` — complete change log with all fixes
- `docs/REPO_MAP.md` — this file (service inventory and quick reference)

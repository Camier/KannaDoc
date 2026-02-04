# Repo Map (LAYRA / KannaDoc)

**Scope:** `/LAB/@thesis/layra` (thesis fork of upstream LAYRA).  
**Updated:** 2026-02-04  
**Goal:** A practical, evidence-backed map of “what lives where” + how the pieces connect.

For “maximum effort” Mermaid diagrams (runtime + ingestion + RAG + eval + workflows), see:
- `docs/architecture/SYSTEM_DIAGRAMS.md`

If you’re trying to *run* the system, the canonical operational source of truth is:
- `docs/ssot/stack.md` (service registry, run modes, ports, drift radar)

If you’re trying to *understand the code*, this file is the fastest path from “repo” → “mental model”.

---

## 0) Orientation (start here)

- Repo overview: `README.md`
- Documentation index: `docs/INDEX.md`
- Stack + run modes SSOT: `docs/ssot/stack.md` + `docs/ssot/stack.yaml`
- “What changed recently”: `docs/operations/CHANGE_LOG.md`

---

## 1) Top-level layout

### Product code
- `backend/` — FastAPI backend (RAG, KB management, eval, workflow engine)
- `frontend/` — Next.js UI (React 19; `next` is `^16.1.6` in `frontend/package.json`)
- `model-server/` — embedding/model service (FastAPI; ColQwen/ColBERT + BGE-M3 sparse vectors)

### Ops / infrastructure
- `docker-compose.yml` — primary dev/research stack (18 services incl. Milvus/MinIO/Kafka/Redis/MySQL/Mongo + monitoring)
- `docker-compose.prod.yml` — production-hardened stack (limits/log rotation, no dev bind mounts, no docker socket mount)
- `docker-compose.override.yml` — local overrides (if used)
- `deploy/` — rollback strategy + compose guidance
- `monitoring/` — Prometheus config + alerts
- `grafana/` — Grafana provisioning (dashboards/datasources)

### Documentation / meta
- `docs/` — “human docs” (SSOT, runbooks, architecture, guides) + Docusaurus site sources
- `scripts/` — repo-level helper scripts (compose wrapper, ingestion helpers, health checks)
- `artifacts/` — generated artifacts (logs, reports, outputs)
- `assets/` — screenshots/logos

---

## 2) AGENTS.md scopes (local contribution rules)

Discovery:
- `AGENTS.md` (repo root) — global instructions (style, structure, canonical commands)
- `backend/lib/entity_extraction/AGENTS.md` — points back to root AGENTS section for V2 extractor docs
- `backend/lib/datalab/AGENTS.md` — points back to root AGENTS section for DataLab library docs
- `backend/scripts/datalab/AGENTS.md` — points back to root AGENTS section for DataLab scripts docs

Practical note: most module-specific details are consolidated into the root `AGENTS.md`.

---

## 3) Runtime topology (Docker Compose)

### Recommended entrypoint
- Prefer `./scripts/compose-clean …` over raw `docker compose …`.
  - It runs compose with a sanitized environment so host shell exports can’t silently override `.env`.
  - Script: `scripts/compose-clean`

### Compose files present in repo
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker-compose.override.yml`

### “Drift radar” (things referenced but missing)
Some helpers/docs reference compose files that do **not** exist in this checkout:
- `docker-compose-no-local-embedding.yml` (referenced by `Makefile` target `up-jina`)
- `docker-compose.thesis.yml` + `.env.thesis` (referenced by `Makefile` target `up-thesis`)
- `docker-compose.gpu.yml` (referenced by `Makefile` target `up-gpu`)
- `deploy/docker-compose.gpu.yml` (mentioned in `scripts/compose-clean --help`)

If you need these modes, they likely need to be restored (or the Makefile targets updated to current reality).

### Services (from `docker-compose.yml`)
Core application:
- `backend` — FastAPI API (internal `:8000`, exposed via `nginx`)
- `frontend` — Next.js UI (internal `:3000`, exposed via `nginx`)
- `nginx` — reverse proxy (`localhost:8090`)
- `model-server` — embeddings service (internal `:8005`)

Storage / infra:
- `mysql` — relational DB
- `mongodb` — chat/workflow/eval persistence
- `redis` — token/task/checkpoint state
- `kafka` + `kafka-init` — task queue + topic initialization
- `minio` — user object storage (note: mapped to host `127.0.0.1:9080/9081` in `docker-compose.yml`)
- `milvus-standalone` + `milvus-etcd` + `milvus-minio` — vector DB stack

Monitoring:
- `prometheus`
- `grafana`

Integration:
- `cliproxyapi` — LLM proxy adapter (used when `CLIPROXYAPI_BASE_URL` is set)

Sandbox / conversion:
- `python-sandbox` — code execution sandbox image
- `unoserver` — document conversion service
- `model-weights-init` — weights initialization container

---

## 4) Backend map (`backend/`)

### Main FastAPI entrypoint
- `backend/app/main.py` — constructs app via `FastAPIFramework`, registers routers, connects Mongo/Kafka/MinIO, sets CORS rules, installs Prometheus middleware.

Router wiring:
- `backend/app/api/__init__.py` — `api_router` with prefix `settings.api_version_url` (defaults to `/api/v1`)
- Endpoint modules: `backend/app/api/endpoints/`
  - `auth.py` — authentication
  - `chat.py` — conversation CRUD + file upload triggers
  - `sse.py` — SSE streaming endpoints (chat and workflow progress)
  - `knowledge_base.py` — KB operations and “search preview” (retrieval debugging)
  - `eval.py` — evaluation datasets/runs
  - `workflow.py` + `chatflow.py` — workflow editor + execution
  - `health.py` — liveness/readiness + `/metrics` export

### Settings and configuration
- `backend/app/core/config.py`
  - Uses `pydantic_settings` and loads env via `env_file = "../.env"`
  - Enforces “no default secrets”: `validate_settings()` fails if critical settings are empty
  - RAG knobs: `MILVUS_URI`, HNSW params (`HNSW_M`, `HNSW_EF_CONSTRUCTION`), hybrid search knobs (`RAG_HYBRID_*`), query vector caps (`rag_max_query_vecs`, etc.)

### Vector DB + retrieval implementation
- `backend/app/db/vector_db.py` — wrapper (Milvus primary)
- `backend/app/db/milvus.py` — `MilvusManager`:
  - HNSW index creation (dense) + sparse inverted index
  - hybrid search support via `RRFRanker` / `WeightedRanker` (controlled by `RAG_HYBRID_*`)
  - retry logic via `tenacity` for Milvus operations

### Embeddings and model providers
Embedding calls:
- `backend/app/rag/get_embedding.py` — fetches embeddings either from:
  - local `model-server` via HTTP (`settings.model_server_url`, default `http://model-server:8005`)
  - or Jina API when `EMBEDDING_MODEL=jina_embeddings_v4` and `JINA_API_KEY` is set

LLM provider selection:
- `backend/app/rag/provider_client.py` + `backend/app/core/llm/providers.yaml`
  - OpenAI-compatible clients (via `openai.AsyncOpenAI`) for multiple providers
  - Special resolution for GLM models: ZAI takes precedence over Zhipu when both keys present
  - CLIProxyAPI takes precedence when `CLIPROXYAPI_BASE_URL` is set

### Workflow engine
- `backend/app/workflow/` — workflow execution + sandbox + MCP tools integration
- `backend/app/workflow/workflow_engine.py` — orchestrator:
  - uses Docker-based sandbox (`python-sandbox`)
  - persists state/events in Redis streams (`workflow:events:{task_id}`)
  - has code scanning and guarded evaluation to reduce injection risk

Workflow definitions/examples:
- `backend/workflows/` — blueprint workflows + prompts + code nodes

---

## 5) Model server (`model-server/`)

What it does:
- Provides embedding endpoints used by the backend.

Where:
- `model-server/model_server.py` — FastAPI app with endpoints like:
  - `POST /embed_text`
  - `POST /embed_image`
  - `POST /embed_sparse`

Caching:
- Connects to Redis (best-effort); caches embeddings by SHA256 of input.

Dependencies:
- `model-server/requirements.txt` includes `colpali_engine`, `bitsandbytes`, `FlagEmbedding`, `redis`, etc.

---

## 6) Data + pipelines (thesis fork focus)

### Local corpus (checked into repo)
- `backend/data/pdfs/` — source PDFs (README: `backend/data/pdfs/README.txt`)
- `backend/data/extractions/` — per-doc extraction folders (normalized blocks + entities)
- `backend/data/corpus/` — aggregated metadata/corpus files

### DataLab pipeline (library)
- `backend/lib/datalab/` — PDF → Marker API → normalized blocks/images/figures
  - key modules include normalization, evidence gating, section extraction, batch extraction

### DataLab pipeline (scripts)
- `backend/scripts/datalab/` — orchestration scripts (entity extraction, ingest, eval, optimize, verify)
  - examples: `extract_entities_v2.py`, `milvus_ingest.py`, `rag_eval.py`, `rag_optimize.py`, `verify_merge.py`

### Pipeline audit
- `backend/docs/PIPELINE_AUDIT_2026-02-02.md` — evidence-based counts + known gaps
  - Notably: entity relationships are currently empty (legacy-migrated V1 entities)
  - Neo4j is explicitly disabled (scripts exist but not deployed)

---

## 7) Evaluation system

Code:
- `backend/app/eval/metrics.py` — MRR / nDCG@K / P@K / R@K
- `backend/app/eval/runner.py` — runs evaluation and tracks p95 latency
- `backend/app/api/endpoints/eval.py` — REST endpoints:
  - `POST /api/v1/eval/datasets`
  - `POST /api/v1/eval/run`
  - plus listing and retrieval endpoints

Data/config:
- `backend/app/eval/config/` — thresholds + dev dataset seeds (if present)
- Thesis writeups: `docs/thesis/evaluation/…`

---

## 8) Frontend (`frontend/`)

What it is:
- Next.js app (React 19) with chat UI, KB management UI, and workflow editor UI.

Entrypoints:
- `frontend/src/app/…` — app router pages/layouts
- `frontend/src/components/…` — UI components
- `frontend/src/lib/api/…` — backend API clients
- Tests:
  - unit: Vitest via `npm run test:run`
  - e2e: Playwright (`frontend/tests/e2e/`)

---

## 9) Tests + CI

Backend tests:
- `backend/tests/` — pytest suite (unit/integration style mixed)
- CI: `.github/workflows/test.yml` runs `pytest` with coverage (`--cov=app`)

Frontend checks:
- CI builds frontend (`npm run build`)

Local shortcuts:
- `make test` / `make test-frontend` / `make test-all`

---

## 10) Security / footguns (map-only; no changes applied here)

- Secrets should live in `.env` (not committed) or a secret manager.
- ⚠️ Repo contains at least one file that appears to embed a literal API key string:
  - `backend/test_glm_models.py`
  - Treat as compromised if it’s real; rotate the key, then move the script to env-based config.

Operational safety:
- Prefer `./scripts/compose-clean` to avoid accidental env override of `.env`.
- `backend/app/main.py` enforces explicit `ALLOWED_ORIGINS` when `DEBUG_MODE=false`.

---

## 11) Quick commands (most common)

### Boot (docker)
- `./scripts/compose-clean up -d --build`
- `make up`
- Health:
  - `curl -f http://localhost:8090/api/v1/health/check`
  - `curl -f http://localhost:8090/api/v1/health/ready`

### Backend tests
- `cd backend && PYTHONPATH=. pytest`

### Frontend dev
- `cd frontend && npm ci && npm run dev`

### Docs dev (Docusaurus)
- `cd docs && npm ci && npm run start`

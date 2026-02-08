# Layer → File Map (LAYRA)

**Scope:** `/LAB/@thesis/layra`  
**Updated:** 2026-02-04  
**Goal:** Map each “étage” (layer/maillon) to the **exact repo files** that implement it.

Notes:
- This is a *code-navigation* map (what to open when you want to change/understand a layer).
- `.env` exists but is not referenced here beyond filenames (no secrets are copied).
- For system-level Mermaid diagrams, see `docs/architecture/SYSTEM_DIAGRAMS.md`.
- For a broader repo map, see `docs/REPO_MAP.md`.
- For an *exhaustive* file inventory (generated lists), see `artifacts/layer-file-map/README.txt`.

---

## 0) Ops / SSOT / Documentation (what’s canonical)

**Stack SSOT (run modes / ports / drift radar)**
- `docs/ssot/stack.md`
- `docs/ssot/stack.yaml`

**Docs entrypoints**
- `README.md`
- `docs/INDEX.md`
- `docs/operations/RUNBOOK.md`
- `docs/operations/DEPLOYMENT_DIAGRAM.md`
- `docs/operations/CHANGE_LOG.md`

**Architecture / repo navigation**
- `docs/REPO_MAP.md`
- `docs/architecture/SYSTEM_DIAGRAMS.md`
- `docs/architecture/REPO_MAP.md` (legacy pointer; should defer to `docs/REPO_MAP.md`)

---

## 1) Runtime Topology (Docker Compose, containers, ports)

**Compose**
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker-compose.override.yml`

**Compose wrappers / helpers**
- `scripts/compose-clean`
- `Makefile`

**Per-service container build**
- Backend: `backend/Dockerfile`, `backend/entrypoint.sh`, `backend/gunicorn_config.py`, `backend/requirements.txt`
- Model server: `model-server/Dockerfile`, `model-server/requirements.txt`
- Frontend: `frontend/Dockerfile`

**Reverse proxy config**
- `frontend/nginx.conf`

---

## 2) Frontend (UI / Next.js)

**Entrypoints & build**
- `frontend/package.json`
- `frontend/next.config.ts`
- `frontend/tsconfig.json`

**Serving / routing**
- `frontend/nginx.conf`

**Where the UI lives**
- `frontend/src/` (Next.js app code; large subtree)

---

## 3) Backend Application (FastAPI entrypoint + routing)

**FastAPI entrypoint**
- `backend/app/main.py`

**Router wiring**
- `backend/app/api/router.py`

**Framework wrapper (app construction / wiring)**
- `backend/app/framework/__init__.py`
- `backend/app/framework/app_framework.py`

**Core utilities (settings, security, logging, embeddings helpers)**
- `backend/app/core/__init__.py`
- `backend/app/core/circuit_breaker.py`
- `backend/app/core/config.py`
- `backend/app/core/embeddings.py`
- `backend/app/core/logging.py`
- `backend/app/core/security.py`
- `backend/app/core/utils.py`

**Core LLM service**
- `backend/app/core/llm/__init__.py`
- `backend/app/core/llm/chat_service.py`
- Model config is user-supplied (`model_name`, `model_url`, `api_key`) and stored in MongoDB (no `providers.yaml`).

---

## 4) Backend API Endpoints (REST surface)

All endpoint modules (FastAPI routers):
- `backend/app/api/endpoints/__init__.py`
- `backend/app/api/endpoints/auth.py`
- `backend/app/api/endpoints/base.py`
- `backend/app/api/endpoints/chat.py`
- `backend/app/api/endpoints/chatflow.py`
- `backend/app/api/endpoints/config.py`
- `backend/app/api/endpoints/eval.py`
- `backend/app/api/endpoints/health.py`
- `backend/app/api/endpoints/knowledge_base.py`
- `backend/app/api/endpoints/sse.py`
- `backend/app/api/endpoints/workflow.py`

---

## 5) Ingestion Path (Upload → Kafka → Convert → Embed → Insert)

**Upload endpoint (creates KB, uploads to MinIO, enqueues Kafka tasks)**
- `backend/app/api/endpoints/chat.py`

**Kafka producer (enqueue file/workflow tasks)**
- `backend/app/utils/kafka_producer.py`

**Kafka consumer (consume tasks; concurrency; DLQ; idempotency)**
- `backend/app/utils/kafka_consumer.py`

**Ingestion orchestration (download, convert, embed, insert, persist metadata)**
- `backend/app/rag/utils.py` (`process_file`, `generate_embeddings`, `insert_to_milvus`)

**File conversion (PDF / docx / images → page images)**
- `backend/app/rag/convert_file.py`
- `backend/app/utils/unoconverter.py` (unoserver client)

**Task status storage (progress + workflow events)**
- `backend/app/db/redis.py`
- `backend/app/db/cache.py`

---

## 6) Embeddings Layer (dense + sparse)

**Backend embedding client (local model-server or optional Jina)**
- `backend/app/rag/get_embedding.py`
- `backend/app/core/circuit_breaker.py` (embedding_service_circuit)

**Model server (embedding endpoints + implementations)**
- `model-server/model_server.py`
- `model-server/config.py`
- `model-server/colbert_service.py`
- `model-server/bge_m3_service.py`

---

## 7) Vector Database Layer (Milvus, indexes, hybrid search)

**Vector DB abstraction**
- `backend/app/db/vector_db.py`
- `backend/app/db/__init__.py`

**Milvus implementation**
- `backend/app/db/milvus.py`

**All DB connectors (used by ingestion/retrieval/workflows/eval)**
- `backend/app/db/cache.py`
- `backend/app/db/db_utils.py`
- `backend/app/db/milvus.py`
- `backend/app/db/miniodb.py`
- `backend/app/db/mongo.py`
- `backend/app/db/mysql_base.py`
- `backend/app/db/mysql_session.py`
- `backend/app/db/redis.py`
- `backend/app/db/vector_db.py`

**Object storage + DB connectors used by ingestion/retrieval**
- `backend/app/db/miniodb.py`
- `backend/app/db/mongo.py`
- `backend/app/db/mysql_base.py`
- `backend/app/db/mysql_session.py`
- `backend/app/db/db_utils.py`

---

## 8) RAG Query Path (Retrieve → hydrate hits → LLM)

**Core RAG execution (history + retrieval + prompt assembly + streaming)**
- `backend/app/core/llm/chat_service.py`

**RAG helpers (message structures, utilities)**
- `backend/app/rag/message.py`
- `backend/app/rag/utils.py` (image hydration via MinIO, helper functions)

**LLM provider selection / clients**
- Model configuration storage: `backend/app/db/repositories/model_config.py`
- LLM client wiring: `backend/app/core/llm/chat_service.py`

**Embeddings utilities (normalize/downsample multivectors)**
- `backend/app/core/embeddings.py`

---

## 9) Workflow Engine (agents/workflows + sandbox + MCP tools + SSE)

**Workflow API**
- `backend/app/api/endpoints/workflow.py`
- `backend/app/api/endpoints/sse.py` (streaming progress/events)

**Workflow engine & graph**
- `backend/app/workflow/workflow_engine.py`
- `backend/app/workflow/graph.py`
- `backend/app/workflow/utils.py`

**Sandbox + safety**
- `backend/app/workflow/sandbox.py`
- `backend/app/workflow/code_scanner.py`

**MCP tool bridge**
- `backend/app/workflow/mcp_tools.py`

**Extracted workflow components**
- `backend/app/workflow/components/__init__.py`
- `backend/app/workflow/components/constants.py`
- `backend/app/workflow/components/llm_client.py`
- `backend/app/workflow/components/checkpoint_manager.py`

---

## 10) Evaluation Harness (retrieval metrics + runs)

**Eval API**
- `backend/app/api/endpoints/eval.py`

**Eval core**
- `backend/app/eval/__init__.py`
- `backend/app/eval/dataset.py`
- `backend/app/eval/runner.py`
- `backend/app/eval/metrics.py`
- `backend/app/eval/labeler.py`
- `backend/app/eval/query_generator.py`

**Eval config datasets**
- `backend/app/eval/config/` (subtree, includes `dataset_dev.jsonl`, `thresholds.yaml`)

---

## 11) Persistence Model (MongoDB repositories + Pydantic models)

**Repository manager + repositories (MongoDB CRUD layer)**
- `backend/app/db/repositories/__init__.py`
- `backend/app/db/repositories/base.py`
- `backend/app/db/repositories/chatflow.py`
- `backend/app/db/repositories/conversation.py`
- `backend/app/db/repositories/eval.py`
- `backend/app/db/repositories/file.py`
- `backend/app/db/repositories/knowledge_base.py`
- `backend/app/db/repositories/model_config.py`
- `backend/app/db/repositories/repository_manager.py`
- `backend/app/db/repositories/workflow.py`

**Models**
- `backend/app/models/__init__.py`
- `backend/app/models/chatflow.py`
- `backend/app/models/conversation.py`
- `backend/app/models/knowledge_base.py`
- `backend/app/models/model_config.py`
- `backend/app/models/shared.py`
- `backend/app/models/user.py`
- `backend/app/models/workflow.py`

**Schemas (API I/O)**
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/chat_responses.py`
- `backend/app/schemas/user.py`

---

## 12) DataLab Pipeline (PDF → blocks/assets) + Scripts (batch operations)

### 12.1 Library (`backend/lib/datalab/`)
- `backend/lib/datalab/__init__.py`
- `backend/lib/datalab/datalab_api.py`
- `backend/lib/datalab/datalab_process.py`
- `backend/lib/datalab/normalization.py`
- `backend/lib/datalab/evidence_gate.py`
- `backend/lib/datalab/section_extractor.py`
- `backend/lib/datalab/batch_extractor.py`
- `backend/lib/datalab/block_index.py`
- `backend/lib/datalab/datalab_ingest.py`
- `backend/lib/datalab/datalab_utils.py`

### 12.2 Scripts (`backend/scripts/datalab/`)
- `backend/scripts/datalab/aggregate_corpus.py`
- `backend/scripts/datalab/consolidate_archive.py`
- `backend/scripts/datalab/create_id_mapping.py`
- `backend/scripts/datalab/extract_deepseek.py`
- `backend/scripts/datalab/migrate_entities_v2.py`
- `backend/scripts/datalab/milvus_ingest.py`
- `backend/scripts/datalab/neo4j_ingest.py` (graph ingestion; currently disabled in deployment)
- `backend/scripts/datalab/rag_eval.py`
- `backend/scripts/datalab/rag_optimize.py`
- `backend/scripts/datalab/recover_extractions.py`
- `backend/scripts/datalab/tidy_data.py`
- `backend/scripts/datalab/verify_merge.py`

### 12.3 Pipeline audits / notes
- `backend/docs/PIPELINE_AUDIT_2026-02-02.md`
- `backend/docs/README.md`

---

## 13) Security / Auth / Observability (cross-cutting “étages”)

**Security & auth**
- `backend/app/core/security.py`
- `backend/app/api/endpoints/auth.py`

**Logging**
- `backend/app/core/logging.py`

**Middlewares & error handling**
- `backend/app/utils/middlewares.py`
- `backend/app/utils/error_handlers.py`

**Prometheus metrics**
- `backend/app/utils/prometheus_metrics.py`
- `backend/app/api/endpoints/health.py` (health + metrics surface)

**Other backend utilities (helpers; referenced across multiple étages)**
- `backend/app/utils/__init__.py`
- `backend/app/utils/error_handlers.py`
- `backend/app/utils/ids.py`
- `backend/app/utils/kafka_consumer.py`
- `backend/app/utils/kafka_producer.py`
- `backend/app/utils/middlewares.py`
- `backend/app/utils/prometheus_metrics.py`
- `backend/app/utils/timezone.py`
- `backend/app/utils/types.py`
- `backend/app/utils/unoconverter.py`
- `backend/app/utils/validation.py`

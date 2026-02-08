# IMPORTANT: Consolidated Repo Overview (LAYRA / KannaDoc)

Scope: /LAB/@thesis/layra
Updated: 2026-02-05
Purpose: Single-page, high-density map of services, configs, dependencies, and paths.

---

## 1) Exhaustive Services and Configs (Milvus / ColQwen / API / Workflow)

```
SERVICE               | PORTS/EXPOSE                    | HEALTHCHECK (if defined)                                   | CONFIG / VARS (defaults)                        | PRIMARY FILES
---------------------|----------------------------------|-----------------------------------------------------------|-----------------------------------------------|-----------------------------
nginx (proxy)         | http://localhost:8090            | /api/v1/health/check (via backend)                        | N/A                                           | /docs/ssot/stack.yaml
backend (FastAPI)     | internal: 8000 -> nginx           | curl -f http://localhost:8000/api/v1/health/check          | DB_URL, REDIS_*, MONGODB_*, MINIO_*, KAFKA_*   | /backend/app/core/config.py
frontend (Next.js)    | internal: 3000 -> nginx           | curl -f http://localhost:3000                              | NEXT_PUBLIC_API_BASE_URL                       | /.env.example
milvus-standalone     | internal:19530, host:127.0.0.1:19531 | curl -f http://localhost:9091/healthz                      | MILVUS_URI, VECTOR_DB                          | /docker-compose.yml
milvus-etcd           | 2379                            | etcdctl endpoint health                                    | ETCD_*                                        | /docker-compose.yml
milvus-minio          | 9000, 9001                      | curl -f http://localhost:9000/minio/health/live            | MILVUS_MINIO_*                                | /docker-compose.yml
minio (assets)        | host 9080:9000, 9081:9001       | curl -f http://localhost:9000/minio/health/live            | MINIO_*                                       | /docker-compose.yml
mongodb               | 27017                           | mongosh --eval db.adminCommand('ping')                     | MONGODB_*                                     | /docker-compose.yml
redis                 | 6379                            | redis-cli -a $REDIS_PASSWORD ping | grep -q PONG           | REDIS_URL, REDIS_PASSWORD                     | /docker-compose.yml
mysql                 | 3306                            | mysqladmin ping -h localhost -u root -p"$MYSQL_ROOT_PASSWORD" | MYSQL_*, DB_URL                            | /docker-compose.yml
kafka                 | 9092/9094                       | kafka-topics.sh --bootstrap-server localhost:9092 --list   | KAFKA_*                                       | /docker-compose.yml
kafka-init            | -                                | depends_on kafka                                           | KAFKA_TOPIC, KAFKA_PARTITIONS_NUMBER          | /docker-compose.yml
model-server (ColQwen)| 8005                            | none explicit                                              | MODEL_SERVER_URL, COLBERT_MODEL_PATH          | /docker-compose.override.yml
python-sandbox        | -                                | none                                                      | SANDBOX_SHARED_VOLUME, SANDBOX_MEMORY_LIMIT   | /docker-compose.yml
cliproxyapi (optional)| 8085/8317                       | none                                                      | CLIPROXYAPI_BASE_URL, CLIPROXYAPI_API_KEY      | /docker-compose.yml
prometheus            | 9090                            | default Prometheus                                         | N/A                                           | /docker-compose.yml
grafana               | 3001                            | default Grafana                                            | N/A                                           | /docker-compose.yml
unoserver             | 2003/3003                       | none                                                      | UNOSERVER_*                                   | /docker-compose.yml
model-weights-init    | -                                | none                                                      | MODEL_BASE_URL, COLBERT_MODEL_PATH            | /docker-compose.yml

Config sources (canonical):
- /LAB/@thesis/layra/.env.example
- /LAB/@thesis/layra/backend/app/core/config.py
- /LAB/@thesis/layra/docs/ssot/stack.yaml
- /LAB/@thesis/layra/docker-compose.yml
- /LAB/@thesis/layra/docker-compose.prod.yml
- /LAB/@thesis/layra/docker-compose.override.yml
- /LAB/@thesis/layra/backend/app/db/repositories/model_config.py (user-supplied LLM config stored in MongoDB)
```

---

## 2) Complete Dependency Tree (module -> module -> artifact)

```
PDFs
└─ /backend/lib/datalab/datalab_process.py
   ├─ /backend/lib/datalab/datalab_api.py
   ├─ /backend/lib/datalab/normalization.py
   ├─ /backend/lib/datalab/section_extractor.py
   ├─ /backend/lib/datalab/evidence_gate.py
   └─ /backend/lib/datalab/block_index.py
      └─ Artifact: /backend/data/extractions/<doc_id>/normalized.json

normalized.json
├─ /backend/scripts/datalab/extract_deepseek.py
│  └─ /backend/lib/entity_extraction/extractor.py
│     ├─ /backend/lib/entity_extraction/prompt.py
│     ├─ /backend/lib/entity_extraction/deepseek_client.py
│     └─ /backend/lib/entity_extraction/schemas.py
│        └─ Artifact: /backend/data/extractions/<doc_id>/entities.json
│
└─ /backend/app/rag/get_embedding.py
   ├─ /backend/app/core/embeddings.py
   ├─ MODEL_SERVER_URL (ColQwen local) / JINA_API_KEY (cloud)
   └─ Artifact: ColQwen multi-vectors -> Milvus collection colqwen*

Milvus
├─ /backend/app/db/milvus.py
└─ /backend/app/db/vector_db.py

RAG API
└─ /backend/app/api/endpoints/knowledge_base.py
   ├─ /backend/app/rag/get_embedding.py
   └─ /backend/app/db/milvus.py

Eval
└─ /backend/app/eval/runner.py
   ├─ /backend/app/eval/metrics.py
   ├─ /backend/app/eval/labeler.py
   ├─ /backend/app/eval/dataset.py
   └─ Artifacts: /backend/app/eval/config/{dataset_dev.jsonl,ground_truth.json}

Workflow
└─ /backend/app/workflow/workflow_engine.py
   ├─ /backend/app/workflow/graph.py
   ├─ /backend/app/workflow/sandbox.py
   ├─ /backend/app/workflow/components/*
   └─ /backend/app/utils/kafka_consumer.py
      └─ Redis / Kafka / Mongo / MySQL state + queues
```

---

## 3) Final ASCII Diagram (detailed, exact paths + ports)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SOURCES                                                                      │
│ /LAB/@thesis/layra/backend/data/pdfs/*.pdf                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ DATALAB PIPELINE                                                              │
│ /backend/lib/datalab/datalab_process.py                                       │
│ /backend/lib/datalab/datalab_api.py                                           │
│ /backend/lib/datalab/normalization.py                                         │
│ /backend/lib/datalab/section_extractor.py                                     │
│ /backend/lib/datalab/evidence_gate.py                                         │
│ /backend/lib/datalab/block_index.py                                           │
│ Output: /backend/data/extractions/<doc_id>/normalized.json                   │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌──────────────────────────────┐      ┌───────────────────────────────────────┐
│ ENTITY EXTRACTION V3.1        │      │ EMBEDDINGS + RETRIEVAL                │
│ /scripts/datalab/extract_deepseek.py │ /backend/app/rag/get_embedding.py      │
│ /lib/entity_extraction/*      │      │ /backend/app/core/embeddings.py        │
│ Output: entities.json         │      │ MODEL_SERVER_URL (ColQwen local)       │
└──────────────────────────────┘      │ /backend/app/db/milvus.py              │
          │                           │ Milvus collection: colqwen*           │
          ▼                           └───────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────┐
│ FASTAPI API                                                                   │
│ /backend/app/api/endpoints/knowledge_base.py                                  │
│ /backend/app/api/endpoints/chat.py                                            │
│ /backend/app/api/endpoints/eval.py                                            │
│ /backend/app/api/endpoints/workflow.py                                        │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ EVALUATION                                                                    │
│ /backend/app/eval/runner.py                                                   │
│ /backend/app/eval/metrics.py                                                  │
│ /backend/app/eval/labeler.py                                                  │
│ /backend/app/eval/dataset.py                                                  │
│ Artifacts: /backend/app/eval/config/{dataset_dev.jsonl,ground_truth.json}     │
└──────────────────────────────────────────────────────────────────────────────┘

================================================================================
INFRA / SERVICES (docker)
================================================================================
nginx -> http://localhost:8090 (proxy)
backend -> internal:8000 (health: /api/v1/health/check)
frontend -> internal:3000

milvus-standalone -> internal:19530, host:127.0.0.1:19531 (health: http://localhost:9091/healthz)
milvus-etcd -> 2379
milvus-minio -> 9000/9001

model-server (ColQwen) -> 8005 (GPU: /docker-compose.override.yml)
minio (assets) -> host 9080:9000, 9081:9001
mongodb -> 27017 (health ping)
redis -> 6379 (health: PONG)
mysql -> 3306 (health ping)
kafka -> 9092/9094 (health: topics list)
python-sandbox -> internal volume only
cliproxyapi -> 8085/8317 (optional proxy)
```

---

## 4) Related docs (canonical cross-refs)

- /LAB/@thesis/layra/docs/ssot/stack.md
- /LAB/@thesis/layra/docs/ssot/stack.yaml
- /LAB/@thesis/layra/docs/REPO_MAP.md
- /LAB/@thesis/layra/docs/architecture/SYSTEM_DIAGRAMS.md
- /LAB/@thesis/layra/docs/reference/ENVIRONMENT_VARIABLES.md
```

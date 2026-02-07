**Version:** 1.0.0
**Last Updated:** 2026-02-07

---

## Purpose

This runbook migrates Milvus data from a **host/systemd Milvus** to the **docker-compose Milvus stack** used by this repo.

Primary goals:
- Preserve **collection names**, **schemas**, **index types/params**, and **aliases** required by the RAG pipeline.
- Keep the host Milvus intact for **instant rollback**.

This migration is intentionally **API-level** (scan + insert + rebuild indexes). It is the safest approach for this environment because the host Milvus uses **local storage** while the docker Milvus uses **remote storage** backed by `milvus-minio`.

---

## Architecture (Source vs Target)

### Source (host)

- Milvus runs as a systemd service: `milvus.service`
- Port: `127.0.0.1:19530`
- Storage: `common.storageType: local` (see `/etc/milvus/configs/milvus.yaml`)
- Embedded etcd: `etcd.use.embed: true`

### Target (docker-compose)

- Services: `milvus-etcd`, `milvus-minio`, `milvus-standalone`
- Internal Milvus URI (from containers): `http://milvus-standalone:19530`
- Host-published port (for debugging tools): `http://127.0.0.1:19531`
  - This avoids clashing with host Milvus on `:19530`.
- Persistence (3 volumes):
  - `milvus_etcd` (metadata)
  - `milvus_minio` (segments and index files)
  - `milvus_data` (local state)

---

## What Must Be Preserved (Thesis Corpus)

These objects are treated as the contract for RAG correctness:

### Dense patch collection

- Collection: `colpali_kanna_128`
- Schema:
  - `pk` (INT64, primary, auto_id)
  - `vector` (FLOAT_VECTOR, dim=128)
  - `image_id` (VARCHAR)
  - `page_number` (INT64)
  - `file_id` (VARCHAR)
  - `filename` (VARCHAR)
  - `enable_dynamic_field: true`
- Indexes:
  - `vector_index`: HNSW, metric `IP`, params `M=32`, `efConstruction=500`
  - `file_id_index`: INVERTED
  - `page_number_index`: INVERTED
  - `image_id_index`: INVERTED

### Sparse page sidecar

- Collection: `colpali_kanna_128_pages_sparse`
- Schema:
  - `page_id` (VARCHAR, primary, auto_id=false)
  - `sparse_vector` (SPARSE_FLOAT_VECTOR)
  - `file_id` (VARCHAR)
  - `page_number` (INT64)
  - `text_preview` (VARCHAR)
  - `enable_dynamic_field: false`
- Indexes:
  - `sparse_vector_index`: SPARSE_INVERTED_INDEX, metric `IP`, `drop_ratio_build=0.2`
  - `page_id_index`: INVERTED
  - `file_id_index`: INVERTED
  - `page_number_index`: INVERTED

### Alias (backend expects this)

- Alias: `colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1`
- Points to: `colpali_kanna_128`

Notes:
- The patch collection uses `auto_id=True`, so primary key values are not preserved.
- The migration rebuilds indexes on the target; index *parameters* are preserved.

---

## Migration Tool

Script:
- `backend/scripts/migrate_milvus_host_to_docker.py`

Defaults:
- Source: `--src-uri http://127.0.0.1:19530`
- Target: `--dst-uri http://127.0.0.1:19531`

Progress artifacts:
- Status JSON: `--status-file /tmp/layra_milvus_migration_status.json`

Important:
- Run the script from the host (not from inside `layra-backend`).
- If your environment prevents writing `__pycache__`, run with:
  - `PYTHONDONTWRITEBYTECODE=1`

---

## Step-by-Step Procedure

### 0) Preconditions

1) Ensure the docker Milvus stack is running and healthy:

```bash
docker compose up -d milvus-etcd milvus-minio milvus-standalone
docker compose ps milvus-etcd milvus-minio milvus-standalone
```

2) Confirm source Milvus is reachable:

```bash
python3 - <<'PY'
from pymilvus import MilvusClient
c = MilvusClient(uri='http://127.0.0.1:19530')
print(c.list_collections())
print(c.get_collection_stats('colpali_kanna_128'))
PY
```

3) Confirm target Milvus is reachable:

```bash
python3 - <<'PY'
from pymilvus import MilvusClient
c = MilvusClient(uri='http://127.0.0.1:19531')
print(c.list_collections())
PY
```

### 1) Run the migration

This will (a) drop existing target collections if any, (b) recreate schema, (c) copy rows in batches,
(d) create indexes, (e) recreate alias, and (f) verify.

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 backend/scripts/migrate_milvus_host_to_docker.py \
  --drop-dst \
  --batch-size 2048 \
  --flush-every 50 \
  --status-file /tmp/layra_milvus_migration_status.json
```

### 2) Monitor progress

```bash
cat /tmp/layra_milvus_migration_status.json

# If you run the migration in background with redirected output, tail the log file:
# tail -n 50 /tmp/layra_milvus_migration.log
```

To monitor HNSW build status:

```bash
python3 - <<'PY'
from pymilvus import MilvusClient
c = MilvusClient(uri='http://127.0.0.1:19531')
d = c.describe_index('colpali_kanna_128', 'vector_index')
print('state', d.get('state'), 'indexed', d.get('indexed_rows'), 'pending', d.get('pending_index_rows'))
PY
```

### 3) Verify target matches source

The script can run a strict verification check without modifying anything:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 backend/scripts/migrate_milvus_host_to_docker.py --verify-only
```

---

## Cutover (Backend -> docker Milvus)

1) Set `MILVUS_URI` in `.env`:

```bash
MILVUS_URI=http://milvus-standalone:19530
```

2) Restart backend:

```bash
docker compose up -d backend
```

3) Verify readiness:

```bash
curl -sf http://localhost:8090/api/v1/health/ready | python3 -m json.tool
docker exec layra-backend python3 -c "import os; print('MILVUS_URI=', os.environ.get('MILVUS_URI'))"
```

4) Smoke test retrieval (search preview)

Find a real knowledge base id in MongoDB:

```bash
docker exec layra-backend python3 - <<'PY'
from pymongo import MongoClient
import os
u=os.environ['MONGODB_ROOT_USERNAME']
p=os.environ['MONGODB_ROOT_PASSWORD']
uri=f'mongodb://{u}:{p}@mongodb:27017/admin'
mc=MongoClient(uri)
db=mc.chat_mongodb
print([d.get('knowledge_base_id') for d in db.knowledge_bases.find({}, {'knowledge_base_id':1,'_id':0})])
PY
```

Then call:

```bash
curl -sf -X POST \
  "http://localhost:8090/api/v1/kb/knowledge-base/<kb_id>/search-preview" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Quercetin inhibits COX-2","top_k":5}' \
  | python3 -m json.tool
```

---

## Rollback (Immediate)

If anything is wrong after cutover, revert `.env` and restart backend.

1) In `.env`:

```bash
MILVUS_URI=http://host.docker.internal:19530
```

2) Restart backend:

```bash
docker compose up -d backend
```

The host Milvus remains unchanged during migration, so rollback is instant.

---

## Troubleshooting

### Docker compose warns about missing provider keys

Warnings like:

- `The "OPENAI_API_KEY" variable is not set. Defaulting to a blank string.`

Mean: docker compose interpolated `${OPENAI_API_KEY}` but it was not set in your shell or `.env`.

Fix options:
- Define the variable (real value) if you use that provider.
- Or explicitly define it as empty in `.env` to silence warnings:
  - `OPENAI_API_KEY=`
  - `JINA_API_KEY=`
  - `JINA_EMBEDDINGS_V4_URL=`
  - `OLLAMA_API_KEY=`

### Target drop fails because aliases exist

Milvus forbids dropping collections with aliases. The script drops aliases first.
If you see this error manually, drop the alias before dropping the collection.

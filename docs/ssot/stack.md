# Stack SSOT - LAYRA Architecture

> **Version:** 3.2.0
> **Last Updated:** 2026-01-29
> **Status:** ✅ Active
> **Focus:** RAG Chat & Models Configuration + ZhipuAI Coding Plan
> **Changes:**
> - Added ZhipuAI Coding Plan provider (glm-4.5, glm-4.6, glm-4.7)
> - Fixed MongoDB schema drift (model_config collection)
> - Fixed SSE endpoint bug (message_id parameter)
> - Updated database documentation (MONGODB_DB=chat_mongodb)
> - Qdrant vector database removed (Milvus now sole backend)
> - Service count reduced from 20 to 18
> - RAG chat system verified operational

---

## North Star

LAYRA is a visual-native RAG and workflow engine that **sees documents like a human** using visual embeddings (ColQwen2.5/Jina) and **executes complex workflows** through Python code execution.

**Definition of Done (DoD):**
- System boots with `./scripts/compose-clean up -d`
- User can upload PDF, query it, and receive layout-aware answers
- Workflow engine can execute Python code in sandboxed environment
- All services have documented entrypoints and dependencies
- Native deployment feasibility is assessed for each service

## Deployment Architecture (Post-Cleanup)

LAYRA uses a **Unified Container Stack** managed via Docker Compose.

### Cleanup Summary (2026-01-28)
- ✅ **Qdrant vector database removed** - Milvus now the sole vector DB backend
- ✅ **Duplicate service investigation** - Two MinIO services confirmed (required: main user storage + Milvus internal)
- ✅ **Nginx verification** - Single confirmed (no duplicates)
- ✅ **Service count reduced** - From 20 to 18 services

### Core Configuration
- **Standard Deployment**: `docker-compose.yml`
  - Optimized for **Production & Research**
  - Includes **GPU Acceleration** (NVIDIA CUDA 12.4)
  - Supports **Multi-LLM Providers** (OpenAI, DeepSeek, Moonshot, Zhipu, MiniMax, Cohere, Ollama, Anthropic, Google)
  - Features **Single Tenant Mode** for shared data access
  - **Monitoring**: Prometheus & Grafana included by default
  - **Vector DB**: Milvus (Qdrant removed for simplification)

### Service Inventory
| Service | Role | Key Config |
|---------|------|------------|
| **Backend** | FastAPI Core | `MAX_WORKERS=4`, Async MySQL/Mongo/Redis |
| **Model Server** | RAG/Embeddings | **GPU Optimized** (`PYTORCH_CUDA_MEMORY_FRACTION=0.9`) |
| **Milvus** | Vector DB | Standalone v2.6.21 + MinIO + Etcd |
| **Middleware** | Async Broker | Kafka (10 partitions) + Redis |
| **Storage** | Data Persistence | MySQL 8.0, MongoDB 7.0, MinIO |
| **Frontend** | UI/UX | Next.js 15 + Nginx Reverse Proxy |


## Service Registry

### Legend

| Symbol | Meaning |
|--------|---------|
| ⚡ | **Critical** - On query/ingest path |
| 🔒 | **Stateful** - Has persistent data |
| 🔗 | **Charnière** - Has 2+ dependents or is entry point |
| 🐳 | **Docker-hard** - Difficult to run natively |
| ✅ | **Native-friendly** - Can run on host |
| ⚠️ | **Hybrid** - Possible but requires effort |

### Application Services (3)

| Service | Type | Layer | Role | Charnière | Critical | Native |
|---------|------|-------|------|-----------|----------|--------|
| **backend** | internal | docker | FastAPI app, business logic, API endpoints | 🔗 | ⚡ | ⚠️ |
| **frontend** | internal | docker | Next.js 15 UI, React 19 chat interface | 🔗 | - | ✅ |
| **nginx** | internal | docker | Reverse proxy, static assets | 🔗 | ⚡ | ✅ |

#### backend

**ID:** `backend`
**Type:** internal
**Layers:** docker (native: ⚠️ possible with effort)
**Role:** FastAPI application serving REST API, WebSocket, workflow engine

**Entrypoint:**
- Docker: `layra-backend` container, port 8000
- Native: `cd backend && gunicorn -c gunicorn_config.py app.main:app`

**Dependencies:**
- Hard: mysql, redis, mongodb, kafka, minio, milvus-standalone
- Soft: unoserver

**Ports:** 8000 (internal), exposed via nginx:8090

**Environment (Required):**
```bash
DB_URL=mysql+asyncmy://layra:password@mysql:3306/layra_db
REDIS_URL=redis:6379
REDIS_PASSWORD=password
MONGODB_URL=mongodb://user:pass@mongodb:27017
MONGODB_DB=chat_mongodb  # Database name for model_config, conversations
KAFKA_BROKER_URL=kafka:9094
MINIO_URL=http://minio:9000
MINIO_ACCESS_KEY=key
MINIO_SECRET_KEY=secret
SECRET_KEY=jwt_secret_key
MILVUS_URI=http://milvus-standalone:19530
```

**Health Check:**
```bash
curl http://localhost:8000/api/v1/health/check
# Or via nginx:
curl http://localhost:8090/api/v1/health/check
```

**Native Feasibility:** ⚠️ **Possible with effort**

**Requirements:**
- Python 3.10+
- System packages: `poppler-utils git curl netcat-openbsd fonts-noto-cjk`
- Python packages: see `backend/requirements.txt`

**Blockers:**
1. Docker socket access (`/var/run/docker.sock`) for sandbox execution
2. Hardcoded container hostnames (e.g., `mysql:3306`)

**Fixes:**
1. Replace Docker SDK with subprocess for sandbox spawning
2. Update all hostnames to `localhost` when running native
3. Install system dependencies via apt

**Evidence:**
- `docker-compose.yml:242-323`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/app/main.py`

---

#### frontend

**ID:** `frontend`
**Type:** internal
**Layers:** docker (native: ✅ highly feasible)
**Role:** Next.js 15 web application for user interface

**Entrypoint:**
- Docker: `layra-frontend` container, port 3000
- Native: `cd frontend && npm install && npm run build && npm start`

**Dependencies:**
- Hard: backend

**Ports:** 3000 (internal), exposed via nginx:8090

**Environment (Required):**
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090/api/v1
```

**Health Check:**
```bash
curl http://localhost:3000
```

**Native Feasibility:** ✅ **Highly feasible**

**Requirements:**
- Node.js 20+
- npm

**Blockers:**
- API_BASE_URL needs to point to backend location

**Evidence:**
- `docker-compose.yml:357-371`
- `frontend/Dockerfile`
- `frontend/package.json`

---

#### nginx

**ID:** `nginx`
**Type:** internal
**Layers:** docker (native: ✅ highly feasible)
**Role:** Nginx reverse proxy routing traffic to frontend/backend

**Entrypoint:**
- Docker: `layra-nginx` container, port 80
- Native: `nginx -c frontend/nginx.conf`

**Dependencies:**
- Hard: frontend, backend
- Soft: minio

**Ports:** 80 (internal), 8090 (external)

**Environment:** None

**Health Check:**
```bash
curl http://localhost:8090
```

**Native Feasibility:** ✅ **Highly feasible**

**Requirements:**
- nginx package

**Blockers:**
- Upstream addresses need updating (`frontend:3000` → `localhost:3000`)

**Evidence:**
- `docker-compose.yml:373-384`
- `frontend/nginx.conf`

---

### Data Storage Services (5)

| Service | Type | Layer | Role | Stateful | Native |
|---------|------|-------|------|----------|--------|
| **mysql** | container | docker | Relational DB: users, auth, metadata | 🔒 | ⚠️ |
| **mongodb** | container | docker | NoSQL DB: chat, workflows | 🔒 | ⚠️ |
| **redis** | container | docker | Cache, queue, locks | 🔒 | ✅ |
| **minio** | container | docker | Object storage: documents | 🔒 | ⚠️ |
| **milvus-standalone** | container | docker | Vector DB: embeddings | 🔒 | 🐳 |


#### mysql

**ID:** `mysql`
**Type:** container
**Layers:** docker (native: ⚠️ feasible, external: possible)
**Role:** Relational database for users, authentication, metadata

**Entrypoint:**
- Docker: `mysql:8.0` image, port 3306
- Native: `systemctl start mysql`
- External: AWS RDS, Google Cloud SQL, Azure Database for MySQL

**Dependencies:** None

**Persistence:** `mysql_data` volume (CRITICAL to backup)

**Environment (Required):**
```bash
MYSQL_ROOT_PASSWORD=root_password
MYSQL_DATABASE=layra_db
MYSQL_USER=layra
MYSQL_PASSWORD=layra_password
```

**Health Check:**
```bash
docker exec layra-mysql mysqladmin ping -h localhost
```

**Native Feasibility:** ⚠️ **Feasible with effort**

**Requirements:**
- mysql-server package

**Blockers:**
1. Data migration from Docker volume
2. Port 3306 may conflict with existing MySQL

**Migration:**
```bash
# Export from Docker
docker exec layra-mysql mysqldump -u root -p layra_db > backup.sql

# Import to native
mysql -u root -p layra_db < backup.sql
```

**Evidence:**
- `docker-compose.yml:96-112`

---

#### mongodb

**ID:** `mongodb`
**Type:** container
**Layers:** docker (native: ⚠️ feasible, external: possible)
**Role:** NoSQL database for chat history, workflow state

**Entrypoint:**
- Docker: `mongo:7.0.12` image, port 27017
- Native: `systemctl start mongod`
- External: MongoDB Atlas, AWS DocumentDB

**Dependencies:** None

**Persistence:** `mongo_data` volume (CRITICAL to backup)

**Environment (Required):**
```bash
MONGODB_INITDB_ROOT_USERNAME=admin
MONGODB_INITDB_ROOT_PASSWORD=admin_password
MONGODB_DB=chat_mongodb  # Application database name
```

**Health Check:**
```bash
docker exec layra-mongodb mongosh --eval "db.adminCommand('ping')"
```

**Native Feasibility:** ⚠️ **Feasible with effort**

**Requirements:**
- mongodb package

**Blockers:**
- Data migration from volume

**Migration:**
```bash
# Export from Docker
docker exec layra-mongodb mongodump --archive=backup.archive

# Import to native
mongorestore --archive=backup.archive
```

**Evidence:**
- `docker-compose.yml:66-80`

---

#### redis

**ID:** `redis`
**Type:** container
**Layers:** docker (native: ✅ highly feasible, external: possible)
**Role:** Cache, task queue, distributed locks, session storage

**Entrypoint:**
- Docker: `redis:7.2.5` image, port 6379
- Native: `redis-server --requirepass password`
- External: AWS ElastiCache, Google Cloud Memorystore

**Dependencies:** None

**Persistence:** `redis_data` volume (low importance - cache)

**Environment (Required):**
```bash
REDIS_PASSWORD=redis_password
```

**Health Check:**
```bash
docker exec layra-redis redis-cli -a password ping
# Should return: PONG
```

**Native Feasibility:** ✅ **Highly feasible**

**Requirements:**
- redis-server package

**Blockers:** None

**Evidence:**
- `docker-compose.yml:82-94`

---

#### minio

**ID:** `minio`
**Type:** container
**Layers:** docker (native: ⚠️ feasible, external: possible)
**Role:** S3-compatible object storage for documents, images

**Entrypoint:**
- Docker: `minio/minio` image, port 9000
- Native: `minio server /data --console-address :9001`
- External: AWS S3, Google Cloud Storage, Azure Blob Storage

**Dependencies:** None

**Persistence:** `minio_data` volume (CRITICAL to backup)

**Environment (Required):**
```bash
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=minio_password
```

**Health Check:**
```bash
curl http://localhost:9000/minio/health/live
```

**Native Feasibility:** ⚠️ **Feasible with effort**

**Requirements:**
- minio package

**Blockers:**
- Console port (9001) configuration
- Data migration

**Evidence:**
- `docker-compose.yml:49-64`

---

#### milvus-standalone

**ID:** `milvus-standalone`
**Type:** container
**Layers:** docker (native: 🐳 difficult, external: possible)
**Role:** Vector database for visual embeddings (ColQwen2.5)

**Entrypoint:**
- Docker: `milvusdb/milvus:v2.6.9` image, port 19530
- External: Zilliz Cloud (managed Milvus)

**Dependencies:**
- Hard: milvus-etcd, milvus-minio

**Persistence:** `milvus_data` volume (medium importance - can re-ingest)

**Environment (Required):**
```bash
ETCD_ENDPOINTS=milvus-etcd:2379
MINIO_ADDRESS=milvus-minio:9000
```

**Health Check:**
```bash
docker exec layra-milvus-standalone curl http://localhost:9091/healthz
```

**Native Feasibility:** 🐳 **Difficult - NOT recommended**

**Requirements:**
- Milvus standalone compilation
- etcd service
- MinIO service

**Blockers:**
1. Complex dependency chain (etcd + minio)
2. No official native install packages
3. Requires coordination service

**Alternatives:**
1. Keep in Docker (recommended)
2. Use Zilliz Cloud (managed)
3. Switch to Qdrant (has native binary)

**Evidence:**
- `docker-compose.yml:171-194`

---

#### qdrant

**ID:** `qdrant`
**Type:** container
**Layers:** docker (native: ✅ feasible)
**Role:** Alternative vector database (inactive, VECTOR_DB=milvus by default)

**Entrypoint:**
- Docker: `qdrant/qdrant:v1.16.2` image, port 6333
- Native: Download binary from GitHub releases

**Dependencies:** None

**Persistence:** `qdrant_data` volume

**Environment (Required):**
```bash
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__METRICS_PORT=6334
```

**Health Check:**
```bash
curl http://localhost:6333/healthz
```

**Native Feasibility:** ✅ **Feasible**

**Requirements:**
- Download qdrant binary
- Systemd service setup

**Blockers:**
- Not active in default config

**Evidence:**
- `docker-compose.yml:114-132`

---

### Infrastructure Services (3)

| Service | Type | Layer | Role | Native |
|---------|------|-------|------|--------|
| **kafka** | container | docker | Event bus for async tasks | 🐳 |
| **kafka-init** | internal | docker | Kafka topic initialization | ✅ |
| **unoserver** | container | docker | Document conversion | 🐳 |

#### kafka

**ID:** `kafka`
**Type:** container
**Layers:** docker (native: 🐳 complex, external: possible)
**Role:** Event bus for async task processing

**Entrypoint:**
- Docker: `apache/kafka:3.8.0` image, port 9094
- Native: `kafka-server-start /etc/kafka/server.properties`
- External: AWS MSK, Confluent Cloud, Google Pub/Sub

**Dependencies:** None

**Persistence:** `kafka_data` volume

**Environment (Required):**
```bash
KAFKA_NODE_ID=0
KAFKA_PROCESS_ROLES=controller,broker
KAFKA_CONTROLLER_QUORUM_VOTERS=0@kafka:9093
```

**Health Check:**
```bash
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

**Native Feasibility:** 🐳 **Complex - NOT recommended**

**Requirements:**
- Java runtime
- Kafka installation
- ZooKeeper (or KRaft mode)

**Blockers:**
- Complex configuration
- Requires Java/ZooKeeper

**Evidence:**
- `docker-compose.yml:17-47`

---

#### kafka-init

**ID:** `kafka-init`
**Type:** internal
**Layers:** docker (native: ✅ highly feasible)
**Role:** Initialize Kafka topics on startup

**Entrypoint:**
- Docker: `layra-kafka-init` image (one-shot)
- Native: `bash init-kafka/init-kafka.sh`

**Dependencies:**
- Hard: kafka

**Environment (Required):**
```bash
KAFKA_TOPIC=task_generation
KAFKA_PARTITIONS_NUMBER=10
KAFKA_REPLICATION_FACTOR=1
```

**Native Feasibility:** ✅ **Highly feasible**

**Evidence:**
- `docker-compose.yml:3-15`
- `init-kafka/init-kafka.sh`

---

#### unoserver

**ID:** `unoserver`
**Type:** container
**Layers:** docker (native: ⚠️ possible)
**Role:** Document conversion (DOCX, XLSX, PPTX → PDF)

**Entrypoint:**
- Docker: `layra-unoserver` image, port 2003
- Native: `python3 -m unoserver.server --port=2003`

**Dependencies:** None

**Environment (Required):**
```bash
UNOSERVER_INSTANCES=1
BASE_PORT=2003
BASE_UNO_PORT=3003
```

**Health Check:**
```bash
docker exec layra-unoserver nc -z localhost 2003
```

**Native Feasibility:** ⚠️ **Possible but complex**

**Requirements:**
- LibreOffice suite
- Python unoserver package
- Headless X11

**Blockers:**
- Requires full LibreOffice installation
- Headless X11 setup
- Font dependencies (CJK fonts)

**Evidence:**
- `docker-compose.yml:225-240`
- `unoserver/Dockerfile`

---

### RAG Chat & Models System (Verified Operational)

**Embedding Configuration:**
- **Primary Mode**: `local_colqwen` (GPU-based ColQwen2.5-v0.2, ~15GB model)
- **Alternative Mode**: `jina_embeddings_v4` (cloud API, no GPU required)
- **Dual Support**: Seamless switching via `EMBEDDING_MODEL` environment variable
- **Circuit Breaker**: Protects embedding service from cascading failures

**LLM Provider System:**
- **8 Providers Supported**: OpenAI, DeepSeek, Moonshot/Kimi, Zhipu/GLM, MiniMax, Cohere, Ollama, Anthropic, Google Gemini
- **Provider Selection**: Automatic based on model name prefix
- **Model Configuration**: MongoDB-based storage per user
- **Unified Chat Service**: Single service (417 lines) handles both RAG and workflow modes
- **Parameter Normalization**: Safe clamping for temperature (0.0-1.0), max_length (1024-1048576), top_p (0.0-1.0), top_k (3-30), score_threshold (0-20)

**Model Configuration Parameters:**
```python
{
  "model_id": "unique_id",
  "model_name": "Display Name",
  "model_url": "https://api.provider.com/v1/chat/completions",
  "llm_provider": "openai|deepseek|moonshot|zhipu|minimax|cohere|ollama|anthropic|google",
  "api_key": "provider_api_key",
  "base_used": ["provider"],
  "system_prompt": "Custom instructions...",
  "temperature": 0.7,  # Sampling randomness
  "max_length": 4096,  # Token limit
  "top_P": 1.0,  # Nucleus sampling
  "top_K": 5,  # Retrieval count
  "score_threshold": 10.0  # RAG confidence filter
}
```

| Service | Type | Layer | Role | Native |
|---------|------|-------|------|--------|
| **model-server** | internal | docker | ColQwen visual embedding server | ⚠️ (GPU) |
| **model-weights-init** | internal | docker | Download ML model weights | ✅ |

#### model-server

**ID:** `model-server`
**Type:** internal
**Layers:** docker (native: ⚠️ possible with GPU)
**Role:** Local visual embedding server (ColQwen2.5)

**Entrypoint:**
- Docker: `layra-model-server` image, port 8005
- Native: `cd model-server && python model_server.py`

**Dependencies:**
- Hard: model-weights-init
- Soft: redis

**Environment (Required):**
```bash
CUDA_VISIBLE_DEVICES=0
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
REDIS_HOST=redis
REDIS_PASSWORD=password
```

**Health Check:**
```bash
curl http://localhost:8005/healthy-check
```

**Native Feasibility:** ⚠️ **Possible with GPU**

**Requirements:**
- NVIDIA GPU with CUDA
- CUDA Toolkit 12.4
- Python 3.10 with PyTorch
- Model weights (~15GB)

**Blockers:**
- Requires NVIDIA GPU + CUDA
- Large model download
- GPU memory management

**Evidence:**
- `docker-compose.yml:325-355`
- `model-server/Dockerfile`

---

#### model-weights-init

**ID:** `model-weights-init`
**Type:** internal
**Layers:** docker (native: ✅ highly feasible)
**Role:** Download ML model weights on first startup

**Entrypoint:**
- Docker: `layra-model-weights-init` image (one-shot)
- Native: `bash init-db/init_models.sh`

**Dependencies:** None

**Persistence:** `model_weights` volume

**Environment (Required):**
```bash
MODEL_BASE_URL=https://huggingface.co/vidore
```

**Native Feasibility:** ✅ **Highly feasible**

**Requirements:**
- git
- git-lfs
- jq

**Blockers:**
- Large download (~15GB)

**Evidence:**
- `docker-compose.yml:207-223`
- `init-db/init_models.sh`

---

### Execution Environment (1)

| Service | Type | Layer | Role | Native |
|---------|------|-------|------|--------|
| **python-sandbox** | internal | docker | Isolated Python execution | ❌ |

#### python-sandbox

**ID:** `python-sandbox`
**Type:** internal
**Layers:** docker (native: ❌ NOT recommended)
**Role:** Isolated Python code execution for workflows

**Entrypoint:**
- Docker: `python-sandbox` image

**Dependencies:** None

**Persistence:** `layra_sandbox_volume` shared volume

**Native Feasibility:** ❌ **NOT recommended - Security risk**

**Requirements:**
- Python 3.12

**Blockers:**
- **SECURITY**: Running user code on host
- No isolation
- Full file system access

**Alternatives:**
- Keep in Docker (essential for security)
- Use firecracker VMs
- Use gvisor

**Evidence:**
- `docker-compose.yml:197-205`
- `sandbox/Dockerfile`

---

### Monitoring Services (3)

| Service | Type | Layer | Role | Native |
|---------|------|-------|------|--------|
| **prometheus** | container | docker | Metrics collection | ✅ |
| **grafana** | container | docker | Visualization dashboards | ✅ |
| **dozzle** | container | docker | Log viewer | N/A |

#### prometheus

**ID:** `prometheus`
**Type:** container
**Layers:** docker (native: ✅ feasible)
**Role:** Metrics collection and monitoring

**Entrypoint:**
- Docker: `prom/prometheus:latest` image, port 9090
- Native: `prometheus --config.file=/etc/prometheus/prometheus.yml`

**Dependencies:** None

**Persistence:** `prometheus_data` volume

**Native Feasibility:** ✅ **Feasible**

**Evidence:**
- `docker-compose.yml:386-399`
- `monitoring/prometheus.yml`

---

#### grafana

**ID:** `grafana`
**Type:** container
**Layers:** docker (native: ✅ feasible)
**Role:** Visualization dashboards for metrics

**Entrypoint:**
- Docker: `grafana/grafana:latest` image, port 3000
- Native: `grafana-server --config=/etc/grafana/grafana.ini`

**Dependencies:**
- Soft: prometheus

**Persistence:** `grafana_data` volume

**Environment (Optional):**
```bash
GF_SECURITY_ADMIN_PASSWORD=admin
```

**Native Feasibility:** ✅ **Feasible**

**Evidence:**
- `docker-compose.yml:401-413`

---

#### dozzle

**ID:** `dozzle`
**Type:** container
**Layers:** docker only
**Role:** Real-time container log viewer (development only)

**Entrypoint:**
- Docker: `amir20/dozzle:latest` image, port 8080

**Dependencies:**
- Hard: `/var/run/docker.sock` (Docker socket mount)

**Native Feasibility:** N/A (Docker-specific tool)

**Evidence:**
- `docker-compose.override.yml:18-26`

---

### Milvus Support Services (2)

| Service | Type | Layer | Role | Native |
|---------|------|-------|------|--------|
| **milvus-etcd** | container | docker | Service discovery for Milvus | 🐳 |
| **milvus-minio** | container | docker | Milvus internal storage | ⚠️ |

#### milvus-etcd

**ID:** `milvus-etcd`
**Type:** container
**Layers:** docker (native: 🐳 difficult)
**Role:** Service discovery for Milvus (coordination)

**Entrypoint:**
- Docker: `quay.io/coreos/etcd:v3.5.18` image, port 2379

**Dependencies:** None

**Persistence:** `milvus_etcd` volume

**Native Feasibility:** 🐳 **Difficult**

**Blockers:**
- Only needed for Milvus
- Complex setup

**Evidence:**
- `docker-compose.yml:135-152`

---

#### milvus-minio

**ID:** `milvus-minio`
**Type:** container
**Layers:** docker (native: ⚠️ not recommended)
**Role:** Internal object storage for Milvus

**Entrypoint:**
- Docker: `minio/minio:RELEASE.2023-03-20T20-16-18Z` image, port 9000

**Dependencies:** None

**Persistence:** `milvus_minio` volume

**Native Feasibility:** ⚠️ **Not recommended - duplicate of main MinIO**

**Blockers:**
- Duplicate of main MinIO
- Could consolidate with main MinIO

**Evidence:**
- `docker-compose.yml:154-169`

---

## Critical Paths (E2E)

### Query Path (RAG)

**Description:** User asks question → retrieval → generation → response

```
User (Frontend)
  ↓ POST /api/v1/chat
Backend (app/api/endpoints/chat.py)
  ↓
MongoDB (fetch chat history)
  ↓
Milvus (semantic search with query embedding)
  ├─→ model-server (local) OR
  └─→ Jina API (remote)
  ↓
MinIO (retrieve stored document images)
  ↓
LLM Provider API (generate response with context)
  ├─→ OpenAI (gpt-4o-mini)
  ├─→ DeepSeek (deepseek-chat)
  ├─→ Moonshot (kimi-k2-thinking)
  └─→ Zhipu (glm-4.7)
  ↓
Backend (stream response via SSE)
  ↓
Frontend (render markdown)
```

**Services Required:**
- frontend, backend, mongodb, milvus, minio
- Optional: model-server (if EMBEDDING_MODEL=local_colqwen)
- External: LLM provider API

**Path Code:**
- Entry: `backend/app/api/endpoints/chat.py`
- Embedding: `backend/app/rag/get_embedding.py`
- Search: `backend/app/db/milvus.py`
- Generation: `backend/app/rag/llm_service.py`

---

### Ingest Path

**Description:** User uploads document → processing → embedding → indexing

```
User (Frontend)
  ↓ POST /api/v1/knowledge-base/upload
Backend (app/api/endpoints/knowledge-base.py)
  ↓
MinIO (store original file)
  ↓
Unoserver (convert DOCX/XLSX/PPTX → PDF)
  ↓
Backend (PDF → images via pdf2image)
  ├─→ app/rag/convert_file.py
  ↓
Visual Embedding Generation
  ├─→ model-server (ColQwen2.5, local) OR
  └─→ Jina API (remote)
  ↓
Milvus (store embeddings with metadata)
  ↓
MySQL (store document metadata)
  ↓
Kafka (async processing notification)
```

**Services Required:**
- backend, minio, unoserver, milvus, mysql, kafka
- Optional: model-server (if EMBEDDING_MODEL=local_colqwen)
- External: Jina API (if EMBEDDING_MODEL=jina_embeddings_v4)

**Path Code:**
- Entry: `backend/app/api/endpoints/knowledge-base.py`
- Conversion: `backend/app/rag/convert_file.py`
- Embedding: `backend/app/rag/get_embedding.py`
- Indexing: `backend/app/db/milvus.py`

---

### Workflow Execution Path

**Description:** User creates workflow → execution → results

```
User (Frontend Workflow Builder)
  ↓ POST /api/v1/workflow/execute
Backend (app/workflow/workflow_engine.py)
  ↓ DAG validation
Kafka (task_generation topic)
  ↓
Backend (workflow orchestrator)
  ↓
Node Execution (app/workflow/executors/)
  ├─→ LLM Node: Call LLM provider
  ├─→ Code Node: Execute Python
  ├─→ Condition Node: Evaluate logic
  └─→ Loop Node: Iterate
  ↓
Python-sandbox (isolated code execution)
  ↓
MongoDB (persist workflow state)
  ↓
Backend (stream updates via SSE)
  ↓
Frontend (display execution progress)
```

**Services Required:**
- frontend, backend, mongodb, kafka, python-sandbox
- External: LLM provider API

**Path Code:**
- Entry: `backend/app/api/endpoints/workflow.py`
- Engine: `backend/app/workflow/workflow_engine.py`
- Executors: `backend/app/workflow/executors/`
- Sandbox: `backend/app/workflow/sandbox.py`

---

### Deploy Path

**Description:** From clean checkout to running system

```
1. git clone repository
2. cp .env.example .env
3. Edit .env with credentials
4. docker network create layra-net (external: true)
5. docker-compose build
   ├─→ backend
   ├─→ frontend
   ├─→ unoserver
   ├─→ model-server
   └─→ python-sandbox
6. Start infrastructure services
   ├─→ mysql
   ├─→ mongodb
   ├─→ redis
   ├─→ minio
   ├─→ milvus-standalone
   └─→ kafka
7. model-weights-init (download ~15GB models, 10-30 min)
8. kafka-init (create topics)
9. Start app services
   ├─→ unoserver
   ├─→ backend
   ├─→ frontend
   └─→ nginx
10. Verify: curl http://localhost:8090/api/v1/health/check
```

**Prerequisites:**
- Docker, Docker Compose
- Optional: NVIDIA Container Toolkit (for GPU)
- External: HuggingFace (model download), LLM provider API keys

---

## External Dependencies

### LLM Providers

**Integration:** Direct API calls via `backend/app/rag/provider_client.py`

| Provider | Base URL | Env Key | Status | Models |
|----------|----------|---------|--------|--------|
| OpenAI | https://api.openai.com/v1 | OPENAI_API_KEY | ✅ Required | gpt-4o, gpt-4o-mini |
| DeepSeek | https://api.deepseek.com | DEEPSEEK_API_KEY | ✅ Required | deepseek-chat, deepseek-coder |
| Moonshot (Kimi) | https://api.moonshot.cn/v1 | MOONSHOT_API_KEY | Optional | moonshot-v1-8k, kimi-k2-thinking |
| Zhipu (GLM) | https://open.bigmodel.cn/api/paas/v4 | ZHIPUAI_API_KEY | Optional | glm-4, glm-4-flash, glm-4-plus |
| **Zhipu Coding** | https://open.bigmodel.cn/api/coding/paas/v4 | ZHIPUAI_API_KEY | Optional | glm-4.5, glm-4.6, glm-4.7 |
| MiniMax | https://api.minimax.chat/v1 | MINIMAX_API_KEY | Optional | abab5.5-chat |
| Cohere | https://api.cohere.ai/v1 | COHERE_API_KEY | Optional | command-r |
| Ollama | https://api.ollama.ai/v1 | OLLAMA_API_KEY | Optional | llama3, mistral |
| Anthropic | https://api.anthropic.com/v1 | ANTHROPIC_API_KEY | Optional | claude-3-opus |
| Google Gemini | https://generativelanguage.googleapis.com/v1 | GEMINI_API_KEY | Optional | gemini-pro |

**Provider Selection:** Automatic based on model name prefix
- `gpt-*` → OpenAI
- `deepseek-*` → DeepSeek
- `kimi-*` or `moonshot-*` → Moonshot
- `glm-4.5*`, `glm-4.6*`, `glm-4.7*` → **Zhipu Coding Plan**
- `glm-*` or `zhipu-*` → Zhipu (Regular)
- `abab*` or `minimax-*` → MiniMax
- `command*` or `cohere-*` → Cohere
- `llama*`, `mistral*`, `mixtral*` → Ollama
- `claude-*` → Anthropic
- `gemini-*` → Google

**Note:** Zhipu Coding Plan requires separate subscription. JWT authentication (id.secret format) required.

---

### Embedding Models

**Local (GPU Required):**
- **Model:** ColQwen2.5-v0.2
- **Path:** /model_weights/colqwen2.5-v0.2
- **Size:** ~15GB
- **DPI:** 200 (configurable via EMBEDDING_IMAGE_DPI)
- **Service:** model-server
- **Environment:** `EMBEDDING_MODEL=local_colqwen`

**Remote (No GPU):**
- **Provider:** Jina AI
- **API:** https://api.jina.ai/v1/embeddings
- **Key:** `JINA_API_KEY`
- **Environment:** `EMBEDDING_MODEL=jina_embeddings_v4`

---

### Model Weights Download

**Source:** HuggingFace Model Hub
- **URL:** https://huggingface.co/vidore
- **Mirror:** Configurable via `MODEL_BASE_URL`
- **Models:**
  - colqwen2.5-base (~8GB)
  - colqwen2.5-v0.2 (~7GB)
- **Tool:** git + git-lfs
- **Init:** `init-db/init_models.sh`

---

## Drift Radar

### Known Gaps (Drift Detection)

#### ✅ docker-compose.yml vs .env.example
**Status:** Verified
**Last Checked:** 2026-01-26
**Notes:** All environment variables in compose are defined in .env.example

---

#### ⚠️ Backend Config vs .env.example
**Status:** Drift Detected
**Issue:** Case mismatch between `config.py` and `.env.example`
**Details:**
- `config.py` defines: `milvus_uri`, `qdrant_url`, `vector_db`
- `.env.example` has: `MILVUS_URI`, `QDRANT_URL`, `VECTOR_DB`
- **Impact:** Pydantic auto-lowercases env vars, but docs inconsistent
**Evidence:**
- `backend/app/core/config.py:56-65`
- `.env.example:58, 127`

**Fix:** Update `.env.example` to match Pydantic expectations (lowercase)

---

#### ⚠️ README vs Actual Compose Files
**Status:** Drift Detected
**Issue:** Docs referenced a missing thesis compose file
**Details:**
- `docker-compose.gpu.yml` - Moved to `deploy/docker-compose.gpu.yml`
- `docker-compose-no-local-embedding.yml` - Archived to `scripts/archive/docker-compose/`
- `docker-compose.backup.yml` - Archived to `scripts/archive/docker-compose/`
- **Actual active:** `docker-compose.yml` (plus optional `docker-compose.override.yml`)
- **Impact:** Confusing deployment guidance until docs are aligned
**Evidence:**
- `README.md:386-389` (correctly references active files)
- See `deploy/DOCKER_COMPOSE_GUIDE.md` for usage
- See `scripts/archive/docker-compose/README.md` for archived file history

**Fix:** Update deployment docs to remove thesis compose references

---

#### ⚠️ Frontend API URL Configuration
**Status:** Drift Detected
**Issue:** Frontend build-time vs runtime configuration
**Details:**
- `NEXT_PUBLIC_API_BASE_URL` is build-time arg in Dockerfile
- nginx routes `/api/` to backend, but frontend may have hardcoded URL
- **Impact:** If backend URL changes, frontend needs rebuild
**Evidence:**
- `frontend/Dockerfile:7-8`
- `frontend/nginx.conf:38-49`

**Fix:** Use relative URLs or runtime config

---

### Configuration Drift Prevention

**Weekly Check:**
```bash
# Compare running containers with SSOT
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep layra

# Verify environment variables
docker exec layra-backend env | grep -E "(DB_URL|MONGODB_URL|KAFKA_BROKER_URL)"

# Check for orphaned volumes
docker volume ls -f name=layra
```

---

## Update Protocol

### Triggers (When to Update SSOT)

Update this document when:
- ✅ Adding or removing a service
- ✅ Changing service versions
- ✅ Modifying ports or network topology
- ✅ Adding new environment variables
- ✅ Changing data flow between services
- ✅ Switching vector database (milvus <-> qdrant)
- ✅ Changing embedding mode (local <-> jina)

---

### PR Checklist

Before submitting PR that changes architecture:
1. [ ] Update `docs/ssot/stack.md`
2. [ ] Update `docs/ssot/stack.yaml`
3. [ ] Update `docker-compose.yml` (or variant)
4. [ ] Update `.env.example`
5. [ ] Verify `README.md` matches actual files
6. [ ] Add migration guide (if breaking change)

---

### Verification Steps

After updating SSOT:
1. [ ] Compare this document with `docker-compose.yml`
2. [ ] Verify all env vars exist in `.env.example`
3. [ ] Check service count matches `docker ps`
4. [ ] Test critical paths (query, ingest, workflow)
5. [ ] Update version number at top of document

---

## Changelog

### Version 3.0.0 (2026-01-26)

**Major Restructure:**
- Complete rewrite with native deployment feasibility assessment
- Added layering analysis (docker/native/external)
- Added critical paths documentation
- Added drift detection section
- Categorized services by deployment complexity
- Created machine-readable `stack.yaml`

**New Sections:**
- Run Modes with layering
- Service Registry with native feasibility
- Critical Paths (query, ingest, workflow, deploy)
- External Dependencies (LLM providers, embeddings)
- Drift Radar with known gaps
- Update Protocol

---

### Version 2.0.0 (2026-01-25)

**Changes:**
- Initial markdown SSOT
- Documented 13 services
- Added environment variables
- Added resource requirements

---

## Appendix

### Service Count Summary

| Category | Count |
|----------|-------|
| Application Services | 3 |
| Data Storage | 6 |
| Infrastructure | 3 |
| Model & Inference | 2 |
| Execution | 1 |
| Monitoring | 3 |
| Milvus Support | 2 |
| **Total** | **20** (16 active in default mode) |

---

### Native Deployment Feasibility Summary

| Feasibility | Count | Services |
|-------------|-------|----------|
| ✅ Highly Feasible | 6 | frontend, nginx, redis, model-weights-init, kafka-init, prometheus, grafana, qdrant |
| ⚠️ Feasible with Effort | 5 | backend, mysql, mongodb, minio, unoserver, model-server (with GPU) |
| 🐳 Difficult/Not Recommended | 4 | milvus-standalone, kafka, milvus-etcd, python-sandbox |
| N/A | 1 | dozzle (Docker-specific) |

**Overall Assessment:** Partial native deployment possible, but Docker remains recommended for most services

---

**END OF SSOT v3.0.0**

*Maintained by: System*
*Last Updated: 2026-01-26*
*Next Review: 2026-02-02*

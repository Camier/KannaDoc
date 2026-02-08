# LAYRA Configuration Reference

**Version**: 2.0.0
**Last Updated**: 2026-01-26  

---

## Overview

LAYRA uses environment variables for configuration. Copy `.env.example` to `.env` and customize for your deployment.

```bash
cp .env.example .env
# Edit .env with your configuration
```

---

## Configuration Variables

### Server Configuration

#### SERVER_IP
- **Default**: `http://localhost:8090`
- **Purpose**: Application server URL for presigned URLs
- **Production**: Use domain name (e.g., `https://api.example.com`)
- **Example**: `SERVER_IP=https://api.layra.ai`

#### DEBUG_MODE
- **Type**: Boolean (`true` | `false`)
- **Default**: `false`
- **Purpose**: Enable debug logging and features
- **Effects**:
  - SQLAlchemy echo enabled (logs all SQL queries)
  - Longer stack traces in errors
  - Hot reloading enabled (development)
  - CORS allow all origins (development)
- **Production**: Always set to `false`

#### LOG_LEVEL
- **Type**: Enum
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default**: `INFO`
- **Development**: `DEBUG`
- **Production**: `INFO`

#### MAX_WORKERS
- **Type**: Integer
- **Default**: `4`
- **Purpose**: Number of async workers
- **Calculation**: 
  - CPU-bound: `num_cores`
  - I/O-bound: `num_cores * 2-4`
  - Recommended: `4-8`

---

### Authentication

#### SECRET_KEY
- **Type**: String
- **Default**: Generated random
- **Purpose**: Secret key for JWT signing
- **Format**: 32+ random characters
- **Security**: NEVER hardcode in production
- **Generation**:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

#### ALGORITHM
- **Type**: String
- **Default**: `HS256`
- **Purpose**: JWT signing algorithm
- **Options**: `HS256`, `RS256`
- **Recommendation**: Keep `HS256` (symmetric)

#### ACCESS_TOKEN_EXPIRE_MINUTES
- **Type**: Integer
- **Default**: `11520` (8 days)
- **Purpose**: JWT token expiration time
- **Units**: Minutes
- **Common Values**:
  - Development: `1440` (1 day)
  - Production: `11520` (8 days)
  - Short-lived: `60` (1 hour)

---

### Redis Configuration

#### REDIS_URL
- **Type**: String (connection string)
- **Format**: `redis://host:port`
- **Default**: `redis:6379`
- **Production**: `redis://redis.internal:6379`
- **Example**: `REDIS_URL=redis://redis.example.com:6379`

#### REDIS_PASSWORD
- **Type**: String
- **Default**: Generated random
- **Purpose**: Redis authentication
- **Security**: Use strong password in production
- **Recommendation**: 32+ random characters

#### REDIS_TOKEN_DB
- **Type**: Integer (0-15)
- **Default**: `0`
- **Purpose**: JWT token storage
- **Note**: DO NOT share with other apps

#### REDIS_TASK_DB
- **Type**: Integer (0-15)
- **Default**: `1`
- **Purpose**: Task progress tracking

#### REDIS_LOCK_DB
- **Type**: Integer (0-15)
- **Default**: `2`
- **Purpose**: Distributed locks

---

### MongoDB Configuration

#### MONGODB_URL
- **Type**: String (connection string)
- **Format**: `mongodb://host:port`
- **Default**: `mongodb:27017`
- **Authentication**: `mongodb://user:pass@host:port`
- **Example**: `MONGODB_URL=mongodb://mongo.internal:27017`

#### MONGODB_ROOT_USERNAME
- **Type**: String
- **Default**: Auto-generated
- **Purpose**: MongoDB admin user

#### MONGODB_ROOT_PASSWORD
- **Type**: String
- **Default**: Auto-generated
- **Security**: Use strong password in production

#### MONGODB_DB
- **Type**: String (database name)
- **Default**: `chat_mongodb`
- **Purpose**: Default database for conversations
- **Note**: Must exist or auto-create enabled

#### MONGODB_POOL_SIZE
- **Type**: Integer
- **Default**: `50`
- **Purpose**: Max connections in pool
- **Tuning**:
  - Small deployments: `10-20`
  - Medium: `50`
  - Large: `100+`

#### MONGODB_MIN_POOL_SIZE
- **Type**: Integer
- **Default**: `5`
- **Purpose**: Min connections to maintain

---

### MySQL Configuration

#### MYSQL_ROOT_PASSWORD
- **Type**: String
- **Default**: Auto-generated
- **Purpose**: MySQL root password
- **Security**: Change immediately in production

#### MYSQL_DATABASE
- **Type**: String
- **Default**: `layra_db`
- **Purpose**: Application database name

#### MYSQL_USER
- **Type**: String
- **Default**: `layra_user`
- **Purpose**: Application database user

#### MYSQL_PASSWORD
- **Type**: String
- **Default**: Auto-generated
- **Purpose**: Application database password
- **Security**: Use strong password in production

#### DB_URL
- **Type**: String (SQLAlchemy connection string)
- **Format**: `mysql+asyncmy://user:pass@host:port/dbname`
- **Default**: `mysql+asyncmy://layra_user:pass@mysql:3306/layra_db`
- **Example**: `DB_URL=mysql+asyncmy://layra:secure_pass@db.internal:3306/layra_prod`

#### DB_POOL_SIZE
- **Type**: Integer
- **Default**: `10`
- **Purpose**: Base connection pool size

#### DB_MAX_OVERFLOW
- **Type**: Integer
- **Default**: `20`
- **Purpose**: Additional connections allowed when pool full

---

### Milvus Configuration

#### MILVUS_URI
- **Type**: String (connection string)
- **Format**: `http://host:port`
- **Default**: `http://milvus-standalone:19530`
- **Production**: `http://milvus.internal:19530`
- **Example**: `MILVUS_URI=http://milvus.example.com:19530`

#### HNSW_M
- **Type**: Integer
- **Default**: `48`
- **Range**: 4-64
- **Purpose**: HNSW M parameter for Milvus index construction
- **Note**: Higher values improve recall but increase memory and build time
- **Added**: v2.1.0 (2026-02-02)

#### HNSW_EF_CONSTRUCTION
- **Type**: Integer
- **Default**: `1024`
- **Minimum**: 8
- **Purpose**: HNSW efConstruction parameter for index build quality
- **Note**: Higher values improve index quality but increase build time
- **Added**: v2.1.0 (2026-02-02)

---

### Vector DB Configuration

#### VECTOR_DB
- **Type**: Enum
- **Options**: `milvus`, `qdrant`
- **Default**: `milvus`
- **Purpose**: Vector database backend selection
- **Note**: Qdrant support added in v2.0.0 for multi-vector experiments
- **Migration**: See `docs/vector_db/OVERVIEW.md` for migration guide

#### QDRANT_URL
- **Type**: String (connection string)
- **Format**: `http://host:port`
- **Default**: `http://qdrant:6333`
- **Purpose**: Qdrant connection URL (only if VECTOR_DB=qdrant)
- **Added**: v2.0.0 (2026-01-25)

---

### MinIO Configuration

#### MINIO_URL
- **Type**: String (S3 endpoint)
- **Format**: `http://host:port`
- **Default**: `http://minio:9000`
- **Purpose**: MinIO internal API endpoint for backend services
- **Note**: Used for internal backend-to-MinIO traffic
- **Example**: `MINIO_URL=http://minio.internal:9000`

#### MINIO_PUBLIC_URL
- **Type**: String (S3 endpoint)
- **Format**: `http://host:port` or `https://domain`
- **Default**: `http://localhost:9000`
- **Purpose**: MinIO public endpoint for user downloads (browser-accessible)
- **Critical**: Split-horizon DNS support - differs from MINIO_URL in production
- **Example**: `MINIO_PUBLIC_URL=https://s3.example.com`
- **Added**: v2.0.0 (2026-01-25)

#### MINIO_ACCESS_KEY
- **Type**: String
- **Default**: `thesis_minio`
- **Purpose**: S3 access key (username)
- **Security**: Change in production

#### MINIO_SECRET_KEY
- **Type**: String
- **Default**: Auto-generated
- **Purpose**: S3 secret key (password)
- **Security**: Use strong key (32+ chars)

#### MINIO_BUCKET_NAME
- **Type**: String
- **Default**: `minio-file`
- **Purpose**: S3 bucket name
- **Note**: Must be lowercase, 3-63 chars

#### MINIO_IMAGE_URL_PREFIX
- **Type**: String
- **Default**: `http://localhost:8090/minio-file`
- **Purpose**: Public URL prefix for images
- **Production**: Use CDN or domain
- **Example**: `MINIO_IMAGE_URL_PREFIX=https://cdn.example.com/files`

---

### Kafka Configuration

#### KAFKA_BROKER_URL
- **Type**: String
- **Format**: `host:port`
- **Default**: `kafka:9094`
- **Production**: `kafka.internal:9094`
- **Example**: `KAFKA_BROKER_URL=kafka-0.kafka.default.svc.cluster.local:9094`

#### KAFKA_TOPIC
- **Type**: String
- **Default**: `task_generation`
- **Purpose**: Topic for file processing tasks
- **Note**: Auto-created if doesn't exist

#### KAFKA_PARTITIONS_NUMBER
- **Type**: Integer
- **Default**: `3`
- **Purpose**: Number of partitions
- **Tuning**:
  - Small: `1`
  - Medium: `3`
  - Large: `10+`
  - Rule: `partitions = expected_throughput / max_consumer_throughput`

#### KAFKA_GROUP_ID
- **Type**: String
- **Default**: `task_consumer_group`
- **Purpose**: Consumer group identifier

#### KAFKA_RETRY_BACKOFF_MS
- **Type**: Integer
- **Default**: `5000`
- **Purpose**: Backoff time between retries (ms)
- **Values**: `1000-10000`

#### KAFKA_SESSION_TIMEOUT_MS
- **Type**: Integer
- **Default**: `30000`
- **Purpose**: Consumer session timeout (ms)
- **Values**: `10000-300000`

---

### Embedding Configuration

#### EMBEDDING_MODEL
- **Type**: Enum
- **Options**:
  - `local_colqwen` - Local ColBERT (GPU required)
  - `jina_embeddings_v4` - Jina API (cloud)
- **Default**: `local_colqwen`
- **Performance**:
  - local_colqwen: 1.67 img/s (RTX 4090)
  - jina_embeddings_v4: ~0.5 img/s (API latency)

#### COLBERT_MODEL_PATH
- **Type**: String (filesystem path)
- **Default**: `/model_weights/colqwen2.5-v0.2`
- **Purpose**: Path to ColBERT model weights
- **Note**: Must exist if using `local_colqwen`
- **Download**:
  ```bash
  huggingface-cli download vidore/colqwen2.5-v0.2 \
    --local-dir /model_weights/colqwen2.5-v0.2
  ```

#### MODEL_BASE_URL
- **Type**: String (URL)
- **Default**: `https://hf-mirror.com/vidore` (China mirror)
- **Options**:
  - `https://huggingface.co/vidore` (Official)
  - `https://hf-mirror.com/vidore` (China, faster)
- **Purpose**: Model download source
- **Use**: Set for faster downloads in China

#### EMBEDDING_IMAGE_DPI
- **Type**: Integer
- **Default**: `200`
- **Purpose**: DPI for document-to-image conversion
- **Tuning**:
  - 150: Faster, lower quality
  - 200: Balanced (recommended)
  - 300: Slower, higher quality
  - 400: Very slow, best quality
- **Auto-scaling**: Adapts based on page count
  - <50 pages: 200 DPI
  - 50-100 pages: 200 DPI
  - 100+ pages: 150 DPI (auto-reduce)

#### JINA_API_KEY
- **Type**: String
- **Purpose**: API key for Jina embeddings
- **Only needed if**: `EMBEDDING_MODEL=jina_embeddings_v4`
- **Get key**: https://cloud.jina.ai

---

### Hybrid Search Configuration

**Purpose**: Combines dense (ColQwen) and sparse (BGE-M3) retrieval for improved precision
**Added**: v2.1.0 (2026-02-06)
**Note**: Sparse embeddings require BGE-M3 to be running on the `model-server`

| Variable | Type | Default | Valid Values | Description |
|----------|------|---------|--------------|-------------|
| `RAG_HYBRID_ENABLED` | Boolean | `false` | `true`, `false` | Enable/disable hybrid retrieval mode |
| `RAG_HYBRID_RANKER` | Enum | `rrf` | `rrf`, `weighted` | Strategy to merge dense and sparse results |
| `RAG_HYBRID_RRF_K` | Integer | `60` | `1-100` | RRF smoothing constant (lower = emphasize top ranks) |
| `RAG_HYBRID_DENSE_WEIGHT` | Float | `0.7` | `0.0-1.0` | Weight for dense scores (used if ranker=weighted) |
| `RAG_HYBRID_SPARSE_WEIGHT` | Float | `0.3` | `0.0-1.0` | Weight for sparse scores (used if ranker=weighted) |

#### Usage Examples

**Reciprocal Rank Fusion (RRF)**
Recommended for general use as it is score-invariant and doesn't require weight tuning.
```bash
RAG_HYBRID_ENABLED=true
RAG_HYBRID_RANKER=rrf
RAG_HYBRID_RRF_K=60
```

**Weighted Scoring**
Useful when one retrieval method is significantly more reliable than the other. Weights should ideally sum to 1.0.
```bash
RAG_HYBRID_ENABLED=true
RAG_HYBRID_RANKER=weighted
RAG_HYBRID_DENSE_WEIGHT=0.8
RAG_HYBRID_SPARSE_WEIGHT=0.2
```

---

### LLM Configuration

LLM configuration is stored per user in MongoDB (see `backend/app/db/repositories/model_config.py`).

The backend expects an OpenAI-compatible chat endpoint and explicit credentials:
- `model_name`: label and `model` sent to the OpenAI-compatible API
- `model_url`: base URL for the OpenAI-compatible server (e.g. `https://api.openai.com/v1`)
- `api_key`: API key for that server

There is no `providers.yaml` registry in this fork; the UI/API writes the model configuration directly.

---

### Document Processing

#### UNOSERVER_INSTANCES
- **Type**: Integer
- **Default**: `1`
- **Purpose**: Number of LibreOffice UNO instances
- **Tuning**:
  - Small: `1`
  - Medium: `2-4`
  - Large: `4-8`
  - Formula: `instances = num_cores / 2`

#### UNOSERVER_HOST
- **Type**: String (hostname)
- **Default**: `unoserver`
- **Purpose**: LibreOffice server hostname

#### UNOSERVER_BASE_PORT
- **Type**: Integer
- **Default**: `2003`
- **Purpose**: Starting port for UNO instances
- **Note**: Ports `2003-2003+INSTANCES-1` will be used

#### UNOSERVER_BASE_UNO_PORT
- **Type**: Integer
- **Default**: `3003`
- **Purpose**: Starting port for UNO protocol
- **Note**: Ports `3003-3003+INSTANCES-1` will be used

#### SANDBOX_SHARED_VOLUME
- **Type**: String (filesystem path)
- **Default**: `/app/sandbox_workspace`
- **Purpose**: Shared volume for sandbox execution
- **Permissions**: Must be writable by app container

---

### Circuit Breaker Configuration

**Purpose**: Prevents cascading failures when external services are unavailable
**Implementation**: `backend/app/core/circuit_breaker.py`
**Added**: v2.0.0 (2026-01-25)

Service-specific thresholds (configured in code):
- **Embedding Service**: 5 failures, 60s recovery
- **LLM Service**: 5 failures, 60s recovery
- **Vector DB Service**: 3 failures, 30s recovery
- **MongoDB Service**: 5 failures, 45s recovery

**Usage**: Applied as decorators to external service calls
```python
from app.core.circuit_breaker import embedding_service_circuit

@embedding_service_circuit
async def get_embeddings_from_httpx(...):
    ...
```

---

### Cache Configuration

**Purpose**: Redis caching layer for frequently accessed data
**Implementation**: `backend/app/db/cache.py`
**Added**: v2.0.0 (2026-01-25)

Cache TTL defaults (seconds):
- **Model Config**: 1800 (30 minutes)
- **User Data**: 3600 (1 hour)
- **KB Metadata**: 1800 (30 minutes)
- **Search Results**: 600 (10 minutes)

**Usage**:
```python
from app.db.cache import CacheService

cache = CacheService()
await cache.get_model_config(model_id)
await cache.invalidate_user(user_id)
```

---

### Repository Pattern

**Purpose**: MongoDB repository pattern for data access layer
**Implementation**: `backend/app/db/repositories/`
**Added**: v2.0.0 (2026-01-25)

Available repositories:
- `ModelConfigRepository` - Model configurations
- `ConversationRepository` - Chat conversations
- `KnowledgeBaseRepository` - Knowledge base metadata
- `FileRepository` - File metadata
- `ChatflowRepository` - Chat flow templates
- `WorkflowRepository` - Workflow definitions
- `NodeRepository` - Workflow nodes

**Usage**:
```python
from app.db.repositories import ModelConfigRepository

repo = ModelConfigRepository()
config = await repo.get_by_id(model_id)
```

---

### Frontend Configuration

#### NEXT_PUBLIC_API_BASE_URL
- **Type**: String (URL)
- **Default**: `http://localhost:8090/api/v1`
- **Purpose**: Frontend API endpoint
- **Production**: Use domain (e.g., `https://api.example.com/api/v1`)
- **Note**: `NEXT_PUBLIC_` prefix makes it available in browser

#### NODE_ENV
- **Type**: Enum (`development` | `production`)
- **Default**: `production`
- **Effects**:
  - `development`: Hot reloading, verbose errors
  - `production`: Optimized, minified, error reporting

---

## Deployment Scenarios

### Local Development

```bash
# .env.local
DEBUG_MODE=true
LOG_LEVEL=DEBUG
EMBEDDING_MODEL=local_colqwen
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8090/api/v1
```

**Launch**:
```bash
./scripts/compose-clean up
```

---

### Single-User Demo (Optional, GPU)

```bash
# .env


DEBUG_MODE=false
LOG_LEVEL=INFO

SINGLE_TENANT_MODE=true
EMBEDDING_MODEL=local_colqwen
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
EMBEDDING_IMAGE_DPI=200

MINIO_URL=http://minio:9000
MILVUS_URI=http://milvus-standalone:19530
MONGODB_URL=mongodb:27017
REDIS_URL=redis:6379
DB_URL=mysql+asyncmy://<db_user>:<db_password>@mysql:3306/layra_db

NEXT_PUBLIC_API_BASE_URL=http://localhost:8090/api/v1
```

**Launch**:
```bash
./scripts/compose-clean up -d --build
```

---

### Production (Cloud)

```bash
# .env.production
DEBUG_MODE=false
LOG_LEVEL=INFO

SECRET_KEY=<generate-with-secrets-module>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=11520

SERVER_IP=https://api.example.com
MINIO_URL=https://s3.example.com
EMBEDDING_MODEL=local_colqwen
EMBEDDING_IMAGE_DPI=200

# External services
DB_URL=mysql+asyncmy://layra_prod:strong_password@db.prod.internal:3306/layra_prod
MONGODB_URL=mongodb://mongo-prod.internal:27017
REDIS_URL=redis://redis-prod.internal:6379
MILVUS_URI=http://milvus-prod.internal:19530
KAFKA_BROKER_URL=kafka-prod.internal:9094

# Frontend
NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1
NODE_ENV=production

# Monitoring
LOG_LEVEL=INFO
MAX_WORKERS=8
```

**Launch**:
```bash
./scripts/compose-clean up -d
```

---

## Environment Variable Validation

**Required Variables** (must be set):
```
SERVER_IP
DEBUG_MODE
LOG_LEVEL
REDIS_URL
MONGODB_URL
DB_URL
MINIO_URL
MILVUS_URI
KAFKA_BROKER_URL
EMBEDDING_MODEL
SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
```

**Optional Variables** (new in v2.0.0):
```
VECTOR_DB=milvus|qdrant        # Default: milvus
QDRANT_URL=http://qdrant:6333  # Only if VECTOR_DB=qdrant
MINIO_PUBLIC_URL=http://localhost:9000  # For split-horizon DNS
```

**Recommended to Customize**:
```
SECRET_KEY
All passwords (Redis, MongoDB, MySQL, MinIO)
NEXT_PUBLIC_API_BASE_URL (must match SERVER_IP)
MINIO_PUBLIC_URL (for production deployments)
```

**Validation Script**:
```bash
#!/bin/bash
required_vars=("SERVER_IP" "DEBUG_MODE" "REDIS_URL" "MONGODB_URL" "DB_URL")

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Required variable $var is not set"
    exit 1
  fi
done

echo "✅ All required variables are set"
```

---

## Performance Tuning

### For High Throughput

```bash
# Increase workers
MAX_WORKERS=16

# Increase connection pools
DB_POOL_SIZE=20
MONGODB_POOL_SIZE=100

# Increase partition count
KAFKA_PARTITIONS_NUMBER=10

# Optimize embedding
EMBEDDING_IMAGE_DPI=150  # Faster, lower quality
UNOSERVER_INSTANCES=8

# Increase UNO instances for document processing
```

### For Low Latency

```bash
# Decrease timeouts
KAFKA_SESSION_TIMEOUT_MS=15000
KAFKA_RETRY_BACKOFF_MS=1000

# Optimize model
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2  # Latest version

# Increase search precision
# (configured in Milvus, not here)
```

### For Resource Efficiency

```bash
# Decrease workers (if high CPU usage)
MAX_WORKERS=2

# Decrease pools (if low memory)
DB_POOL_SIZE=5
MONGODB_POOL_SIZE=10

# Reduce UNO instances
UNOSERVER_INSTANCES=1

# Lower DPI
EMBEDDING_IMAGE_DPI=150
```

---

## GPU & Model Server Configuration (RTX 5000 Optimized)

The `model-server` running `ColQwen2.5` has been tuned for 16GB VRAM.

### ColBERT Service Settings
Located in `model-server/colbert_service.py`:
- **Quantization**: 4-bit (BNB) enabled.
- **Attention**: SDPA (Scaled Dot Product Attention) enforced.
- **Resolution**:
  - `shortest_edge`: **768** (Reduced from default 3136)
  - `longest_edge`: **1536**
  - *Reason*: Prevents CUDA OOM on 16GB cards. Defaults require ~24GB+.

### Docker Compose
- `shm_size`: '2gb' (Required for PyTorch dataloader, though `num_workers=0` is used).
- `deploy.resources.reservations.devices`: 1 GPU.

---

## Troubleshooting

### Connection Issues

**Problem**: `Connection refused to Milvus`
```
Solution: Check MILVUS_URI and network connectivity
docker-compose logs milvus
```

**Problem**: `Redis timeout`
```
Solution: Check REDIS_URL and Redis container status
docker-compose logs redis
redis-cli ping  # Should return PONG
```

### Performance Issues

**Problem**: `Slow document processing`
```
Solution: Check EMBEDDING_IMAGE_DPI and UNOSERVER_INSTANCES
Increase UNOSERVER_INSTANCES for parallel processing
```

**Problem**: `High memory usage`
```
Solution: Decrease pool sizes:
DB_POOL_SIZE=5
MONGODB_POOL_SIZE=10
UNOSERVER_INSTANCES=1
```

---

**Related Documentation**:
- [API.md](./API.md) - API endpoints
- [DATABASE.md](./DATABASE.md) - Database schemas
- [Deployment Guide](../DEPLOYMENT.md) - Deployment instructions

# Credentials SSOT (Single Source of Truth)

Generated: 2026-01-27

---

## ACTUAL CREDENTIALS IN USE

### Database Credentials

| Service | Username | Password | Source |
|---------|----------|----------|--------|
| MySQL (layra) | `layra` | `layra_password` | .env.example |
| MySQL (root) | `root` | `root_password_strong` | .env.example |
| MongoDB | `testuser` | `testpassword` | .env.example |
| Redis | N/A | `redispassword_strong` | .env.example |
| MinIO (main) | `minio_acc_3m4n5o` | `minio_sec_6p7q8r` | .env.example |
| MinIO (Milvus) | `${MILVUS_MINIO_ACCESS_KEY}` | `${MILVUS_MINIO_SECRET_KEY}` | docker-compose.yml |

### API Keys

| Key | Value | Source |
|-----|-------|--------|
| JINA_API_KEY | `your_jina_api_key_here` | .env.example (placeholder) |
| SECRET_KEY | `your_super_secret_key_change_this_in_production` | .env.example (placeholder) |

### Hardcoded Credential (BUG)

| Location | Credential | Should Use |
|----------|-----------|------------|
| `model-server/config.py:6` | `thesis_redis_1c962832d09529674794ff43258d721c` | `REDIS_PASSWORD` from env |

---

## ENV VARIABLES TO REMOVE FROM .env.example (BLOAT)

These are defined but **never used** in docker-compose.yml:

```bash
# REMOVE - Not used anywhere
ALLOWED_ORIGINS
KAFKA_REPLICATION_FACTOR
KAFKA_RETRY_BACKOFF_MS
KAFKA_SESSION_TIMEOUT_MS
LOG_FILE
MILVUS_URI
MINIO_PUBLIC_URL
MYSQL_DATABASE      # Hardcoded in docker-compose
MYSQL_PASSWORD      # Hardcoded in docker-compose
MYSQL_ROOT_PASSWORD # Hardcoded in docker-compose
MYSQL_USER          # Hardcoded in docker-compose
VECTOR_DB
```

---

## CONNECTION STRINGS

| Service | Connection String |
|---------|------------------|
| MySQL | `mysql+asyncmy://layra:layra_password@mysql:3306/layra_db` |
| MongoDB | `mongodb://testuser:testpassword@mongodb:27017` |
| Redis | `redis:6379` (auth via `REDIS_PASSWORD`) |
| MinIO | `http://minio:9000` |
| Milvus | `http://milvus-standalone:19530` |
| Kafka | `kafka:9094` |

---

## CRITICAL FIXES NEEDED

1. **model-server/config.py**: Use `REDIS_PASSWORD` from environment instead of hardcoded value
2. **docker-compose.yml**: MySQL credentials are hardcoded inline, should use ${} variables

---

## MINIMAL .env.example (CLEANED)

After removing bloat, only these variables are actually used:

```bash
# Server
SERVER_IP=http://localhost
DEBUG_MODE=false
LOG_LEVEL=INFO
MAX_WORKERS=10

# MySQL
DB_URL=mysql+asyncmy://layra:layra_password@mysql:3306/layra_db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis:6379
REDIS_PASSWORD=redispassword_strong
REDIS_TOKEN_DB=0
REDIS_TASK_DB=1
REDIS_LOCK_DB=2

# MongoDB
MONGODB_URL=mongodb://testuser:testpassword@mongodb:27017
MONGODB_ROOT_USERNAME=testuser
MONGODB_ROOT_PASSWORD=testpassword
MONGODB_DB=chat_mongodb
MONGODB_POOL_SIZE=100
MONGODB_MIN_POOL_SIZE=10

# MinIO (main)
MINIO_URL=http://minio:9000
MINIO_ACCESS_KEY=minio_acc_3m4n5o
MINIO_SECRET_KEY=minio_sec_6p7q8r
MINIO_BUCKET_NAME=minio-file
MINIO_IMAGE_URL_PREFIX=http://localhost:9000/minio-file

# Milvus MinIO
MILVUS_MINIO_ACCESS_KEY=milvus_minio_admin
MILVUS_MINIO_SECRET_KEY=milvus_minio_secret_strong

# Kafka
KAFKA_BROKER_URL=kafka:9094
KAFKA_TOPIC=task_generation
KAFKA_PARTITIONS_NUMBER=10
KAFKA_GROUP_ID=layra-group

# Models
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
EMBEDDING_MODEL=colqwen2.5
EMBEDDING_IMAGE_DPI=200
MODEL_BASE_URL=http://model-server:8000

# Security
SECRET_KEY=your_super_secret_key_change_this_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=11520
ALGORITHM=HS256

# API Keys
JINA_API_KEY=your_jina_api_key_here

# Unoconv
UNOSERVER_HOST=unoserver
UNOSERVER_BASE_PORT=2003
UNOSERVER_BASE_UNO_PORT=3003
UNOSERVER_INSTANCES=5

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NODE_ENV=development

# Sandbox
SANDBOX_SHARED_VOLUME=/tmp/sandbox
```

---

## SERVICE INTERNAL CONNECTIONS (Hardcoded in docker-compose)

These are set directly in docker-compose.yml and don't need env vars:

- MySQL root/user credentials (inline in docker-compose)
- Redis password (inline healthcheck only)
- MinIO Milvus credentials (inline - needs fixing)

---

## NEXT STEPS

1. Fix `model-server/config.py` to use env var
2. Clean .env.example to remove bloat
3. Consider externalizing MySQL credentials to env vars

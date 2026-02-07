# Environment Variables Reference

**Version:** 2.1.0
**Last Updated:** 2026-01-27
**Status:** Comprehensive Reference

---

## Table of Contents

- [Quick Start](#quick-start-minimal-configuration)
- [Server Configuration](#server-configuration)
- [Database Configuration](#database-configuration)
  - [MySQL](#mysql-configuration)
  - [MongoDB](#mongodb-configuration)
  - [Redis](#redis-configuration)
  - [Connection Pooling](#connection-pooling)
- [Storage Configuration](#storage-configuration)
  - [MinIO](#minio-configuration)
  - [Milvus Internal MinIO](#milvus-internal-minio)
- [Vector Database Configuration](#vector-database-configuration)
- [Message Queue Configuration](#message-queue-configuration)
- [Embedding Model Configuration](#embedding-model-configuration)
- [Document Processing Configuration](#document-processing-configuration)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Authentication & Security](#authentication--security)
- [Frontend Configuration](#frontend-configuration)
- [Multi-Tenancy Configuration](#multi-tenancy-configuration)
- [Security Considerations](#security-considerations)
- [Common Pitfalls](#common-pitfalls)
- [Related Documentation](#related-documentation)

---

## Quick Start: Minimal Configuration

To get Layra running with minimal configuration, you MUST set these variables:

```bash
# Required for system startup
SERVER_IP=http://localhost:8090
SECRET_KEY=<generate-with-openssl-rand-hex-32>

  # Database connections
  DB_URL=mysql+asyncmy://layra:password@mysql:3306/layra_db
  REDIS_URL=redis:6379
  MONGODB_URL=mongodb:27017
  MILVUS_URI=http://milvus-standalone:19530

  # At least one LLM provider (see LLM Provider section)
  # Examples (pick one provider you actually use):
  # OPENAI_API_KEY=sk-your-openai-key-here
  # DEEPSEEK_API_KEY=sk-your-deepseek-key-here
  # ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
  # Or use an OpenAI-compatible proxy:
  # CLIPROXYAPI_BASE_URL=http://cliproxyapi:8317/v1
  # CLIPROXYAPI_API_KEY=your-proxy-key
  ```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# or
openssl rand -hex 32
```

---

## Server Configuration

### `SERVER_IP`

**Variable Name:** `SERVER_IP`
**Type:** String (URL)
**Default Value:** `http://localhost:8090` (from config.py: `http://localhost`)
**Required:** Yes
**Example Values:**
- Development: `http://localhost:8090`
- Production: `https://api.example.com`
- Docker: `http://layra-backend:8090`

**Purpose:**
- Base URL for the application server
- Used for generating presigned URLs for file downloads
- Referenced by frontend for API endpoints

**Related Variables:**
- `NEXT_PUBLIC_API_BASE_URL` - Should typically match `SERVER_IP` + `/api/v1`
- `MINIO_IMAGE_URL_PREFIX` - Uses `SERVER_IP` for image URLs

**Security Notes:**
- In production, use HTTPS with valid SSL certificate
- Ensure DNS resolves correctly if using domain name

---

### `DEBUG_MODE`

**Variable Name:** `DEBUG_MODE`
**Type:** Boolean
**Default Value:** `false` (from config.py)
**Required:** No
**Example Values:** `true`, `false`

**Purpose:**
- Enables verbose logging and debugging features
- SQLAlchemy echo mode (logs all SQL queries)
- Longer stack traces in error responses
- CORS allows all origins (development only)
- Hot reloading in development

**Effects When `true`:**
- Detailed error messages exposed to clients
- All SQL queries logged to console
- Performance overhead due to logging

**Security Notes:**
- **NEVER** enable in production
- Exposes internal system details
- Significant performance impact

---

### `LOG_LEVEL`

**Variable Name:** `LOG_LEVEL`
**Type:** Enum
**Default Value:** `INFO` (from config.py)
**Required:** No
**Valid Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Purpose:**
- Controls verbosity of application logging
- Affects which log messages are written to output

**Recommendations:**
- Development: `DEBUG`
- Production: `INFO` or `WARNING`
- Troubleshooting: `DEBUG` (temporary)

**Related Variables:**
- `DEBUG_MODE` - Also affects logging behavior

---

### `MAX_WORKERS`

**Variable Name:** `MAX_WORKERS`
**Type:** Integer
**Default Value:** `10` (from config.py)
**Required:** No
**Example Values:** `2`, `4`, `8`, `16`

**Purpose:**
- Number of async worker processes for handling requests
- Affects concurrent request capacity

**Tuning Guidelines:**
- CPU-bound tasks: `num_cores`
- I/O-bound tasks: `num_cores * 2-4`
- Recommended: `4-8` for typical deployments
- High throughput: `16+` (with sufficient RAM)

**Security Notes:**
- Too many workers can exhaust memory
- Monitor memory usage when increasing

---

## Database Configuration

### MySQL Configuration

### `DB_URL`

**Variable Name:** `DB_URL`
**Type:** String (SQLAlchemy Connection String)
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:**
- Docker: `mysql+asyncmy://layra:password@mysql:3306/layra_db`
- External: `mysql+asyncmy://user:pass@db.example.com:3306/layra_prod`

**Purpose:**
- Primary database connection string for MySQL/MariaDB
- Uses `asyncmy` driver for async operations

**Security Notes:**
- Contains credentials - protect .env file
- Use strong passwords (32+ characters)
- Restrict database user to minimum required permissions
- Use SSL connections in production: `?ssl=true`

**Related Variables:**
- `MYSQL_ROOT_PASSWORD` - Root admin password
- `MYSQL_USER` - Application database user
- `MYSQL_PASSWORD` - Application database password
- `MYSQL_DATABASE` - Database name
- `DB_POOL_SIZE` - Connection pool size
- `DB_MAX_OVERFLOW` - Pool overflow limit

**Validation:**
- Must include username, password, host, port, and database name
- Format: `mysql+asyncmy://username:password@host:port/database`

---

### `DB_POOL_SIZE`

**Variable Name:** `DB_POOL_SIZE`
**Type:** Integer
**Default Value:** `10` (from config.py)
**Required:** No
**Example Values:** `5`, `10`, `20`, `50`

**Purpose:**
- Base number of connections to maintain in MySQL connection pool
- Affects concurrent database operation capacity

**Tuning Guidelines:**
- Small deployments (< 100 users): `5-10`
- Medium deployments (100-1000 users): `10-20`
- Large deployments (1000+ users): `20-50`
- High write throughput: Increase to `20+`

**Related Variables:**
- `DB_MAX_OVERFLOW` - Additional connections allowed when pool is full
- `MAX_WORKERS` - Should align with worker count

**Security Notes:**
- Too large pools can exhaust database connections
- Monitor database `max_connections` setting

---

### `DB_MAX_OVERFLOW`

**Variable Name:** `DB_MAX_OVERFLOW`
**Type:** Integer
**Default Value:** `20` (from config.py)
**Required:** No
**Example Values:** `10`, `20`, `50`

**Purpose:**
- Maximum additional connections allowed beyond `DB_POOL_SIZE`
- Handles traffic spikes by temporarily expanding pool

**Total Connections:** `DB_POOL_SIZE + DB_MAX_OVERFLOW`

**Tuning Guidelines:**
- Set to `2x` pool size for bursty traffic
- Set to `0.5x` pool size for steady traffic
- Monitor for connection exhaustion during spikes

**Related Variables:**
- `DB_POOL_SIZE` - Base pool size

---

### MySQL-Specific Variables

#### `MYSQL_ROOT_PASSWORD`

**Variable Name:** `MYSQL_ROOT_PASSWORD`
**Type:** String
**Default Value:** Auto-generated in docker-compose
**Required:** Yes
**Example Values:** `<strong-32-char-password>`

**Purpose:**
- MySQL root administrator password
- Used for database initialization and administrative tasks

**Security Notes:**
- **CRITICAL:** Change from default in production
- Use strong password (32+ characters, mixed case, numbers, symbols)
- Never commit to version control
- Rotate periodically (quarterly recommended)

**Related Variables:**
- `MYSQL_USER` - Application user
- `MYSQL_PASSWORD` - Application user password

---

#### `MYSQL_DATABASE`

**Variable Name:** `MYSQL_DATABASE`
**Type:** String (database name)
**Default Value:** `layra_db` (from docker-compose)
**Required:** No
**Example Values:** `layra_db`, `layra_prod`, `layra_staging`

**Purpose:**
- Name of the MySQL database to create/use
- Auto-created on first startup

**Security Notes:**
- Use descriptive names for different environments
- Avoid exposing internal structure in database names

---

#### `MYSQL_USER`

**Variable Name:** `MYSQL_USER`
**Type:** String (username)
**Default Value:** `layra` (from docker-compose)
**Required:** No
**Example Values:** `layra`, `layra_app`, `layra_web`

**Purpose:**
- MySQL application user with limited privileges
- Used by backend for database operations

**Security Notes:**
- **NEVER** use root user for application connections
- Grant minimum required permissions only
- Separate users for different environments

---

#### `MYSQL_PASSWORD`

**Variable Name:** `MYSQL_PASSWORD`
**Type:** String
**Default Value:** Auto-generated in docker-compose
**Required:** Yes
**Example Values:** `<strong-32-char-password>`

**Purpose:**
- Password for application database user
- Used in `DB_URL` connection string

**Security Notes:**
- Use different password from `MYSQL_ROOT_PASSWORD`
- Strong password required (32+ characters)
- Rotate regularly

**Related Variables:**
- `MYSQL_USER` - Associated username
- `DB_URL` - Must contain same password

---

### MongoDB Configuration

### `MONGODB_URL`

**Variable Name:** `MONGODB_URL`
**Type:** String (Connection String)
**Default Value:** `localhost:27017` (from config.py)
**Required:** Yes
**Example Values:**
- Docker: `mongodb://mongo:27017`
- With auth: `mongodb://user:pass@host:27017`
- Replica set: `mongodb://host1:27017,host2:27017/?replicaSet=myReplicaSet`

**Purpose:**
- MongoDB connection URI
- Stores conversations, chat history, knowledge base metadata

**Security Notes:**
- Use authentication in production
- Enable TLS/SSL for remote connections
- Restrict to localhost/internal networks when possible
- Use connection string with auth: `mongodb://username:password@host:port`

**Related Variables:**
- `MONGODB_ROOT_USERNAME` - Admin username
- `MONGODB_ROOT_PASSWORD` - Admin password
- `MONGODB_DB` - Database name
- `MONGODB_POOL_SIZE` - Connection pool size

---

### `MONGODB_ROOT_USERNAME`

**Variable Name:** `MONGODB_ROOT_USERNAME`
**Type:** String
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:** `admin`, `layra_admin`

**Purpose:**
- MongoDB admin username for authentication

**Security Notes:**
- Change from default in production
- Use separate admin account from application account
- Minimum 6 characters

**Related Variables:**
- `MONGODB_ROOT_PASSWORD` - Admin password
- `MONGODB_URL` - Connection string

---

### `MONGODB_ROOT_PASSWORD`

**Variable Name:** `MONGODB_ROOT_PASSWORD`
**Type:** String
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:** `<strong-32-char-password>`

**Purpose:**
- MongoDB admin password for authentication

**Security Notes:**
- **CRITICAL:** Use strong password (32+ characters)
- Different from MySQL and Redis passwords
- Rotate quarterly
- Never commit to version control

**Related Variables:**
- `MONGODB_ROOT_USERNAME` - Admin username

---

### `MONGODB_DB`

**Variable Name:** `MONGODB_DB`
**Type:** String (database name)
**Default Value:** `chat_mongodb` (from config.py)
**Required:** No
**Example Values:** `layra_mongo`, `chat_mongodb`, `layra_conversations`

**Purpose:**
- Default MongoDB database name
- Stores chat conversations and metadata

**Security Notes:**
- Use environment-specific names (dev, staging, prod)
- Must exist or auto-create must be enabled

---

### `MONGODB_POOL_SIZE`

**Variable Name:** `MONGODB_POOL_SIZE`
**Type:** Integer
**Default Value:** `50` (from config.py)
**Required:** No
**Example Values:** `10`, `50`, `100`, `200`

**Purpose:**
- Maximum number of connections in MongoDB connection pool

**Tuning Guidelines:**
- Small deployments: `10-20`
- Medium deployments: `50`
- Large deployments: `100-200`
- High chat throughput: `100+`

**Security Notes:**
- Monitor MongoDB connection limits
- Too large can exhaust memory

**Related Variables:**
- `MONGODB_MIN_POOL_SIZE` - Minimum connections to maintain

---

### `MONGODB_MIN_POOL_SIZE`

**Variable Name:** `MONGODB_MIN_POOL_SIZE`
**Type:** Integer
**Default Value:** `10` (from config.py)
**Required:** No
**Example Values:** `5`, `10`, `20`

**Purpose:**
- Minimum number of connections to maintain in MongoDB pool
- Keeps connections open for faster response

**Tuning Guidelines:**
- Set to `20%` of `MONGODB_POOL_SIZE`
- Higher values reduce connection latency but use more memory

**Related Variables:**
- `MONGODB_POOL_SIZE` - Maximum pool size

---

### Redis Configuration

### `REDIS_URL`

**Variable Name:** `REDIS_URL`
**Type:** String (Connection String)
**Default Value:** `localhost:6379` (from config.py)
**Required:** Yes
**Example Values:**
- Docker: `redis://redis:6379`
- With auth: `redis://:password@host:6379`
- External: `redis://redis.example.com:6379`

**Purpose:**
- Redis server connection URI
- Used for caching, session storage, distributed locks

**Security Notes:**
- Use authentication in production (set `REDIS_PASSWORD`)
- Bind to internal interfaces only
- Use TLS for remote connections
- Protect with firewall

**Related Variables:**
- `REDIS_PASSWORD` - Authentication password
- `REDIS_TOKEN_DB` - Token storage database
- `REDIS_TASK_DB` - Task tracking database
- `REDIS_LOCK_DB` - Distributed locks database

---

### `REDIS_PASSWORD`

**Variable Name:** `REDIS_PASSWORD`
**Type:** String
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:** `<strong-32-char-password>`

**Purpose:**
- Redis authentication password
- Required for Redis ACL in production

**Security Notes:**
- **CRITICAL:** Use strong password (32+ characters)
- Different from database passwords
- Rotate regularly
- Never use default passwords

**Related Variables:**
- `REDIS_URL` - Connection string (may include password)

---

### `REDIS_TOKEN_DB`

**Variable Name:** `REDIS_TOKEN_DB`
**Type:** Integer (0-15)
**Default Value:** `0` (from config.py)
**Required:** No
**Example Values:** `0`, `1`, `2`

**Purpose:**
- Redis database number for JWT token storage
- Stores active user sessions

**Security Notes:**
- DO NOT share with other applications
- Redis supports 16 databases (0-15)
- Each database is isolated

**Related Variables:**
- `REDIS_TASK_DB` - Task storage (use different number)
- `REDIS_LOCK_DB` - Lock storage (use different number)

---

### `REDIS_TASK_DB`

**Variable Name:** `REDIS_TASK_DB`
**Type:** Integer (0-15)
**Default Value:** `1` (from config.py)
**Required:** No
**Example Values:** `0`, `1`, `2`

**Purpose:**
- Redis database number for task progress tracking
- Stores async task states

**Security Notes:**
- Must be different from `REDIS_TOKEN_DB`
- Isolated from token storage

**Related Variables:**
- `REDIS_TOKEN_DB` - Token storage
- `REDIS_LOCK_DB` - Lock storage

---

### `REDIS_LOCK_DB`

**Variable Name:** `REDIS_LOCK_DB`
**Type:** Integer (0-15)
**Default Value:** `2` (from config.py)
**Required:** No
**Example Values:** `0`, `1`, `2`

**Purpose:**
- Redis database number for distributed locks
- Prevents race conditions in concurrent operations

**Security Notes:**
- Must be different from `REDIS_TOKEN_DB` and `REDIS_TASK_DB`
- Critical for data consistency

---

### Connection Pooling

Connection pooling variables are covered under their respective database sections above.

---

## Storage Configuration

### MinIO Configuration

MinIO provides S3-compatible object storage for files, images, and documents.

### `MINIO_URL`

**Variable Name:** `MINIO_URL`
**Type:** String (URL)
**Default Value:** `http://minio:9000` (from config.py)
**Required:** Yes
**Example Values:**
- Docker: `http://minio:9000`
- External: `https://s3.example.com`
- Internal: `http://minio.internal:9000`

**Purpose:**
- MinIO API endpoint for backend services
- Used for internal backend-to-MinIO traffic

**Security Notes:**
- Use HTTPS in production
- Different from `MINIO_PUBLIC_URL` in split-horizon DNS setups
- Internal endpoint (not browser-accessible)

**Related Variables:**
- `MINIO_PUBLIC_URL` - Public endpoint for browser access
- `MINIO_ACCESS_KEY` - S3 access key (username)
- `MINIO_SECRET_KEY` - S3 secret key (password)

---

### `MINIO_PUBLIC_URL`

**Variable Name:** `MINIO_PUBLIC_URL`
**Type:** String (URL)
**Default Value:** `""` (empty, falls back to `SERVER_IP + :9000`)
**Required:** No
**Example Values:**
- Development: `http://localhost:9000`
- Production: `https://s3.example.com`
- CDN: `https://cdn.example.com`

**Purpose:**
- MinIO public endpoint for user downloads (browser-accessible)
- Used in presigned URLs for external access
- Critical for split-horizon DNS deployments

**When to Set:**
- Production deployments with external users
- Behind reverse proxy/load balancer
- Using CDN for file distribution
- Split-horizon DNS (internal vs external URLs)

**Security Notes:**
- Must be accessible from user browsers
- Use HTTPS in production
- May differ from `MINIO_URL` in production
- Falls back to `SERVER_IP:9000` if not set (Docker only)

**Related Variables:**
- `MINIO_URL` - Internal endpoint
- `SERVER_IP` - Fallback for public URL
- `MINIO_IMAGE_URL_PREFIX` - Image URL prefix

---

### `MINIO_ACCESS_KEY`

**Variable Name:** `MINIO_ACCESS_KEY`
**Type:** String
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:** `layra_minio`, `minio_admin`, `AKIAIOSFODNN7EXAMPLE`

**Purpose:**
- S3 access key (username) for MinIO authentication
- At least 3 characters, recommended 20+ characters

**Security Notes:**
- **CRITICAL:** Change from default in production
- Use different key for each environment
- Rotate quarterly
- Treat as sensitive credential

**Related Variables:**
- `MINIO_SECRET_KEY` - Corresponding secret key

---

### `MINIO_SECRET_KEY`

**Variable Name:** `MINIO_SECRET_KEY`
**Type:** String
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:** `<strong-32-char-password>`

**Purpose:**
- S3 secret key (password) for MinIO authentication
- At least 8 characters, recommended 32+ characters

**Security Notes:**
- **CRITICAL:** Use strong password (32+ characters)
- Different from database passwords
- Rotate regularly
- Never commit to version control
- Use mixed case, numbers, symbols

**Related Variables:**
- `MINIO_ACCESS_KEY` - Corresponding access key

---

### `MINIO_BUCKET_NAME`

**Variable Name:** `MINIO_BUCKET_NAME`
**Type:** String (bucket name)
**Default Value:** `minio-file` (from config.py)
**Required:** No
**Example Values:** `layra-files`, `layra-documents`, `layra-user-uploads`

**Purpose:**
- Default S3 bucket name for file storage
- Auto-created on first startup if doesn't exist

**Naming Requirements:**
- Lowercase only
- 3-63 characters
- No spaces or special characters (except hyphen)
- Must start/end with letter or number
- Cannot be IP address format

**Security Notes:**
- Use descriptive names for different environments
- Avoid exposing internal structure
- Enable bucket policies for access control

---

### `MINIO_IMAGE_URL_PREFIX`

**Variable Name:** `MINIO_IMAGE_URL_PREFIX`
**Type:** String (URL)
**Default Value:** `http://localhost:8090/minio-file` (from .env.example)
**Required:** No
**Example Values:**
- Development: `http://localhost:8090/minio-file`
- Production: `https://cdn.example.com/files`
- With CDN: `https://d1234567890.cloudfront.net`

**Purpose:**
- Public URL prefix for image access
- Prepended to image paths in responses
- Used by frontend to display images

**When to Customize:**
- Using CDN for static content
- Custom domain for files
- Production deployment with SSL

**Security Notes:**
- Must be accessible from user browsers
- Use HTTPS in production
- May reference reverse proxy or CDN

**Related Variables:**
- `MINIO_PUBLIC_URL` - MinIO public endpoint
- `SERVER_IP` - May be used as base

---

### Milvus Internal MinIO

Milvus vector database uses its own internal MinIO instance for vector storage.

### `MILVUS_MINIO_ACCESS_KEY`

**Variable Name:** `MILVUS_MINIO_ACCESS_KEY`
**Type:** String
**Default Value:** `minioadmin` (from .env.example)
**Required:** No (internal use)
**Example Values:** `minioadmin`, `milvus_minio`

**Purpose:**
- Access key for Milvus internal MinIO instance
- Used by Milvus for vector data storage
- Separate from main MinIO instance

**Security Notes:**
- Internal use only (Milvus <-> MinIO)
- Change from default in production
- Different from main `MINIO_ACCESS_KEY`

**Related Variables:**
- `MILVUS_MINIO_SECRET_KEY` - Corresponding secret key

---

### `MILVUS_MINIO_SECRET_KEY`

**Variable Name:** `MILVUS_MINIO_SECRET_KEY`
**Type:** String
**Default Value:** `minioadmin` (from .env.example)
**Required:** No (internal use)
**Example Values:** `minioadmin`, `<strong-password>`

**Purpose:**
- Secret key for Milvus internal MinIO instance
- Used by Milvus for vector data storage

**Security Notes:**
- Internal use only
- Change from default in production
- Strong password recommended
- Different from main `MINIO_SECRET_KEY`

---

## Vector Database Configuration

### `MILVUS_URI`

**Variable Name:** `MILVUS_URI`
**Type:** String (Connection URI)
**Default Value:** Required field (no default) in config.py
**Required:** Yes
**Example Values:**
- Docker: `http://milvus-standalone:19530`
- Host (debug tools): `http://localhost:19531` (published port from docker-compose)
- External: `http://milvus.example.com:19530`
- Cluster: `http://milvus-coordinator:19530`

**Important Notes (Docker networking):**
- Do **not** set `MILVUS_URI=http://127.0.0.1:19530` for the backend container.
  Inside a container, `127.0.0.1` points to the container itself, not the Milvus service.
- If you need to reach the docker Milvus from the host, use `http://localhost:19531`.

**Migration Runbook:**
- Host/systemd Milvus -> docker-compose Milvus: `docs/operations/MILVUS_HOST_TO_DOCKER_MIGRATION.md`

**Purpose:**
- Milvus vector database connection URI
- Stores document embeddings for semantic search

**Security Notes:**
- Use internal network when possible
- Enable authentication in production
- Use TLS for remote connections

**Related Variables:**
- `EMBEDDING_MODEL` - Determines embedding dimension
- `VECTOR_DB` - Can switch to Qdrant (experimental)

---

### `VECTOR_DB`

**Variable Name:** `VECTOR_DB`
**Type:** Enum
**Default Value:** `milvus` (from config.py)
**Required:** No
**Valid Values:** `milvus`, `qdrant`

**Purpose:**
- Vector database backend selection
- Allows switching between Milvus and Qdrant

**Options:**
- `milvus` - Production-grade vector DB (default)
- `qdrant` - Alternative vector DB (experimental, added v2.0.0)

**Migration Notes:**
- See `docs/vector_db/OVERVIEW.md` for migration guide
- Data migration required when switching
- Qdrant support added for multi-vector experiments

**Related Variables:**
- `QDRANT_URL` - Required if `VECTOR_DB=qdrant`
- `MILVUS_URI` - Required if `VECTOR_DB=milvus`

---

### `QDRANT_URL`

**Variable Name:** `QDRANT_URL`
**Type:** String (Connection URI)
**Default Value:** `http://qdrant:6333` (from config.py)
**Required:** Only if `VECTOR_DB=qdrant`
**Example Values:** `http://qdrant:6333`, `http://qdrant.example.com:6333`

**Purpose:**
- Qdrant vector database connection URI
- Alternative to Milvus for multi-vector experiments

**Security Notes:**
- Experimental feature (v2.0.0)
- Enable authentication in production
- Use internal network when possible

**Related Variables:**
- `VECTOR_DB` - Must be set to `qdrant`

---

## Message Queue Configuration

### Kafka Configuration

### `KAFKA_BROKER_URL`

**Variable Name:** `KAFKA_BROKER_URL`
**Type:** String (Connection String)
**Default Value:** `localhost:9094` (from config.py)
**Required:** Yes
**Example Values:**
- Docker: `kafka:9094`
- External: `kafka.example.com:9094`
- Cluster: `kafka-0.kafka.internal:9094,kafka-1.kafka.internal:9094`

**Purpose:**
- Kafka broker connection URL
- Used for async task processing and file ingestion

**Security Notes:**
- Use internal network when possible
- Enable SASL/SSL in production
- Restrict access with firewall

**Related Variables:**
- `KAFKA_TOPIC` - Default topic name
- `KAFKA_GROUP_ID` - Consumer group identifier

---

### `KAFKA_TOPIC`

**Variable Name:** `KAFKA_TOPIC`
**Type:** String (topic name)
**Default Value:** `task_generation` (from config.py)
**Required:** No
**Example Values:** `task_generation`, `file_processing`, `layra_tasks`

**Purpose:**
- Default Kafka topic for task messages
- Auto-created if doesn't exist

**Security Notes:**
- Use descriptive names
- Separate topics for different environments

**Related Variables:**
- `KAFKA_PARTITIONS_NUMBER` - Topic partition count

---

### `KAFKA_PARTITIONS_NUMBER`

**Variable Name:** `KAFKA_PARTITIONS_NUMBER`
**Type:** Integer
**Default Value:** `10` (from config.py)
**Required:** No
**Example Values:** `1`, `3`, `10`, `50`

**Purpose:**
- Number of partitions for Kafka topic
- Affects parallelism of message processing

**Tuning Guidelines:**
- Small deployments: `1-3`
- Medium deployments: `3-10`
- Large deployments: `10-50`
- Formula: `partitions = expected_throughput / max_consumer_throughput`

**Security Notes:**
- More partitions = more parallelism
- Cannot decrease after topic creation
- Affects consumer scaling

**Related Variables:**
- `KAFKA_GROUP_ID` - Consumer group identifier

---

### `KAFKA_GROUP_ID`

**Variable Name:** `KAFKA_GROUP_ID`
**Type:** String
**Default Value:** `task_consumer_group` (from config.py)
**Required:** No
**Example Values:** `layra_consumers`, `file_processors`

**Purpose:**
- Consumer group identifier for Kafka
- Enables load balancing among consumers

**Security Notes:**
- Unique per deployment/environment
- Prevents cross-environment consumption

---

### `KAFKA_RETRY_BACKOFF_MS`

**Variable Name:** `KAFKA_RETRY_BACKOFF_MS`
**Type:** Integer (milliseconds)
**Default Value:** Not defined in .env.example (5000 typical)
**Required:** No
**Example Values:** `1000`, `5000`, `10000`

**Purpose:**
- Backoff time between Kafka retry attempts
- Prevents overwhelming system during failures

**Tuning Guidelines:**
- Fast recovery: `1000-3000`
- Normal: `5000`
- Slow recovery: `10000+`

**Security Notes:**
- Too short may cause cascading failures
- Too long delays recovery

**Related Variables:**
- `KAFKA_SESSION_TIMEOUT_MS` - Consumer session timeout

---

### `KAFKA_SESSION_TIMEOUT_MS`

**Variable Name:** `KAFKA_SESSION_TIMEOUT_MS`
**Type:** Integer (milliseconds)
**Default Value:** Not defined in .env.example (30000 typical)
**Required:** No
**Example Values:** `10000`, `30000`, `60000`

**Purpose:**
- Kafka consumer session timeout
- Consumer considered dead if no heartbeat within this time

**Tuning Guidelines:**
- Fast detection: `10000`
- Normal: `30000`
- Slow networks: `60000+`

**Security Notes:**
- Too short may cause premature rebalancing
- Too long delays failure detection

**Related Variables:**
- `KAFKA_RETRY_BACKOFF_MS` - Retry backoff time

---

## Embedding Model Configuration

### `EMBEDDING_MODEL`

**Variable Name:** `EMBEDDING_MODEL`
**Type:** Enum
**Default Value:** `local_colqwen` (from config.py)
**Required:** No
**Valid Values:** `local_colqwen`, `jina_embeddings_v4`

**Purpose:**
- Embedding model provider for document vectorization
- Determines how text/images are converted to vectors

**Options:**

| Option | Requirements | Performance | Use Case |
|--------|-------------|-------------|----------|
| `local_colqwen` | GPU with 16GB+ VRAM, ~15GB model download | 1.67 img/s (RTX 4090) | High throughput, low latency |
| `jina_embeddings_v4` | JINA_API_KEY, no GPU | ~0.5 img/s (API latency) | No GPU available, cloud-based |

**Security Notes:**
- Local model: No data leaves your infrastructure
- Cloud API: Documents sent to Jina servers
- Consider data privacy when choosing

**Related Variables:**
- `COLBERT_MODEL_PATH` - Path to local model
- `JINA_API_KEY` - Required for Jina embeddings
- `MODEL_BASE_URL` - Model download source

---

### `COLBERT_MODEL_PATH`

**Variable Name:** `COLBERT_MODEL_PATH`
**Type:** String (filesystem path)
**Default Value:** `/model_weights/colqwen2.5-v0.2` (from config.py)
**Required:** Only if `EMBEDDING_MODEL=local_colqwen`
**Example Values:** `/model_weights/colqwen2.5-v0.2`, `/models/colbert`

**Purpose:**
- Path to ColBERT model weights on filesystem
- Must exist and contain model files

**Model Download:**
```bash
# Using Hugging Face CLI
huggingface-cli download vidore/colqwen2.5-v0.2 \
  --local-dir /model_weights/colqwen2.5-v0.2

# Or using MODEL_BASE_URL with mirror (China)
MODEL_BASE_URL=https://hf-mirror.com/vidore
```

**Security Notes:**
- Requires ~15GB disk space
- Ensure volume is mounted in container
- Verify model integrity after download

**Related Variables:**
- `EMBEDDING_MODEL` - Must be `local_colqwen`
- `MODEL_BASE_URL` - Download source

---

### `MODEL_BASE_URL`

**Variable Name:** `MODEL_BASE_URL`
**Type:** String (URL)
**Default Value:** `https://huggingface.co/vidore` (from .env.example)
**Required:** No
**Example Values:**
- Official: `https://huggingface.co/vidore`
- China mirror: `https://hf-mirror.com/vidore`

**Purpose:**
- Model download source for Hugging Face models
- Allows using mirrors for faster downloads

**Options:**
- Official: `https://huggingface.co/vidore` (global, may be slow)
- China mirror: `https://hf-mirror.com/vidore` (faster in China)

**Security Notes:**
- Only use trusted sources
- Verify model checksums after download
- Official Hugging Face recommended for production

**Related Variables:**
- `COLBERT_MODEL_PATH` - Download destination
- `HF_TOKEN` - For accessing gated models

---

### `HF_TOKEN`

**Variable Name:** `HF_TOKEN`
**Type:** String (API token)
**Default Value:** Not set (optional)
**Required:** Only for gated models
**Example Values:** `hf_your_huggingface_token_here`

**Purpose:**
- Hugging Face authentication token
- Required for accessing gated models

**Get Token:**
1. Visit https://huggingface.co/settings/tokens
2. Create new token with "read" permissions
3. Set as `HF_TOKEN` in .env

**Security Notes:**
- Treat as sensitive credential
- Rotate regularly
- Grant minimum required permissions
- Never commit to version control

**Related Variables:**
- `MODEL_BASE_URL` - Model source

---

### `JINA_API_KEY`

**Variable Name:** `JINA_API_KEY`
**Type:** String (API key)
**Default Value:** `""` (empty string from config.py)
**Required:** Only if `EMBEDDING_MODEL=jina_embeddings_v4`
**Example Values:** `jina_your_api_key_here`

**Purpose:**
- API key for Jina embeddings service
- Required when using cloud-based embeddings

**Get Key:**
1. Visit https://cloud.jina.ai
2. Sign up and create API key
3. Set as `JINA_API_KEY` in .env

**Security Notes:**
- **CRITICAL:** Protect this key
- Documents are sent to Jina servers
- Consider data privacy implications
- Rotate regularly
- Monitor usage for anomalies

**Related Variables:**
- `EMBEDDING_MODEL` - Must be `jina_embeddings_v4`
- `JINA_EMBEDDINGS_V4_URL` - API endpoint

---

### `JINA_EMBEDDINGS_V4_URL`

**Variable Name:** `JINA_EMBEDDINGS_V4_URL`
**Type:** String (URL)
**Default Value:** `https://api.jina.ai/v1/embeddings` (from config.py)
**Required:** No
**Example Values:** `https://api.jina.ai/v1/embeddings`

**Purpose:**
- Jina embeddings API endpoint
- Typically uses default

**Security Notes:**
- Use HTTPS only
- Verify URL for security (check for typosquatting)
- Proxy through corporate firewall if required

---

### `EMBEDDING_IMAGE_DPI`

**Variable Name:** `EMBEDDING_IMAGE_DPI`
**Type:** Integer
**Default Value:** `200` (from config.py)
**Required:** No
**Example Values:** `150`, `200`, `300`, `400`

**Purpose:**
- DPI (dots per inch) for document-to-image conversion
- Affects quality and speed of embedding generation

**Tuning Guidelines:**

| DPI | Quality | Speed | Use Case |
|-----|---------|-------|----------|
| 150 | Lower | Faster | Large documents, drafts |
| 200 | Balanced | Balanced | **Recommended default** |
| 300 | Higher | Slower | High-quality documents |
| 400 | Best | Very slow | Critical documents |

**Auto-Scaling Behavior:**
- < 50 pages: Uses configured DPI
- 50-100 pages: Uses 200 DPI
- 100+ pages: Uses 150 DPI (auto-reduced for performance)

**Security Notes:**
- Higher DPI = more processing time
- Higher DPI = larger intermediate files
- Monitor memory usage for large documents

---

## Document Processing Configuration

### `UNOSERVER_INSTANCES`

**Variable Name:** `UNOSERVER_INSTANCES`
**Type:** Integer
**Default Value:** `1` (from config.py)
**Required:** No
**Example Values:** `1`, `2`, `4`, `8`

**Purpose:**
- Number of LibreOffice UNO server instances for document conversion
- Enables parallel document processing

**Tuning Guidelines:**
- Small deployments: `1`
- Medium deployments: `2-4`
- Large deployments: `4-8`
- Formula: `instances = num_cores / 2`

**Security Notes:**
- Each instance uses ~500MB RAM
- Too many instances can exhaust memory
- Monitor CPU usage when increasing

**Related Variables:**
- `UNOSERVER_HOST` - Server hostname
- `UNOSERVER_BASE_PORT` - Starting port number
- `UNOSERVER_BASE_UNO_PORT` - Starting UNO port

---

### `UNOSERVER_HOST`

**Variable Name:** `UNOSERVER_HOST`
**Type:** String (hostname)
**Default Value:** `unoserver` (from config.py)
**Required:** No
**Example Values:** `unoserver`, `uno.internal`, `localhost`

**Purpose:**
- LibreOffice UNO server hostname
- Used for document conversion (DOC, XLS, PPT to PDF)

**Security Notes:**
- Internal service only
- No external access required
- Use Docker network hostname in containerized deployments

**Related Variables:**
- `UNOSERVER_INSTANCES` - Number of instances
- `UNOSERVER_BASE_PORT` - Starting port

---

### `UNOSERVER_BASE_PORT`

**Variable Name:** `UNOSERVER_BASE_PORT`
**Type:** Integer (port number)
**Default Value:** `2003` (from config.py)
**Required:** No
**Example Values:** `2002`, `2003`, `3000`

**Purpose:**
- Starting port for UNO server instances
- Ports `BASE_PORT` to `BASE_PORT + INSTANCES - 1` will be used

**Example:**
- `UNOSERVER_INSTANCES=3`
- `UNOSERVER_BASE_PORT=2003`
- Uses ports: `2003`, `2004`, `2005`

**Security Notes:**
- Ensure ports are not used by other services
- Firewall from external access
- Internal network only

**Related Variables:**
- `UNOSERVER_INSTANCES` - Determines port range
- `UNOSERVER_BASE_UNO_PORT` - UNO protocol port

---

### `UNOSERVER_BASE_UNO_PORT`

**Variable Name:** `UNOSERVER_BASE_UNO_PORT`
**Type:** Integer (port number)
**Default Value:** `3003` (from config.py)
**Required:** No
**Example Values:** `3002`, `3003`, `4000`

**Purpose:**
- Starting port for UNO protocol communication
- Ports `BASE_UNO_PORT` to `BASE_UNO_PORT + INSTANCES - 1` will be used

**Example:**
- `UNOSERVER_INSTANCES=3`
- `UNOSERVER_BASE_UNO_PORT=3003`
- Uses ports: `3003`, `3004`, `3005`

**Security Notes:**
- Internal protocol only
- Different from `UNOSERVER_BASE_PORT`
- Ensure no port conflicts

**Related Variables:**
- `UNOSERVER_INSTANCES` - Determines port range
- `UNOSERVER_BASE_PORT` - Server port

---

### `SANDBOX_SHARED_VOLUME`

**Variable Name:** `SANDBOX_SHARED_VOLUME`
**Type:** String (filesystem path)
**Default Value:** `/app/sandbox_workspace` (from config.py)
**Required:** No
**Example Values:** `/app/sandbox_workspace`, `/tmp/sandbox`, `/var/lib/layra/sandbox`

**Purpose:**
- Shared volume for sandbox code execution
- Used for running user-defined code in workflows

**Security Notes:**
- **CRITICAL:** Isolate from sensitive directories
- Must be writable by app container
- Regular cleanup recommended
- Resource limits should be enforced
- Monitor for malicious code execution

---

## LLM Provider Configuration

Layra supports multiple LLM providers. At least one provider API key is REQUIRED.

### `OPENAI_API_KEY`

**Variable Name:** `OPENAI_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (required)
**Required:** Yes (or alternative provider)
**Example Values:** `sk-your-openai-api-key-here`

**Purpose:**
- OpenAI API key for GPT models
- Primary LLM provider for most deployments

**Get Key:**
1. Visit https://platform.openai.com/api-keys
2. Create new API key
3. Set as `OPENAI_API_KEY` in .env

**Supported Models:**
- `gpt-4o` - Flagship model (recommended)
- `gpt-4o-mini` - Faster, cheaper
- `gpt-4-turbo` - Previous generation
- `gpt-3.5-turbo` - Legacy, low cost

**Security Notes:**
- **CRITICAL:** Protect this key
- Rotate immediately if compromised
- Monitor usage for anomalies
- Set spending limits in OpenAI dashboard
- Use organization-scoped keys if available

**Related Variables:**
- `DEFAULT_LLM_PROVIDER` - Set to `openai` to use as default
- `DEFAULT_LLM_MODEL` - Default model selection

---

### `DEEPSEEK_API_KEY`

**Variable Name:** `DEEPSEEK_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `sk-your-deepseek-api-key-here`

**Purpose:**
- DeepSeek API key for cost-effective LLM
- Alternative to OpenAI, often cheaper

**Supported Models:**
- `deepseek-chat` - General purpose
- `deepseek-coder` - Code generation
- `deepseek-reasoner` - Complex reasoning

**Security Notes:**
- Protect like OpenAI key
- Monitor usage and costs
- Check rate limits

**Related Variables:**
- `DEFAULT_LLM_PROVIDER` - Set to `deepseek` to use as default
- `REASONING_LLM_PROVIDER` - Can use deepseek for reasoning

---

### `ANTHROPIC_API_KEY`

**Variable Name:** `ANTHROPIC_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `sk-ant-your-anthropic-api-key-here`

**Purpose:**
- Anthropic Claude API key
- Alternative LLM provider

**Supported Models:**
- `claude-3-opus` - Most capable
- `claude-3-sonnet` - Balanced
- `claude-3-haiku` - Fastest

**Security Notes:**
- Protect key from unauthorized access
- Monitor usage
- Check rate limits

**Related Variables:**
- `DEFAULT_LLM_PROVIDER` - Set to `anthropic` to use as default

---

### `GEMINI_API_KEY`

**Variable Name:** `GEMINI_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `AIza-your-gemini-api-key-here`

**Purpose:**
- Google Gemini API key
- Google's LLM offering

**Supported Models:**
- `gemini-pro` - General purpose
- `gemini-ultra` - Most capable

**Security Notes:**
- Protect from unauthorized access
- Enable API restrictions in Google Cloud Console
- Monitor usage and costs

**Related Variables:**
- `DEFAULT_LLM_PROVIDER` - Set to `gemini` to use as default

---

### `ZHIPUAI_API_KEY`

**Variable Name:** `ZHIPUAI_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `your-zhipuai-api-key-here`

**Purpose:**
- Zhipu AI (GLM) API key
- Optimized for Chinese language
- **Note:** For Z.ai (GLM Coding Plan), use `ZAI_API_KEY` instead.

**Supported Models:**
- `glm-4-plus` - Most capable
- `glm-4-0520` - Latest version
- `glm-4-flash` - Fastest, cost-effective

**Security Notes:**
- Protect from unauthorized access
- Monitor usage

**Related Variables:**
- `CHINESE_LLM_PROVIDER` - Set to `zhipu` for Chinese text
- `CODING_LLM_PROVIDER` - Can use zhipu for code

---

### `ZAI_API_KEY`

**Variable Name:** `ZAI_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `your-zai-api-key-here`

**Purpose:**
- Z.ai (GLM Coding Plan) API key
- Dedicated provider for Z.ai platform (https://z.ai)
- Supports GLM coding models with specific casing requirements (handled automatically)

**Supported Models:**
- `glm-4.7` - Coding optimized
- `glm-4.7-flash` - Fast coding
- `glm-4.5-air` - Lightweight coding

**Security Notes:**
- Distinct from ZhipuAI keys (different format)
- **CRITICAL:** Do not mix with `ZHIPUAI_API_KEY`
- Protect from unauthorized access

**Related Variables:**
- `CODING_LLM_PROVIDER` - Set to `zai`

---

### `MOONSHOT_API_KEY`

**Variable Name:** `MOONSHOT_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `sk-your-moonshot-api-key-here`

**Purpose:**
- Moonshot AI (Kimi) API key
- Chinese language optimized

**Supported Models:**
- `moonshot-v1-8k` - 8K context
- `moonshot-v1-32k` - 32K context
- `moonshot-v1-128k` - 128K context

**Security Notes:**
- Protect from unauthorized access
- Monitor usage

**Related Variables:**
- `BACKUP_LLM_PROVIDER` - Can use moonshot as backup

---

### `MINIMAX_API_KEY`

**Variable Name:** `MINIMAX_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `your-minimax-api-key-here`

**Purpose:**
- MiniMax AI API key
- Alternative LLM provider

**Security Notes:**
- Protect from unauthorized access
- Monitor usage

---

### `COHERE_API_KEY`

**Variable Name:** `COHERE_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `your-cohere-api-key-here`

**Purpose:**
- Cohere API key
- Enterprise-focused LLM provider

**Supported Models:**
- `command-r-plus` - Flagship
- `command-r` - Standard

**Security Notes:**
- Protect from unauthorized access
- Monitor usage

---

### `OLLAMA_API_KEY`

**Variable Name:** `OLLAMA_API_KEY`
**Type:** String (API key)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `your-ollama-api-key-here`

**Purpose:**
- Ollama API key for local models
- Run LLMs locally without external API calls

**Security Notes:**
- Local deployment only
- No data leaves infrastructure
- Requires sufficient compute resources

---

### Default LLM Configuration

### `DEFAULT_LLM_PROVIDER`

**Variable Name:** `DEFAULT_LLM_PROVIDER`
**Type:** String (provider name)
**Default Value:** `openai` (from .env.example)
**Required:** No
**Valid Values:** `openai`, `deepseek`, `anthropic`, `gemini`, `zhipu`, `moonshot`, `minimax`, `cohere`, `ollama`

**Purpose:**
- Default LLM provider for new users
- Used when no provider specified

**Security Notes:**
- Ensure corresponding API key is set
- Verify provider is accessible

**Related Variables:**
- `DEFAULT_LLM_MODEL` - Default model for provider

---

### `DEFAULT_LLM_MODEL`

**Variable Name:** `DEFAULT_LLM_MODEL`
**Type:** String (model name)
**Default Value:** `gpt-4o` (from .env.example)
**Required:** No
**Example Values:** `gpt-4o`, `gpt-4o-mini`, `deepseek-chat`, `claude-3-opus`

**Purpose:**
- Default model for default provider
- Must be valid model for `DEFAULT_LLM_PROVIDER`

**Popular Models:**
- OpenAI: `gpt-4o`, `gpt-4o-mini`
- DeepSeek: `deepseek-chat`
- Anthropic: `claude-3-opus`
- Zhipu: `glm-4-plus`

**Security Notes:**
- Verify model exists and is available
- Check pricing for usage

**Related Variables:**
- `DEFAULT_LLM_PROVIDER` - Must match provider

---

### Specialized LLM Configuration

### `BACKUP_LLM_PROVIDER`

**Variable Name:** `BACKUP_LLM_PROVIDER`
**Type:** String (provider name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `moonshot`, `deepseek`

**Purpose:**
- Backup LLM provider for fallback
- Used when primary provider fails

**Security Notes:**
- Ensure corresponding API key is set
- Test failover regularly

**Related Variables:**
- `BACKUP_LLM_MODEL` - Backup model selection

---

### `BACKUP_LLM_MODEL`

**Variable Name:** `BACKUP_LLM_MODEL`
**Type:** String (model name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `moonshot-v1-32k`

**Purpose:**
- Backup model for backup provider
- Used for failover scenarios

---

### `REASONING_LLM_PROVIDER`

**Variable Name:** `REASONING_LLM_PROVIDER`
**Type:** String (provider name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `deepseek`

**Purpose:**
- LLM provider for complex reasoning tasks
- May use more capable models

**Security Notes:**
- Typically more expensive
- Use for complex workflows only

**Related Variables:**
- `REASONING_LLM_MODEL` - Reasoning model selection

---

### `REASONING_LLM_MODEL`

**Variable Name:** `REASONING_LLM_MODEL`
**Type:** String (model name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `deepseek-reasoner`, `gpt-4o`

**Purpose:**
- Model for complex reasoning tasks
- Higher quality, slower, more expensive

---

### `CODING_LLM_PROVIDER`

**Variable Name:** `CODING_LLM_PROVIDER`
**Type:** String (provider name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `zhipu`, `openai`

**Purpose:**
- LLM provider optimized for code generation
- Used in code execution workflows

**Security Notes:**
- Code-specialized models recommended
- Test code output carefully

**Related Variables:**
- `CODING_LLM_MODEL` - Coding model selection

---

### `CODING_LLM_MODEL`

**Variable Name:** `CODING_LLM_MODEL`
**Type:** String (model name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `glm-4-plus`, `gpt-4o`

**Purpose:**
- Model for code generation tasks
- Should be code-optimized

---

### `CHINESE_LLM_PROVIDER`

**Variable Name:** `CHINESE_LLM_PROVIDER`
**Type:** String (provider name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `zhipu`

**Purpose:**
- LLM provider optimized for Chinese language
- Better performance on Chinese text

**Security Notes:**
- Use provider with good Chinese support
- Zhipu recommended

**Related Variables:**
- `CHINESE_LLM_MODEL` - Chinese model selection

---

### `CHINESE_LLM_MODEL`

**Variable Name:** `CHINESE_LLM_MODEL`
**Type:** String (model name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `glm-4-0520`

**Purpose:**
- Model for Chinese language tasks
- Optimized for Chinese text

---

### `ECONOMY_LLM_PROVIDER`

**Variable Name:** `ECONOMY_LLM_PROVIDER`
**Type:** String (provider name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `zhipu`

**Purpose:**
- Cost-effective LLM provider for high-volume tasks
- Used when quality requirements are lower

**Security Notes:**
- Lower cost typically means lower quality
- Monitor for acceptable performance

**Related Variables:**
- `ECONOMY_LLM_MODEL` - Economy model selection

---

### `ECONOMY_LLM_MODEL`

**Variable Name:** `ECONOMY_LLM_MODEL`
**Type:** String (model name)
**Default Value:** Not set (optional)
**Required:** No
**Example Values:** `glm-4-flash`

**Purpose:**
- Cost-effective model for high-volume tasks
- Faster, cheaper, lower quality

---

## Authentication & Security

### `SECRET_KEY`

**Variable Name:** `SECRET_KEY`
**Type:** String (hex)
**Default Value:** `""` (empty, required to set)
**Required:** Yes
**Example Values:** `a1b2c3d4e5f6...` (32+ hex characters)

**Purpose:**
- Secret key for JWT token signing
- Critical for authentication security

**Generation:**
```bash
# Python
python -c "import secrets; print(secrets.token_hex(32))"

# OpenSSL
openssl rand -hex 32
```

**Security Notes:**
- **CRITICAL:** Must be set in production
- Use cryptographically secure random generation
- 32+ bytes (256 bits) minimum
- Rotate periodically (quarterly recommended)
- **NEVER** share across environments
- **NEVER** commit to version control
- Changing invalidates all existing tokens

**Related Variables:**
- `ALGORITHM` - JWT signing algorithm
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token lifetime

---

### `ALGORITHM`

**Variable Name:** `ALGORITHM`
**Type:** String (algorithm name)
**Default Value:** `HS256` (from config.py)
**Required:** No
**Valid Values:** `HS256`, `RS256`

**Purpose:**
- JWT token signing algorithm
- Determines how tokens are cryptographically signed

**Options:**
- `HS256` - HMAC with SHA-256 (symmetric, recommended)
- `RS256` - RSA with SHA-256 (asymmetric, more complex)

**Recommendation:**
- Keep `HS256` for most deployments
- `RS256` only if you have PKI infrastructure

**Security Notes:**
- `HS256`: `SECRET_KEY` must be kept secret
- `RS256`: Private key must be kept secret

---

### `ACCESS_TOKEN_EXPIRE_MINUTES`

**Variable Name:** `ACCESS_TOKEN_EXPIRE_MINUTES`
**Type:** Integer (minutes)
**Default Value:** `11520` (8 days, from config.py: `60 * 24 * 8`)
**Required:** No
**Example Values:**
- Development: `1440` (1 day)
- Production: `11520` (8 days)
- Short-lived: `60` (1 hour)

**Purpose:**
- JWT token expiration time
- Users must re-authenticate after this period

**Recommendations:**
- High security: `60-480` (1-8 hours)
- Normal: `1440` (1 day)
- Convenience: `11520` (8 days)

**Security Notes:**
- Shorter tokens = better security
- Longer tokens = better UX
- Balance based on threat model
- Consider refresh token mechanism

**Related Variables:**
- `SECRET_KEY` - Used to sign tokens
- `ALGORITHM` - Signing algorithm

---

## Frontend Configuration

### `NEXT_PUBLIC_API_BASE_URL`

**Variable Name:** `NEXT_PUBLIC_API_BASE_URL`
**Type:** String (URL)
**Default Value:** `http://localhost:8090/api/v1` (from .env.example)
**Required:** Yes
**Example Values:**
- Development: `http://localhost:8090/api/v1`
- Production: `https://api.example.com/api/v1`
- Docker: `http://layra-backend:8090/api/v1`

**Purpose:**
- Frontend API endpoint
- Where the frontend sends API requests

**Special Behavior:**
- `NEXT_PUBLIC_` prefix makes variable available in browser
- Different from other env vars (server-only)

**Security Notes:**
- Must be accessible from user browsers
- Use HTTPS in production
- Should match `SERVER_IP` + `/api/v1`

**Related Variables:**
- `SERVER_IP` - Backend server URL
- `MINIO_PUBLIC_URL` - Public file access

---

### `NODE_ENV`

**Variable Name:** `NODE_ENV`
**Type:** Enum
**Default Value:** `production` (from .env.example)
**Required:** No
**Valid Values:** `development`, `production`

**Purpose:**
- Node.js environment mode
- Affects frontend build and runtime behavior

**Effects:**
- `development`:
  - Hot reloading enabled
  - Verbose error messages
  - Source maps available
  - Unoptimized builds
- `production`:
  - Optimized, minified builds
  - Error reporting enabled
  - Better performance
  - No debugging features

**Security Notes:**
- Use `production` in production deployments
- `development` mode exposes debugging information

---

## Multi-Tenancy Configuration

### `SINGLE_TENANT_MODE`

**Variable Name:** `SINGLE_TENANT_MODE`
**Type:** Boolean
**Default Value:** `false` (from config.py)
**Required:** No
**Valid Values:** `true`, `false`

**Purpose:**
- Controls data isolation between users
- Determines access control behavior

**Behavior:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| `false` | Multi-tenant: Users see only their own data | Production, multi-user |
| `true` | Single-tenant: All users see all data | Personal deployment, testing |

**Security Notes:**
- **CRITICAL:** Set to `false` in production
- `true` bypasses username-based access controls
- All data becomes visible to all users when `true`
- Useful for single-user deployments only

**Use Cases:**
- `false` (multi-tenant): Production, team deployments
- `true` (single-tenant): Personal instance, development, testing

---

## Security Considerations

### Critical Security Variables

These variables MUST be set and protected:

1. **`SECRET_KEY`** - JWT signing key
2. **`REDIS_PASSWORD`** - Redis authentication
3. **`MONGODB_ROOT_PASSWORD`** - MongoDB admin
4. **`MYSQL_ROOT_PASSWORD`** - MySQL root
5. **`MYSQL_PASSWORD`** - MySQL application user
6. **`MINIO_ACCESS_KEY`** - S3 access key
7. **`MINIO_SECRET_KEY`** - S3 secret key
8. **`OPENAI_API_KEY`** (or alternative) - LLM access

### Password Guidelines

**Strong Password Requirements:**
- Minimum 32 characters
- Mixed case (uppercase and lowercase)
- Numbers and special symbols
- No dictionary words or patterns
- Unique per service and environment

**Generation:**
```bash
# OpenSSL (recommended)
openssl rand -base64 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# /dev/urandom (Linux)
cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1
```

### API Key Protection

**Best Practices:**
1. Never commit .env files to version control
2. Add .env to .gitignore
3. Use different keys for dev/staging/prod
4. Rotate keys quarterly
5. Monitor usage for anomalies
6. Revoke compromised keys immediately
7. Set spending limits on paid APIs
8. Use organization-scoped keys when available

### Environment-Specific Security

| Environment | DEBUG_MODE | HTTPS | Password Strength | Key Rotation |
|-------------|------------|-------|-------------------|--------------|
| Development | `true` | Optional | Standard | Monthly |
| Staging | `false` | Recommended | Strong | Quarterly |
| Production | `false` | **Required** | **Strong (32+ chars)** | Quarterly |

### Data Privacy Considerations

**Local Embedding (`local_colqwen`):**
- No data leaves infrastructure
- Recommended for sensitive data
- Requires GPU with 16GB+ VRAM

**Cloud Embedding (`jina_embeddings_v4`):**
- Documents sent to Jina servers
- Review Jina's privacy policy
- Consider data residency requirements

**LLM Providers:**
- All prompts and responses sent to provider
- Review provider's data retention policies
- Enterprise agreements available for some providers
- Consider local models for sensitive data

---

## Common Pitfalls

### 1. Missing Required Variables

**Problem:** Application fails to start with validation errors.

**Solution:** Ensure all critical variables are set:
```bash
# Minimum required
SERVER_IP=http://localhost:8090
SECRET_KEY=<generate-strong-key>
DB_URL=<your-mysql-connection-string>
REDIS_URL=redis:6379
MONGODB_URL=mongodb://mongo:27017
MILVUS_URI=http://milvus:19530
OPENAI_API_KEY=<your-openai-key>
```

### 2. Weak or Default Passwords

**Problem:** Using default passwords from .env.example.

**Solution:** Generate strong passwords for all services:
```bash
# Generate unique passwords for each service
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)
MYSQL_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
MONGODB_ROOT_PASSWORD=$(openssl rand -base64 32)
MINIO_SECRET_KEY=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
```

### 3. DEBUG_MODE in Production

**Problem:** Exposes internal system details, performance impact.

**Solution:** Always set `DEBUG_MODE=false` in production:
```bash
# Production .env
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### 4. Mismatched URLs

**Problem:** Frontend can't reach backend, broken file downloads.

**Solution:** Ensure URLs are consistent:
```bash
# Backend URL
SERVER_IP=https://api.example.com

# Frontend should match
NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1

# MinIO public URL
MINIO_PUBLIC_URL=https://s3.example.com
MINIO_IMAGE_URL_PREFIX=https://cdn.example.com/files
```

### 5. Wrong Embedding Model Configuration

**Problem:** System tries to use GPU model without GPU, or vice versa.

**Solution:** Match embedding model to infrastructure:
```bash
# With GPU (RTX 4090, 16GB+ VRAM)
EMBEDDING_MODEL=local_colqwen
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2

# Without GPU
EMBEDDING_MODEL=jina_embeddings_v4
JINA_API_KEY=<your-jina-key>
```

### 6. Insufficient Connection Pools

**Problem:** Database connection errors under load.

**Solution:** Increase pool sizes based on load:
```bash
# For high traffic
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
MONGODB_POOL_SIZE=100
REDIS_URL=redis://redis:6379  # Use connection pooling
```

### 7. Wrong Redis Database Numbers

**Problem:** Data conflicts between different Redis databases.

**Solution:** Use unique database numbers:
```bash
REDIS_TOKEN_DB=0   # Auth tokens
REDIS_TASK_DB=1    # Task progress
REDIS_LOCK_DB=2    # Distributed locks
# Never use the same number for multiple purposes
```

### 8. Single Tenant Mode in Production

**Problem:** All users can see all data (security breach).

**Solution:** Always disable in production:
```bash
# Production .env
SINGLE_TENANT_MODE=false  # MUST be false!
```

### 9. Hardcoded Credentials

**Problem:** Credentials hardcoded in config files (anti-pattern).

**Solution:** Use environment variables:
```bash
# WRONG - Don't do this
minio_password = "thesis_redis_1c962832d09529674794ff43258d721c"

# CORRECT - Use env var
minio_password = os.getenv("MINIO_SECRET_KEY")
```

### 10. Missing LLM Provider Keys

**Problem:** Chat functionality doesn't work.

**Solution:** Set at least one LLM provider:
```bash
# Choose one or more
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Set default
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o
```

---

## Related Documentation

- **[Configuration Guide](../core/CONFIGURATION.md)** - Detailed configuration scenarios
- **[Stack SSOT](../ssot/stack.md)** - System architecture and service dependencies
- **[Quick Start](../getting-started/QUICKSTART.md)** - Get Layra running in 5 minutes
- **[Database Documentation](../core/DATABASE.md)** - Database schemas and operations
- **[Embeddings Pipeline](../core/EMBEDDINGS.md)** - Embedding model setup and usage
- **[Troubleshooting](../operations/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Credentials SSOT](../ssot/CREDENTIALS.md)** - Credential management best practices

---

## Variables Lacking Defaults

The following variables are required but have no default value in config.py. These MUST be set in your .env file:

**Critical (System Won't Start Without These):**
- `SECRET_KEY` - JWT signing key
- `DB_URL` - MySQL connection string
- `REDIS_PASSWORD` - Redis authentication
- `MONGODB_ROOT_USERNAME` - MongoDB admin user
- `MONGODB_ROOT_PASSWORD` - MongoDB admin password
- `MINIO_ACCESS_KEY` - MinIO access key
- `MINIO_SECRET_KEY` - MinIO secret key
- `MILVUS_URI` - Milvus connection URI

**At Least One LLM Provider Key Required:**
- `OPENAI_API_KEY` (recommended)
- `DEEPSEEK_API_KEY` (alternative)
- `ANTHROPIC_API_KEY` (alternative)
- Or any other supported LLM provider

---

## Validation Checklist

Before deploying, verify:

- [ ] All required variables are set
- [ ] Strong passwords generated (32+ characters)
- [ ] `DEBUG_MODE=false` in production
- [ ] `SINGLE_TENANT_MODE=false` in production
- [ ] At least one LLM provider API key set
- [ ] URLs are consistent (`SERVER_IP`, `NEXT_PUBLIC_API_BASE_URL`)
- [ ] Embedding model matches infrastructure (GPU vs cloud)
- [ ] Redis database numbers are unique
- [ ] Connection pools sized for expected load
- [ ] HTTPS enabled for production URLs
- [ ] `.env` file not committed to version control
- [ ] `.env` file has correct permissions (600)

---

**Document Version:** 2.1.0
**Last Updated:** 2026-01-27
**Maintained By:** Layra Development Team
**For Issues:** [GitHub Issues](https://github.com/liweiphys/layra/issues)

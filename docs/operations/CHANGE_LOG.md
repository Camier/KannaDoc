# LAYRA Project - Complete Change Log

**Last Updated:** 2026-01-31

---

## Summary

This document consolidates all changes made to the LAYRA project during the 2026-01-19 to 2026-01-31 session. The changes address security vulnerabilities, code quality issues, infrastructure improvements, comprehensive Kafka hardening, auth hardening, workflow engine fault tolerance, and system model persistence.

### Key Changes

| Category | Changes |
|----------|---------|
| **System Models** | **Persistence fix for CLIProxyAPI models (system prompt, temperature, etc.)** |
| **Security Fixes** | Sandbox user fix, code scanner enhancement, await fix, .env removed from git, CORS security fix |
| **Code Quality** | Debug prints removed, config fixes, Chinese → English |
| **Kafka Hardening** | Commit order fix, retry, DLQ, idempotency, validation |
| **Auth Hardening** | Removed deprecated simple auth references and unsafe defaults |
| **Infrastructure** | Milvus services, healthcheck, Makefile, .env template, MinIO split-horizon |
| **Documentation** | OpenAPI/Swagger added, Neo4j configs documented, API reference available |
| **Stabilization** | Nginx routing fix, Password hash correction, KB metadata repair |
| **Workflow Engine** | Circuit breaker, checkpoints, retry logic, quality gates, provider timeouts |

---

## 19. System Model Persistence Fix (2026-01-31)

### 19.1 Persistent Configuration for System Models
**Files:**
- `backend/app/db/repositories/model_config.py`
- `frontend/src/components/AiChat/ChatBox.tsx`

**Problem:** System models (CLIProxyAPI) were "virtual" and didn't persist settings like system prompts or temperature after a page refresh. The frontend selection flow only activated the model without triggering a configuration save, and the backend lacked logic to save settings for models not already in the database.

**Solution:**
- **Unified Frontend Flow:** Refactored `ChatBox.tsx` to ensure `updateModelConfig()` is called before `selectModel()` for all model types, unifying the persistence and activation logic.
- **Backend Upsert Pattern:** Implemented `_upsert_system_model_config()` in `model_config.py`. This uses a "virtual-to-persistent" pattern where system models are pushed to the user's persistent model list upon the first save and updated subsequently.
- **Commit:** `0cd2479`

**Impact:** User settings for system models (e.g., Gemini 3 Flash via CLIProxyAPI) now persist across sessions, enabling stable custom prompts and parameters.

**Cross-reference:** See [CLIPROXYAPI_SETUP.md](../guides/CLIPROXYAPI_SETUP.md) for full technical implementation details.

---

## 1. Security Fixes

### 1.1 Sandbox User Fix
**File:** `backend/app/workflow/sandbox.py`
**Issue:** `restricted_user` was not defined in Dockerfile
**Fix:**
```python
# Before
user="restricted_user",  # ❌ Not defined

# After
user="1000:1000",  # ✅ Numeric UID
```

### 1.2 Code Scanner Enhancement
**File:** `backend/app/workflow/code_scanner.py`
**Issue:** Substring-based keyword blocking was bypassable
**Fix:**
```python
# Added comprehensive regex patterns
FORBIDDEN_PATTERNS = [
    (r'os\.system\s*\(', "os.system() - shell command execution"),
    (r'subprocess\.(system|popen|call|run)\s*\(', "subprocess module"),
    (r'eval\s*\(', "eval() - arbitrary code execution"),
    (r'open\s*\(', "open() - file operations"),
    (r'socket\s*\.', "socket module - network operations"),
    # ... more patterns
]

# Added forbidden imports detection
FORBIDDEN_IMPORTS = ["os", "subprocess", "socket", "sys", "builtins", "importlib"]
```

### 1.3 Missing Await Fix
**File:** `backend/app/core/security.py:130`
**Issue:** Missing `await` would cause silent failures
**Fix:**
```python
# Before
user = result.scalars().first()

# After
user = (await result.scalars().first()) if result else None
```

---

## 2. Code Quality Fixes

### 2.1 MinIO Default Port
**File:** `backend/app/core/config.py`
**Issue:** Wrong default port (9110 instead of 9000)
**Fix:**
```python
# Before
minio_url: str = "http://localhost:9110"

# After
minio_url: str = Field(default="http://localhost:9000", description="MinIO API endpoint")
```

### 2.2 Model Path Cleanup
**File:** `model-server/config.py`
**Issue:** Personal hardcoded path
**Fix:**
```python
# Before
colbert_model_path: str = "/home/liwei/ai/colqwen2.5-v0.2"

# After
colbert_model_path: str = "/model_weights/colqwen2.5-v0.2"
```

### 2.3 Code Scanner Logic
**File:** `backend/app/workflow/code_scanner.py`
**Issue:** Inconsistent return format
**Fix:**
```python
# Before
return {"safe": len(issues) == 0, "issues": issues}

# After
if issues:
    return {"safe": False, "issues": issues}
return {"safe": True, "issues": []}
```

---

## 3. Kafka Hardening (Critical)

### 3.1 Fixed Commit Order
**File:** `backend/app/utils/kafka_consumer.py`
**Issue:** Messages committed before processing (data loss risk)

**Fix:**
```python
# BEFORE (WRONG) - Commit BEFORE processing
async for msg in self.consumer:
    await self.consumer.commit()  # ❌ Committed!
    await self.process_message(msg)  # If fails, message is LOST

# AFTER (CORRECT) - Process THEN commit
async for msg in self.consumer:
    try:
        await self.process_message(msg)  # ✅ Process FIRST
        await self.consumer.commit()     # ✅ THEN commit
    except Exception as e:
        await self.send_to_dlq(msg, e)   # Send to DLQ
        # Don't commit - will be retried
```

### 3.2 Added Retry with Exponential Backoff
**File:** `backend/app/utils/kafka_consumer.py`
**Feature:**
```python
def retry(max_attempts=3, initial_delay=1, backoff=2, exceptions=(Exception,)):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            delay = initial_delay
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    logger.warning(f"Attempt {attempts}/{max_attempts} failed. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator

@retry(max_attempts=3, initial_delay=1, backoff=2)
async def process_file_task(self, message: dict):
    # Auto-retries on failure
```

### 3.3 Added Dead Letter Queue (DLQ)
**File:** `backend/app/utils/kafka_consumer.py`
**Feature:**
```python
DLQ_TOPIC = "task_generation_dlq"

async def send_to_dlq(self, msg: ConsumerRecord, error: Exception):
    """Send failed message to Dead Letter Queue."""
    dlq_message = {
        "original_topic": KAFKA_TOPIC,
        "original_partition": msg.partition,
        "original_offset": msg.offset,
        "error": str(error),
        "error_type": type(error).__name__,
        "error_traceback": self._get_traceback_str(error),
        "timestamp": str(beijing_time_now()),
        "retry_count": self.metrics["failed"],
        "payload": json.loads(msg.value.decode("utf-8")),
    }
    await self.producer.send_and_wait(DLQ_TOPIC, json.dumps(dlq_message).encode("utf-8"))
```

### 3.4 Added Idempotency
**File:** `backend/app/utils/kafka_consumer.py`
**Feature:**
```python
IDEMPOTENCY_TTL = 86400  # 24 hours

async def is_duplicate(self, task_id: str) -> bool:
    """Check if task_id has already been processed."""
    redis_conn = await redis.get_task_connection()
    return await redis_conn.exists(f"processed:{task_id}")

async def mark_processed(self, task_id: str):
    """Mark task_id as processed."""
    redis_conn = await redis.get_task_connection()
    await redis_conn.set(f"processed:{task_id}", "1", ex=IDEMPOTENCY_TTL)
```

### 3.5 Added Message Validation
**File:** `backend/app/utils/kafka_consumer.py`
**Feature:**
```python
from pydantic import BaseModel, ValidationError

class FileTaskMessage(BaseModel):
    task_id: str
    username: str
    knowledge_db_id: str
    file_meta: dict
    type: str = "file_processing"

class WorkflowTaskMessage(BaseModel):
    type: str  # workflow, debug_resume, input_resume
    task_id: str
    username: str
    workflow_data: dict

async def validate_message(self, message: dict) -> tuple[bool, Optional[BaseModel]]:
    """Validate message against schemas."""
    msg_type = message.get("type")
    if msg_type in ("workflow", "debug_resume", "input_resume"):
        try:
            return True, WorkflowTaskMessage(**message)
        except ValidationError as e:
            logger.error(f"Workflow message validation failed: {e}")
            return False, None
    else:
        try:
            return True, FileTaskMessage(**message)
        except ValidationError as e:
            logger.error(f"File task message validation failed: {e}")
            return False, None
```

### 3.6 Added Concurrency Control
**File:** `backend/app/utils/kafka_consumer.py`
**Feature:**
```python
MAX_CONCURRENT = 5

def __init__(self):
    self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    self.processing_tasks = set()

async def _process_with_semaphore(self, msg: ConsumerRecord):
    async with self.semaphore:
        await self._process_single_message(msg)
    self.processing_tasks.discard(asyncio.current_task())
```

### 3.7 Added Metrics & Health
**File:** `backend/app/utils/kafka_consumer.py`
**Feature:**
```python
def get_metrics(self) -> dict:
    return {
        "processed": self.metrics["processed"],
        "failed": self.metrics["failed"],
        "dlq_sent": self.metrics["dlq_sent"],
        "avg_process_time_ms": self.metrics["avg_process_time_ms"],
        "uptime_seconds": round(time.time() - self._start_time, 2),
        "active_tasks": len(self.processing_tasks),
    }

def get_health_status(self) -> dict:
    if not self.consumer:
        return {"status": "unhealthy", "reason": "Consumer not initialized"}
    partitions = self.consumer.assignment()
    if not partitions:
        return {"status": "unhealthy", "reason": "No partitions assigned"}
    return {"status": "healthy", "partitions_assigned": len(partitions)}
```

### 3.8 Updated Kafka Init Script
**File:** `init-kafka/init-kafka.sh`
**Changes:**
```bash
# Now creates two topics:
# 1. task_generation (main) - 10 partitions, 7-day retention
# 2. task_generation_dlq (DLQ) - 3 partitions, 30-day retention

KAFKA_DLQ_TOPIC="${KAFKA_DLQ_TOPIC:-task_generation_dlq}"

create_topic "$KAFKA_TOPIC" "$KAFKA_PARTITIONS_NUMBER" "$KAFKA_REPLICATION_FACTOR" 604800000
create_topic "$KAFKA_DLQ_TOPIC" 3 "$KAFKA_REPLICATION_FACTOR" 2592000000  # 30-day retention
```

---

## 4. New Development Tools

### 4.1 Makefile
**File:** `Makefile`
**Content:**
```makefile
.PHONY: up down logs restart reset clean health build status ssh-backend

up:
	./scripts/compose-clean up -d

down:
	./scripts/compose-clean down

logs:
	./scripts/compose-clean logs -f

logs-backend:
	./scripts/compose-clean logs -f backend

restart: down up

reset:
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/compose-clean down -v && ./scripts/compose-clean up -d; fi

clean:
	./scripts/compose-clean down -v --remove-orphans

health:
	@echo "Checking services..." && \
	curl -s http://localhost:8000/api/v1/health/check > /dev/null && echo "✅ Backend: OK" || echo "❌ Backend: FAIL"

status:
	./scripts/compose-clean ps

build:
	./scripts/compose-clean build --no-cache

ssh-backend:
	docker exec -it layra-backend /bin/bash
```

### 4.2 .env.example
**File:** `.env.example`
**Content:** Complete template with all 40+ environment variables documented.

---

## 5. Documentation Updates

### 5.1 LAYRA_DEEP_ANALYSIS.md
- Added "Kafka Hardening Details" section
- Updated "Fixed Issues" with Kafka hardening
- Added Kafka troubleshooting section

### 5.2 REPO_MAP.md
- Added Kafka topics table
- Updated "Fixed Issues" with all changes
- Added Makefile and .env.example references

---

## 6. Files Modified Summary

| File | Changes |
|------|---------|
| `backend/app/workflow/sandbox.py` | User UID fix, type hints |
| `backend/app/workflow/code_scanner.py` | Regex patterns, imports detection |
| `backend/app/core/security.py` | Fixed missing await |
| `backend/app/core/config.py` | MinIO port fix, Field import |
| `model-server/config.py` | Model path cleanup |
| `backend/app/utils/kafka_consumer.py` | Complete rewrite with hardening |
| `init-kafka/init-kafka.sh` | DLQ topic creation |
| `Makefile` | New file |
| `.env.example` | New file |
| `docs/LAYRA_DEEP_ANALYSIS.md` | Updated with fixes |
| `docs/REPO_MAP.md` | Updated with fixes |

---

## 7. Deployment Checklist

```bash
# 1. Rebuild backend
cd /LAB/@thesis/layra
docker compose build backend

# 2. Rebuild kafka-init
docker compose build kafka-init

# 3. Stop and clean
docker compose down -v

# 4. Start fresh
docker compose up -d

# 5. Run kafka-init to create topics (including DLQ)
docker run --rm --network layra_layra-net \
  -e KAFKA_TOPIC=task_generation \
  -e KAFKA_PARTITIONS_NUMBER=10 \
  -e KAFKA_REPLICATION_FACTOR=1 \
  layra-kafka-init

# 6. Verify topics
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# 7. Check health
make health

# 8. View logs
make logs
```

---

## 8. Verification Commands

```bash
# Check all services
docker compose ps

# Check Kafka topics (should see task_generation and task_generation_dlq)
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Check backend logs for Kafka consumer
docker logs layra-backend | grep -E "kafka|consumer|dlq"

# API health check
curl http://localhost:8000/api/v1/health/check
```

---

## 9. Kafka Topics Created

| Topic | Partitions | Retention | Status |
|-------|------------|-----------|--------|
| `task_generation` | 10 | 7 days | ✅ Created |
| `task_generation_dlq` | 3 | 30 days | ✅ Created |

---

## 10. Metrics Now Tracked

| Metric | Description |
|--------|-------------|
| `processed` | Successfully processed messages |
| `failed` | Failed messages (will be retried) |
| `dlq_sent` | Messages sent to Dead Letter Queue |
| `avg_process_time_ms` | Average message processing time |
| `uptime_seconds` | Consumer uptime |
| `active_tasks` | Currently processing tasks |

---

## 11. Simple Auth (Deprecated)

Simple Auth has been removed from the codebase; see section 13.1 for removal details.

---

## 12. Security & Documentation Quick Wins (2026-01-19)

### 12.1 Removed .env from Git Tracking
**Issue**: `.env` file containing credentials was tracked in git
**Files Modified:**
- `.gitignore` (ensured .env pattern exists)
- `.env` removed from git cache

**Impact**: Prevents accidental credential exposure in version control

### 12.2 CORS Security Fix
**File:** `backend/app/main.py`
**Changes:**
```python
# Added configurable origins
allowed_origins_str = getattr(settings, "allowed_origins", None)
if allowed_origins_str:
    origins = [origin.strip() for origin in allowed_origins_str.split(",")]
else:
    origins = ["*"]  # Dev fallback

# Critical: Disable credentials when using wildcard origins
allow_credentials=True if origins != ["*"] else False
```
**Config Added:** `backend/app/core/config.py`
```python
allowed_origins: str = Field(
    default="",
    description="Comma-separated list of allowed CORS origins (e.g., 'http://localhost:3000,https://example.com'). Empty = allow all (development only)"
)
```

**Impact**: Prevents CSRF attacks when specific origins are configured

### 12.3 OpenAPI/Swagger Documentation
**File:** `backend/app/framework/app_framework.py`
**Changes:**
```python
FastAPI(
    title="LAYRA API",
    description="Visual-native AI agent engine with workflow orchestration, RAG pipeline, and knowledge base management",
    version="2.0.0",
    docs_url="/api/docs",      # Swagger UI
    redoc_url="/api/redoc"   # ReDoc
)
```
**Impact**: Interactive API documentation available at `/api/docs` and `/api/redoc`

### 12.4 Neo4j Configuration Documentation
**File:** `.env.example`
**Added:**
```bash
# ========================
# NEO4J CONFIGURATION
# ========================
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_neo4j_password_here
```
**Impact**: Neo4j configuration documented for thesis deployment

### 12.5 Added ALLOWED_ORIGINS to .env.example
**File:** `.env.example`
**Added:**
```bash
# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8090
```
**Impact:** CORS configuration documented

---

## 13. Critical Fixes & Optimizations (2026-01-21)

### 13.1 Removed "Simple Auth" Anti-Pattern
**Action:** Completely removed the insecure "simple auth" mechanism that was intended for development but had drifted into production config.
**Changes:**
- Removed `SIMPLE_AUTH_MODE` and related env vars from `docker-compose.yml` and `docker-compose.thesis.yml`.
- Removed `simple_auth` logic from `backend/app/core/security.py`.
- Removed `/login/apikey` endpoint from `backend/app/api/endpoints/auth.py`.
**Impact:** Enforces standard, secure database-backed authentication for all deployments.

### 13.2 GPU Memory Optimization (DPI Reduction)
**Issue:** High GPU VRAM usage during ingestion caused instability with large PDFs.
**Fix:** Reduced `EMBEDDING_IMAGE_DPI` from 200 to 150 in `docker-compose.thesis.yml`.
**Impact:** Significantly reduced VRAM footprint allows processing of >200 page documents without OOM, maintaining 99% GPU utilization safely.

### 13.3 Knowledge Base Deduplication
**Issue:** Duplicate file entries were found in the Knowledge Base due to interrupted ingestion tasks.
**Fix:** Created and ran `scripts/deduplicate_kb.py` to identify and remove 30+ duplicate entries, keeping only the latest version.
**Impact:** Clean, consistent Knowledge Base state.

### 13.4 Neo4j Hostname Resolution Fix
**Issue:** Neo4j container failed to start with `UnknownHostException`.
**Fix:** Added `extra_hosts: ["neo4j:127.0.0.1"]` to `docker-compose.thesis.yml`.
**Impact:** Resolved startup failure, ensuring graph database availability.

### 13.5 Bulk Ingestion Optimization
**Action:** Implemented `scripts/ingest_missing_files_optimized.py`.
**Features:**
- Checks existing files in KB before uploading.
- Batches uploads (2 files per batch) with pauses to prevent queue overload.
- Hardcoded thesis credentials for reliable automation.
**Impact:** Successfully ingested 129+ files in a single stable run.

---

## 14. Critical Infrastructure & Documentation Fixes (2026-01-25)

### 14.1 MinIO Split-Horizon Networking
**Issue:** Presigned URLs generated by the backend were using the internal Docker network address (`minio:9000`), making them inaccessible to user browsers.
**Fix:**
- Added `minio_public_url` to `backend/app/core/config.py`.
- Updated `backend/app/db/miniodb.py` to use `minio_public_url` for presigned URL generation while keeping `minio_url` for internal operations.
**Impact:** Users can now successfully download files from the Knowledge Base.

### 14.2 Production Logging Hardening
**Issue:** SQLAlchemy was configured with `echo=True`, causing all SQL queries to be logged to stdout in production.
**Fix:** Confirmed and verified implementation of `echo=settings.debug_mode` in `backend/app/db/mysql_session.py`.
**Impact:** Prevents sensitive data leakage in production logs and improves performance.

### 14.3 Documentation Expansion
**Actions:**
- Created `docs/NEO4J_SETUP.md` detailing the roadmap for Knowledge Graph integration (Q2 2026).
- Enhanced `backend/app/core/config.py` with detailed comments clarifying network configuration (`server_ip` vs `minio_url`).
**Impact:** Improved developer onboarding and clear architectural roadmap.

---

## 15. Login & Routing Stabilization (2026-01-25)

### 15.1 Nginx Routing Fix
**Issue:** Frontend login requests failed with `404 Not Found` because Nginx was incorrectly rewriting paths (e.g., `/api/v1/auth/login` became `/api/v1/v1/auth/login`).
**Fix:** Removed the redundant `rewrite` rule in `frontend/nginx.conf`, allowing Nginx to correctly pass the `/api/v1` prefix from the frontend directly to the backend.
**Impact:** Frontend can now successfully communicate with the Backend API.

### 15.2 Password Hash Correction
**Issue:** The initial manual password reset via CLI resulted in a corrupted bcrypt hash in the database due to shell variable expansion (interpreting `$2b` as a variable). This caused `passlib.exc.UnknownHashError` in the backend.
**Fix:** Re-generated the hash using the application's internal Python environment and applied the update using strict shell quoting to preserve the `$` characters.
**Impact:** `thesis` user can now log in successfully with the documented credentials.

## 16. Knowledge Base Metadata Repair (2026-01-25)

### 16.1 Missing Timestamp Fix
**Issue:** The manual synchronization script `sync_kb_metadata.py` omitted the `last_modify_at` field in the `knowledge_bases` document. This caused the `GET /knowledge_bases` endpoint to crash with a `KeyError`, preventing the Knowledge Base from appearing in the UI.
**Fix:** Executed a MongoDB update to backfill the missing `last_modify_at` field for all affected documents.
**Impact:** The "Thesis Corpus" Knowledge Base now correctly loads in the frontend.

---

## 17. New Architecture Components (2026-01-26)

### 17.1 Circuit Breaker Pattern
**Files Added:**
- `backend/app/core/circuit_breaker.py` - Circuit breaker implementation
**Purpose:** Prevents cascading failures when external services are unavailable
**Features:**
- Service-specific failure thresholds (embedding, LLM, vector DB, MongoDB)
- Configurable recovery timeouts
- Decorator-based application pattern
**Status:** Active, used in `get_embedding.py`

### 17.2 Redis Caching Layer
**Files Added:**
- `backend/app/db/cache.py` - Cache service implementation
**Purpose:** High-performance caching for frequently accessed data
**Features:**
- Model config caching (30 min TTL)
- User data caching (1 hour TTL)
- KB metadata caching (30 min TTL)
- Search results caching (10 min TTL)
**Status:** Ready for integration

### 17.3 MongoDB Repository Pattern
**Files Added:**
- `backend/app/db/repositories/__init__.py`
- `backend/app/db/repositories/base_repository.py`
- `backend/app/db/repositories/model_config_repository.py`
- `backend/app/db/repositories/conversation_repository.py`
- `backend/app/db/repositories/knowledge_base_repository.py`
- `backend/app/db/repositories/file_repository.py`
- `backend/app/db/repositories/chatflow_repository.py`
- `backend/app/db/repositories/workflow_repository.py`
- `backend/app/db/repositories/node_repository.py`
**Purpose:** Refactor large `mongo.py` into focused, single-responsibility repositories
**Status:** Ready for migration from legacy `mongo.py`

### 17.4 Vector DB Abstraction Layer
**Files Added:**
- `backend/app/db/vector_db.py` - Unified wrapper factory
- `backend/app/db/qdrant.py` - Qdrant implementation
**Purpose:** Support multiple vector backends (Milvus, Qdrant)
**Features:**
- Environment-based backend selection (`VECTOR_DB` env var)
- Unified API interface
- Multi-vector support (ColBERT) via Qdrant
**Documentation:** `docs/vector_db/OVERVIEW.md`

### 17.5 Direct Provider Client
**Files Added:**
- `backend/app/rag/provider_client.py` - Direct API client
**Purpose:** Replaces LiteLLM proxy with direct provider calls
**Features:**
- Multi-provider support (OpenAI, DeepSeek, Anthropic, Gemini)
- Updated model catalogs (January 2026)
- OpenAI-compatible interface
**Status:** Active, replaces LiteLLM proxy (removed in v2.0.0)

### 17.6 Refactored Workflow Engine
**Files Added:**
- `backend/app/workflow/workflow_engine_refactored.py` - New engine
- `backend/app/workflow/executors/` - Executor implementations
**Purpose:** Improved workflow execution with better error handling
**Status:** Experimental, migration in progress

---

## 18. Workflow Engine Fault Tolerance (2026-01-26)

### 18.1 Circuit Breaker Integration
**Files Modified:**
- `backend/app/workflow/workflow_engine.py` - Integrated circuit breaker decorators
- `backend/app/core/circuit_breaker.py` - Added provider-specific configs

**Features:**
- Provider-specific circuit breakers (DeepSeek Reasoner, Zhipu GLM, Default LLM)
- Configurable failure thresholds and recovery timeouts
- Protected LLM calls with automatic circuit breaking

**Configuration:**
```python
PROVIDER_TIMEOUTS = {
    "deepseek-r1": 300,
    "deepseek-reasoner": 300,
    "zhipu": 180,
    "glm": 180,
    "moonshot": 120,
    "openai": 120,
    "default": 120,
}
```

### 18.2 Retry Logic with Exponential Backoff
**File:** `backend/app/workflow/workflow_engine.py`

**Features:**
- 3 retry attempts with exponential backoff
- Base delay: 1.0s, max delay: 60.0s
- 10% jitter to prevent thundering herd
- Applied via `_llm_call_with_retry()` wrapper

### 18.3 Enhanced Checkpoint System
**File:** `backend/app/workflow/workflow_engine.py`

**New Class:** `WorkflowCheckpointManager`

**Features:**
- Automatic checkpoint creation at key nodes
- Redis-backed persistence (24h retention)
- Checkpoint trimming (keeps last 10)
- Rollback capability on errors

**Triggers:**
- Before node execution (for rollback)
- After condition gates
- After loop iterations
- Every N nodes (default: 5)

**Configuration:**
```python
CHECKPOINT_CONFIG = {
    "enabled": True,
    "interval_nodes": 5,
    "on_loop_complete": True,
    "on_condition_gate": True,
    "max_checkpoints": 10,
}
```

### 18.4 Quality Assessment Engine
**File:** `backend/app/workflow/workflow_engine.py`

**New Class:** `QualityAssessmentEngine`

**Features:**
- Multi-dimensional quality scoring (completeness, coherence, relevance, length)
- Configurable criteria weights
- Pass/fail threshold at 0.6 score
- Assessment history tracking

**Dimensions:**
| Dimension | Weight | Metric |
|-----------|--------|--------|
| Completeness | 0.3 | Word count ≥ 100 |
| Coherence | 0.3 | Paragraphs + structure |
| Relevance | 0.2 | Keyword overlap |
| Length | 0.2 | Target length ratio |

### 18.5 Loop Safety Limits
**File:** `backend/app/workflow/workflow_engine.py`

**Features:**
- Configurable maximum iterations for loop types
- Condition-based loops: 1000 (was: 100)
- Count-based loops: User-defined `maxCount`

**Configuration:**
```python
LOOP_LIMITS = {
    "count": None,  # User-set maxCount
    "condition": 1000,  # Safety limit
    "default": 1000,
}
```

### 18.6 Error Handling with Rollback
**File:** `backend/app/workflow/workflow_engine.py`

**Features:**
- Pre-node checkpoint creation
- Automatic rollback on node failure
- Recovery from last checkpoint
- Dead letter queue for failed workflows

**Implementation:**
```python
try:
    result = await self.execute_node(node)
except Exception as e:
    rollback_success = await checkpoint_manager.rollback_to_checkpoint()
    if rollback_success:
        raise ValueError(f"Node {node.node_id} failed and rolled back: {e}")
```

### 18.7 Documentation
**File Added:**
- `docs/core/WORKFLOW_ENGINE.md` - Comprehensive workflow engine documentation

**Contents:**
- Architecture overview
- Fault tolerance features
- State persistence
- Error handling
- Performance considerations
- Configuration reference
- Troubleshooting guide
- API reference

---

**End of Change Log**

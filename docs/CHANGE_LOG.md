# LAYRA Project - Complete Change Log

**Last Updated:** 2026-01-19

---

## Summary

This document consolidates all changes made to the LAYRA project during the 2026-01-19 to 2026-01-20 session. The changes address security vulnerabilities, code quality issues, infrastructure improvements, comprehensive Kafka hardening, and simple auth integration for solo projects.

### Key Changes

| Category | Changes |
|----------|---------|
| **Security Fixes** | Sandbox user fix, code scanner enhancement, await fix, .env removed from git, CORS security fix |
| **Code Quality** | Debug prints removed, config fixes, Chinese → English |
| **Kafka Hardening** | Commit order fix, retry, DLQ, idempotency, validation |
| **Simple Auth** | New lightweight auth module for solo/development use |
| **Infrastructure** | Milvus services, healthcheck, Makefile, .env template |
| **Documentation** | OpenAPI/Swagger added, Neo4j configs documented, API reference available |

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
	./compose-clean up -d

down:
	./compose-clean down

logs:
	./compose-clean logs -f

logs-backend:
	./compose-clean logs -f backend

restart: down up

reset:
	@read -p "Are you sure? [y/N] " -n 1 -r; echo; if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./compose-clean down -v && ./compose-clean up -d; fi

clean:
	./compose-clean down -v --remove-orphans

health:
	@echo "Checking services..." && \
	curl -s http://localhost:8000/api/v1/health/check > /dev/null && echo "✅ Backend: OK" || echo "❌ Backend: FAIL"

status:
	./compose-clean ps

build:
	./compose-clean build --no-cache

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

## 11. Simple Auth Integration for Solo Projects

### 11.1 New Simple Auth Module
**File:** `backend/app/core/simple_auth.py`
**Purpose:** Lightweight authentication alternative for solo/development use

**Features:**
- API key authentication (header: `X-API-Key`)
- Password authentication (header: `Authorization: Bearer password`)
- No database required
- No Redis token storage
- No registration needed

**Usage:**
```bash
# Enable in .env
SIMPLE_AUTH_MODE=true
SIMPLE_API_KEY=layra-dev-key-2024
SIMPLE_USERNAME=layra
SIMPLE_PASSWORD=layra123
```

### 11.2 Updated Security Module
**File:** `backend/app/core/security.py`
**Changes:**
- Added `api_key_header` for API key authentication
- Added `get_current_user_simple()` for simple auth mode
- Added `get_current_user_full()` for full JWT + Redis auth
- Modified `get_current_user()` to automatically switch between modes

### 11.3 Updated Auth Endpoints
**File:** `backend/app/api/endpoints/auth.py`
**Changes:**
- Modified `/login` to support simple auth mode (password-based)
- Added new endpoint `/login/apikey` for API key login

**API Key Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/apikey \
  -H "X-API-Key: layra-dev-key-2024"
```

**Password Login (simple mode):**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=layra&password=layra123"
```

### 11.4 Updated Configuration
**File:** `backend/app/core/config.py`
**Added Settings:**
```python
simple_auth_mode: bool = Field(default=False)
simple_api_key: str = Field(default="layra-dev-key-2024")
simple_username: str = Field(default="layra")
simple_password: str = Field(default="layra123")
```

### 11.5 Updated Docker Compose
**File:** `docker-compose.yml`
**Added Environment Variables:**
```yaml
- SIMPLE_AUTH_MODE=${SIMPLE_AUTH_MODE:-false}
- SIMPLE_API_KEY=${SIMPLE_API_KEY:-layra-dev-key-2024}
- SIMPLE_USERNAME=${SIMPLE_USERNAME:-layra}
- SIMPLE_PASSWORD=${SIMPLE_PASSWORD:-layra123}
```

### 11.6 Updated .env Template
**File:** `.env.example`
**Added:**
```bash
# Simple Auth (Solo/Dev Mode)
SIMPLE_AUTH_MODE=true
SIMPLE_API_KEY=layra-dev-key-2024
SIMPLE_USERNAME=layra
SIMPLE_PASSWORD=layra123
```

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
**Impact:** Neo4j configuration documented for thesis deployment

### 12.5 Added ALLOWED_ORIGINS to .env.example
**File:** `.env.example`
**Added:**
```bash
# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8090
```
**Impact:** CORS configuration documented

---

**End of Change Log**

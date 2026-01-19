# LAYRA Project Deep Technical Analysis

## Overview

**LAYRA** is a "visual-native" AI automation engine that combines document understanding with agent workflow orchestration. It treats documents as visual entities (preserving layout/tables/charts) rather than token sequences.

---

## Architecture Overview

```
User → Nginx (8090) → FastAPI Backend → [Kafka, Redis, MySQL, MongoDB, MinIO, Milvus]
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              Model Server         Unoserver         Python Sandbox
              (ColQwen2.5)         (Doc→Images)       (Docker exec)
              GPU: RTX 3090
```

---

## Core Components

| Service | Purpose | Port | Status |
|---------|---------|------|--------|
| **Frontend** | Next.js 15 + TailwindCSS UI | 3000 | ✅ Running |
| **Backend** | FastAPI orchestration | 8000 | ✅ Healthy |
| **Nginx** | Reverse proxy | 8090 | ✅ Running |
| **Kafka** | Async task queue | 9092 | ✅ Healthy |
| **MySQL** | Auth/users | 3306 | ✅ Healthy |
| **MongoDB** | Chat history/workflows | 27017 | ✅ Healthy |
| **Redis** | Caching/state | 6379 | ✅ Healthy |
| **MinIO** | Object storage | 9000 | ✅ Healthy |
| **Milvus** | Vector database | 19530 | ✅ Healthy |
| **Model Server** | ColQwen2.5 embeddings | 8005 | ✅ Healthy |
| **Unoserver** | Document conversion | 2003 | ✅ Healthy |
| **Python Sandbox** | Code execution | - | ✅ Running |

---

## Quick Start

```bash
# Start all services
cd /LAB/@thesis/layra
./compose-clean up -d

# Check status
./compose-clean ps

# View logs
./compose-clean logs -f backend

# Access UI
# Open http://localhost:8090
```

---

## 1. Workflow Engine Deep Dive

### Execution Model (`workflow_engine.py`)

The workflow engine uses a **tree-based execution model** with stack-based traversal:

```python
class WorkflowEngine:
    execution_stack = [self.graph[1]]  # Stack-based execution
    execution_status = {node["id"]: False}  # Node completion tracking
    loop_index = {}  # Loop iteration counters
    breakpoints = set()  # Debug breakpoints
```

**Execution Flow:**
1. DAG validation via `WorkflowGraph`
2. Stack-based depth-first traversal
3. Node-type specific handlers:
   - `handle_condition()` - Python expression evaluation
   - `handle_loop()` - Count/condition-based iteration
   - Direct execution for LLM/Function nodes

**State Management:**
- `save_state()` / `load_state()` - Redis-backed state persistence
- 1-hour TTL on all workflow state keys
- Enables pause/resume debugging

### Graph Construction (`graph.py`)

```python
class TreeNode:
    children = []          # Normal execution flow
    loop_info = []         # Loop body entry
    loop_next = []         # Loop exit points
    loop_last = []         # Post-loop execution
    condition = None       # Condition branch index
```

**Edge Types:**
- **Normal edges**: Sequential execution
- **Condition edges**: `condition-0`, `condition-1`, etc.
- **Loop edges**: `loop_body` (entry), `loop_next` (exit)

**Validation Rules:**
- No cross-hierarchy connections
- Loop nodes must have exactly one `loop_body` and one `loop_next`
- Condition nodes can have multiple conditional outputs

---

## 2. Sandbox Execution (`sandbox.py`)

**Docker-based isolation:**

```python
self.container = self.client.containers.run(
    image=self.image,
    detach=True,
    mem_limit="100m",           # Memory limit
    cpu_period=100000,
    cpu_quota=50000,            # 50% CPU limit
    volumes={"layra_sandbox_volume": {"bind": "/shared", "mode": "rw"}},
    security_opt=["no-new-privileges"],
    user="1000:1000",
)
```

**Key features:**
- Ephemeral containers per workflow session
- Session-isolated workspace (`/shared/{session_id}`)
- Optional image commit for environment persistence
- Resource limits: 100MB RAM, 50% CPU

**Code execution API:**
```python
async def execute(self, code, inputs, pip, image_url, remove, timeout):
    # Installs pip packages, runs code, returns output
```

---

## 3. Security: Code Scanner (`code_scanner.py`)

AST-based static analysis with regex patterns:

```python
FORBIDDEN_PATTERNS = [
    (r'os\.system\s*\(', "os.system() - shell command execution"),
    (r'subprocess\.(system|popen|call|run)\s*\(',
     "subprocess module - shell command execution"),
    (r'eval\s*\(', "eval() - arbitrary code execution"),
    (r'exec\s*\(', "exec() - arbitrary code execution"),
    (r'__import__\s*\(', "__import__() - dynamic module import"),
    (r'open\s*\(', "open() - file operations"),
    (r'socket\s*\.', "socket module - network operations"),
]
```

---

## 4. RAG Pipeline

### Document Conversion (`convert_file.py`)

```
Input: PDF/DOCX/XLSX/PPTX/Images
                ↓
        [Unoserver/LibreOffice]
                ↓
        High-DPI Images (100-200 DPI)
                ↓
    List[BytesIO] → Model Server
```

**Format support:**
- Direct: PDF, images (JPG, PNG, GIF, etc.)
- Converted via LibreOffice: DOCX, XLSX, PPTX, SVG

### Embedding Service (`get_embedding.py`)

```python
async def get_embeddings_from_httpx(data, endpoint, embedding_model):
    if embedding_model == "jina_embeddings_v4":
        return await _get_jina_embeddings(data, ...)
    else:
        return await _get_local_embeddings(data, ...)
```

**Dual model support:**
- **Local**: ColQwen2.5 via `model-server:8005`
- **Cloud**: Jina Embeddings v4 API

### Vector Storage (`milvus.py`)

```python
schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
schema.add_field(field_name="image_id", datatype=DataType.VARCHAR, max_length=65535)
schema.add_field(field_name="page_number", datatype=DataType.INT64)
schema.add_field(field_name="file_id", datatype=DataType.VARCHAR, max_length=65535)

# Index: HNSW with Inner Product (IP)
index_params = {"M": 16, "efConstruction": 500}
```

---

## 5. MCP Integration (`mcp_tools.py`)

```python
class MCPClient:
    async def connect_to_sse_server(self):
        streams = await self.exit_stack.enter_async_context(
            sse_client(url=self.server_url, ...)
        )
        session = await self.exit_stack.enter_async_context(ClientSession(*streams))
```

**Protocol:**
- SSE (Server-Sent Events) for tool discovery
- JSON-RPC for tool calls

---

## 6. Async Processing (Kafka)

```python
message = {
    "type": workflow_type,  # "workflow", "debug_resume", "input_resume"
    "task_id": task_id,
    "username": username,
    "workflow_data": workflow_data
}
await self.producer.send(
    KAFKA_TOPIC,
    json.dumps(message).encode("utf-8"),
    headers=[(KAFKA_PRIORITY_HEADER, priority.encode("utf-8"))]
)
```

---

## 7. Real-Time Streaming (SSE)

```python
async def workflow_sse(task_id, username):
    async def event_generator():
        while True:
            events = await redis.xread({f"workflow:events:{task_id}": '$'})
            yield parse_message(events)
```

**Event types:**
- `node`: Individual node execution result
- `workflow`: Workflow-level status
- Status values: `pause`, `running`, `vlm_input`, `vlm_input_debug`

---

## 8. Data Models

### MySQL (SQLAlchemy)
```python
class User(Base):
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    hashed_password = Column(String(100))
    password_migration_required = Column(Boolean)
```

### MongoDB (NoSQL)
- `chatflows`: Conversation history, turns
- `workflows`: Saved workflow configurations

### Redis
- `workflow:{task_id}:state` - Execution state (1hr TTL)
- `workflow:events:{task_id}` - Event stream (Redis Streams)
- Token caching, session management

---

## 9. Frontend Architecture

**Stack:** Next.js 15 + TypeScript + xyflow (React Flow)

```typescript
const FlowEditor: React.FC<FlowEditorProps> = ({ workFlow }) => {
  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} />
  );
}
```

**Node Types:**
- `StartNode`: Workflow entry point
- `LLMNode`: Model configuration
- `FunctionNode`: Python code execution
- `KnowledgeBaseNode`: RAG retrieval
- `ConditionNode`: Branching logic
- `LoopNode`: Iteration control
- `McpNode`: External tool integration

---

## Fixed Issues (2024-01-19)

### Security Fixes
1. ✅ Sandbox user: `restricted_user` → `1000:1000` (numeric UID)
2. ✅ Code scanner: Added regex patterns, forbidden imports detection
3. ✅ MCP tools: Fixed type hints, proper exception handling
4. ✅ Fixed missing `await` on `scalars().first()` in security.py

### Code Quality Fixes
1. ✅ Graph.py: Removed debug print statements, fixed bare except clauses
2. ✅ Config.py: Fixed `Field` import (pydantic vs pydantic_settings), removed hardcoded paths
3. ✅ Entrypoint.sh: Fixed Alembic migration issue (rm -rf migrations before init)
4. ✅ MCP tools: Fixed `dict = None` → `Optional[Dict] = None`
5. ✅ Fixed MinIO default port (9110 → 9000) in config.py
6. ✅ Fixed code scanner return format for `open()` detection

### Infrastructure Fixes
1. ✅ Added missing Milvus services to docker-compose.yml
2. ✅ Kafka consumer now enabled in main.py
3. ✅ Fixed docker-compose.yml Milvus service definitions
4. ✅ Cleaned up old Docker containers and volumes
5. ✅ Backend healthcheck added to docker-compose.yml

### Kafka Hardening (2024-01-20)
1. ✅ **Critical**: Fixed commit order (process THEN commit) - prevents data loss
2. ✅ Added retry with exponential backoff (3 retries, 1s→2s→4s)
3. ✅ Added Dead Letter Queue (DLQ) topic: `task_generation_dlq`
4. ✅ Added idempotency checking via Redis (24h TTL)
5. ✅ Added message validation with Pydantic schemas
6. ✅ Added concurrency control (max 5 concurrent tasks)
7. ✅ Added metrics tracking (processed, failed, dlq_sent, avg_time)
8. ✅ Added health check endpoint for Kafka consumer
9. ✅ Updated init-kafka.sh to create DLQ topic

### Naming Fixes
1. ✅ Fixed typo: `messgae_type` → `message_type`
2. ✅ Translated all Chinese comments to English
3. ✅ Fixed personal model path in model-server/config.py (`/home/liwei/ai/` → `/model_weights/`)

### New Development Tools
1. ✅ Added `Makefile` with common shortcuts
2. ✅ Created `.env.example` template with all environment variables documented

---

## Kafka Hardening Details

### Architecture Changes

```
Before (Vulnerable):
  for msg in consumer:
      await consumer.commit()     # ❌ Commit BEFORE processing
      await process_message(msg)  # If fails, message is LOST

After (Hardened):
  for msg in consumer:
      try:
          await process_message(msg)  # ✅ Process FIRST
          await consumer.commit()     # ✅ THEN commit
      except Exception as e:
          await send_to_dlq(msg, e)   # Send failed messages to DLQ
          # Don't commit - will be retried
```

### New Kafka Topics

| Topic | Partitions | Retention | Purpose |
|-------|------------|-----------|---------|
| `task_generation` | 10 | 7 days | Main task queue |
| `task_generation_dlq` | 3 | 30 days | Dead Letter Queue |

### New Features in KafkaConsumerManager

```python
class KafkaConsumerManager:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)  # Concurrency control
        self.metrics = {
            "processed": 0,
            "failed": 0,
            "dlq_sent": 0,
            "avg_process_time_ms": 0,
        }

    # 1. Retry with exponential backoff
    @retry(max_attempts=3, initial_delay=1, backoff=2)
    async def process_file_task(self, message: dict):
        # ...

    # 2. Dead Letter Queue
    async def send_to_dlq(self, msg: ConsumerRecord, error: Exception):
        # Sends failed messages with full error context

    # 3. Idempotency
    async def is_duplicate(self, task_id: str) -> bool:
        # Uses Redis: key="processed:{task_id}", TTL=24h

    # 4. Message Validation
    async def validate_message(self, message: dict) -> tuple[bool, BaseModel]:
        # Pydantic schema validation

    # 5. Metrics & Health
    def get_metrics(self) -> dict:
        return self.metrics

    def get_health_status(self) -> dict:
        return {"status": "healthy", "partitions_assigned": ...}
```

### Kafka Configuration Updates

**init-kafka/init-kafka.sh** now:
1. Creates main topic (`task_generation`) with configurable partitions
2. Creates DLQ topic (`task_generation_dlq`) with 3 partitions
3. Sets 30-day retention for DLQ (for debugging)
4. Validates both topics after creation

### Monitoring Commands

```bash
# Check Kafka topics
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe DLQ topic
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --describe --topic task_generation_dlq --bootstrap-server localhost:9092

# View DLQ messages (optional)
docker exec layra-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic task_generation_dlq --from-beginning --bootstrap-server localhost:9092

# Check backend logs for Kafka activity
docker logs layra-backend -f | grep -E "kafka|consumer|dlq"
```

### Error Handling Flow

```
Message Received
       ↓
Validate message schema (Pydantic)
       ↓
Check idempotency (Redis)
       ↓
Process message (with retry)
       ↓
    ┌───✅ Success → Mark processed → Commit → Next message
    │
    └───❌ Failure → Send to DLQ → Don't commit → Retry later
```

---

## Security Analysis

| Aspect | Implementation |
|--------|----------------|
| **Auth** | JWT tokens, Redis-backed sessions |
| **Code Execution** | AST scanning, Docker sandbox, resource limits |
| **User Isolation** | Username-prefixed resources |
| **Secrets** | Environment variables via `.env` |

**Improvements needed:**
- Create `restricted_user` in Dockerfile
- Add network isolation for sandbox containers
- Implement Redis key namespacing by user
- Add rate limiting on API endpoints

---

## Performance Considerations

| Component | Configuration |
|-----------|---------------|
| **Vector Search** | HNSW index, M=16, efConstruction=500 |
| **Milvus** | Dynamic fields enabled, IP metric |
| **Kafka** | 10 partitions, 2GB max message size |
| **Docker** | 100MB memory, 50% CPU per sandbox |

---

## Critical Code Paths

**Workflow Execution:**
```
POST /api/v1/workflow/execute
  → WorkflowEngine context (sandbox init)
  → KafkaProducerManager.send_workflow_task()
  → GET /api/v1/sse/workflow/{username}/{task_id}
    → Redis XREAD on workflow:events:{task_id}
```

**Document Ingestion:**
```
POST /api/v1/knowledge-base/upload
  → convert_file_to_images()
  → get_embeddings_from_httpx()
  → MilvusManager.create_collection()
```

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `workflow_engine.py` | Core execution engine with pause/resume |
| `graph.py` | DAG validation, tree node management |
| `sandbox.py` | Docker-based code execution |
| `code_scanner.py` | AST security scanning |
| `mcp_tools.py` | Model Context Protocol client |
| `get_embedding.py` | Visual embedding abstraction |
| `convert_file.py` | Multi-format document conversion |
| `milvus.py` | Vector storage with HNSW index |
| `kafka_producer.py` | Async task queuing |
| `sse.py` | Real-time event streaming |
| `chatflow.py` | Conversation history management |

---

## Tech Stack Summary

```
Frontend:  Next.js 15, TypeScript, TailwindCSS 4.0, Zustand, xyflow
Backend:   FastAPI, Kafka, Redis, MySQL, MongoDB, MinIO, Milvus
ML/NLP:    ColQwen2.5, Jina-Embeddings-v4, Qwen2.5-VL (LLM)
Infra:     Docker, Docker Compose, Nginx
```

---

## Strengths

1. **Novel visual-native approach** - No layout loss in document RAG
2. **Enterprise-grade architecture** - Decoupled services, async processing
3. **Full Python control** - Arbitrary code execution in workflows
4. **Comprehensive tooling** - MCP, breakpoints, human-in-the-loop
5. **Dual embedding options** - Local GPU or cloud Jina API

## Considerations

1. **GPU required** for local embedding (ColQwen2.5 needs ~16GB VRAM)
2. **Complex deployment** - 13+ Docker services
3. **Heavy resource usage** - Multiple databases + model server
4. **Security hardening needed** for production use

---

## Environment Variables

> **Note:** See `.env.example` for the complete template. Copy it to `.env` and customize.

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_URL` | - | MySQL connection string |
| `REDIS_URL` | redis:6379 | Redis connection |
| `REDIS_PASSWORD` | - | Redis password |
| `MONGODB_URL` | mongodb://...:27017 | MongoDB connection |
| `MINIO_URL` | http://minio:9000 | MinIO endpoint |
| `MINIO_ACCESS_KEY` | - | MinIO access key |
| `MINIO_SECRET_KEY` | - | MinIO secret key |
| `MILVUS_URI` | http://milvus-standalone:19530 | Milvus endpoint |
| `KAFKA_BROKER_URL` | kafka:9094 | Kafka broker |
| `SECRET_KEY` | - | JWT secret key (change in production!) |
| `ALGORITHM` | HS256 | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 11520 | Token expiry (8 days) |
| `COLBERT_MODEL_PATH` | /model_weights/colqwen2.5-v0.2 | Local model path |
| `EMBEDDING_MODEL` | local_colqwen | Embedding model (local_colqwen/jina_embeddings_v4) |
| `JINA_API_KEY` | - | Jina AI API key for cloud embeddings |
| `DEBUG_MODE` | false | Enable debug mode |
| `LOG_LEVEL` | INFO | Logging level |

### Quick Setup

1. Copy the template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values (only `SECRET_KEY` and database passwords need changing for local dev)

3. Start LAYRA:
   ```bash
   make up
   ```

---

## Troubleshooting

### Using Makefile (Recommended)

```bash
# Start all services
make up

# View logs (follow mode)
make logs

# View backend logs only
make logs-backend

# Restart all services
make restart

# Check service health
make health

# Check status
make status

# Full reset (WARNING: deletes all data!)
make reset

# SSH into containers
make ssh-backend    # Backend container
make ssh-model      # Model server container
```

### Using compose-clean (Original)

```bash
# Check all services
./compose-clean ps

# View backend logs
./compose-clean logs -f backend

# Reset everything
./compose-clean down -v
./compose-clean up -d

# Check API health
curl http://localhost:8000/api/v1/health/check

# Rebuild backend only
./compose-clean build backend --no-cache
```

### MinIO Console
```
URL: http://localhost:9001
Access Key: minio_acc_3m4n5o
Secret Key: minio_sec_6p7q8r
```

### Kafka Troubleshooting

```bash
# Check if Kafka is running
docker exec layra-kafka /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# List all topics
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Check topic descriptions
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --describe --topic task_generation --bootstrap-server localhost:9092
docker exec layra-kafka /opt/kafka/bin/kafka-topics.sh --describe --topic task_generation_dlq --bootstrap-server localhost:9092

# Check consumer lag (if messages aren't processing)
docker exec layra-kafka /opt/kafka/bin/kafka-consumer-groups.sh --describe --group task_consumer_group --bootstrap-server localhost:9092

# View DLQ messages
docker exec layra-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic task_generation_dlq --from-beginning --bootstrap-server localhost:9092 --timeout-ms 5000

# Check Kafka logs
docker logs layra-kafka -f

# Check backend Kafka consumer logs
docker logs layra-backend | grep -E "kafka|consumer|dlq"
```

### Common Issues

**Messages not processing:**
```bash
# Check consumer group status
docker exec layra-kafka /opt/kafka/bin/kafka-consumer-groups.sh --describe --group task_consumer_group --bootstrap-server localhost:9092

# If lag is high, check backend logs
docker logs layra-backend | tail -50
```

**DLQ filling up:**
```bash
# Check DLQ message count
docker exec layra-kafka /opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic task_generation_dlq --time -1

# View recent DLQ messages to identify pattern
docker exec layra-kafka /opt/kafka/bin/kafka-console-consumer.sh --topic task_generation_dlq --max-messages 10 --bootstrap-server localhost:9092
```

---

## Simple Auth Mode (Solo/Dev)

For solo projects or development environments, LAYRA provides a lightweight authentication alternative that doesn't require full database setup.

### Overview

| Feature | Full Auth | Simple Auth |
|---------|-----------|-------------|
| **Database** | MySQL (users table) | None |
| **Token Storage** | Redis | JWT only |
| **Registration** | Required | Not needed |
| **Users** | Multiple | Single |
| **Setup Complexity** | Medium | Low |

### Enabling Simple Auth

```bash
# Edit .env and set:
SIMPLE_AUTH_MODE=true
SIMPLE_API_KEY=layra-dev-key-2024
SIMPLE_USERNAME=layra
SIMPLE_PASSWORD=layra123
```

Restart the backend:
```bash
docker compose restart backend
```

### API Endpoints

#### API Key Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/apikey \
  -H "X-API-Key: layra-dev-key-2024"
```

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user": {
        "username": "layra",
        "email": "layra@simple.local"
    }
}
```

#### Password Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=layra&password=layra123"
```

#### Verify Token
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/auth/verify-token
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMPLE_AUTH_MODE` | false | Enable simple auth (true/false) |
| `SIMPLE_API_KEY` | layra-dev-key-2024 | API key for apikey login |
| `SIMPLE_USERNAME` | layra | Username for password login |
| `SIMPLE_PASSWORD` | layra123 | Password for password login |

### How It Works

1. **API Key Authentication**: The `X-API-Key` header is validated against `SIMPLE_API_KEY`
2. **Password Authentication**: Username/password validated against configured credentials
3. **Token Generation**: A simple JWT token is issued with 8-hour expiry
4. **Token Validation**: Tokens are validated using the main `SECRET_KEY`

### Switching Between Modes

| Current Mode → | New Mode | Action |
|----------------|----------|--------|
| Full Auth → Simple Auth | Set `SIMPLE_AUTH_MODE=true`, restart backend |
| Simple Auth → Full Auth | Set `SIMPLE_AUTH_MODE=false`, restart backend |

### Production Recommendation

Use **Full Auth** in production with:
- Multiple users
- User registration
- Token revocation
- Session management

Use **Simple Auth** for:
- Solo development
- Demo environments
- Quick testing
- Single-user deployments

---

## Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    LAYRA Platform                        │
                    └─────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│   Frontend    │            │    Nginx      │            │  Model Server │
│  (Next.js 15) │◄──────────►│  (Reverse     │───────────►│  (ColQwen2.5) │
│   :3000       │            │   Proxy :8090)│            │   :8005       │
└───────────────┘            └───────┬───────┘            └───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │           Backend (FastAPI)              │
                    │            layra-backend :8000           │
                    └────────────────────┬────────────────────┘
                                         │
         ┌────────────┬───────────┬──────┴──────┬───────────┬────────────┐
         ▼            ▼           ▼             ▼           ▼            ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐  ┌─────────┐ ┌─────────┐  ┌─────────┐
    │  MySQL  │ │ MongoDB │ │  Redis  │  │  Kafka  │ │  MinIO  │  │ Milvus  │
    │  :3306  │ │ :27017  │ │  :6379  │  │  :9092  │ │  :9000  │  │ :19530  │
    └─────────┘ └─────────┘ └─────────┘  └─────────┘ └─────────┘  └─────────┘
         │            │           │             │           │            │
         │            │           │             │           │            │
         └────────────┴───────────┴─────────────┴───────────┴────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │            Supporting Services           │
                    └────────────────────┬────────────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
    ┌───────────┐               ┌───────────────┐               ┌─────────────┐
    │ Unsserver │               │ Docker Sandbox│               │  MCP Tools  │
    │  (Docs)   │               │ (Code Exec)   │               │  (Ext API)  │
    │  :2003    │               │ (Container)   │               │             │
    └───────────┘               └───────────────┘               └─────────────┘
```

---

**Last Updated:** 2026-01-19
**Version:** 2.1

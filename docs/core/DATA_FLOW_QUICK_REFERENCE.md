# RAG System Data Flow - Quick Reference

## Executive Summary

The Layra RAG system uses an **event-driven architecture** with Kafka for async processing, Redis for state management, and a multi-storage backend (MinIO/Milvus/MongoDB). Data flows through **three primary paths**: upload, query, and workflow execution.

---

## 1. Critical Bottlenecks (Top 5)

| # | Bottleneck | Location | Impact | Fix Priority |
|---|------------|----------|--------|--------------|
| 1 | **Synchronous PDF Conversion** | `convert_file.py:133-143` | Blocks event loop up to 10min per file | 🔴 CRITICAL |
| 2 | **Sequential Embedding Batches** | `utils.py:110-151` | No pipelining, network latency accumulates | 🔴 CRITICAL |
| 3 | **CPU-Bound MaxSim Reranking** | `milvus.py:236-243` | Python event loop blocked on matrix ops | 🔴 CRITICAL |
| 4 | **Synchronous Docker Exec** | `sandbox.py:223-239` | Each code node blocks on container | 🟡 HIGH |
| 5 | **Sequential Node Execution** | `workflow_engine.py:577-583` | No parallelism in workflows | 🟡 HIGH |

**Quick Wins**:
- Move MaxSim to GPU (embedding service)
- Cache converted images in Redis
- Implement container pooling for sandboxes

---

## 2. Data Consistency Issues

### Problem: No Distributed Transactions

```
MinIO Upload → Kafka → Consumer → Milvus + MongoDB
    ✓           ✓         ✗           ✗
```

**Failure Scenario**: If Milvus insert succeeds but MongoDB fails → orphaned vectors

**Current Mitigation**: Best-effort cleanup in exception handler (not guaranteed)

**Recommended Fix**: Implement Saga pattern with compensating transactions

### Other Consistency Issues

1. **Redis State Expiration**: Workflow state expires after 1 hour → lost work
2. **Eventual Search Consistency**: Uploaded files not immediately searchable
3. **Partial Checkpoint Rollback**: Sandbox state lost on rollback

---

## 3. Error Propagation Patterns

### Recovery Strategy Matrix

| Error Type | Detection | Recovery | Cleanup |
|------------|-----------|----------|---------|
| **Embedding OOM** | Error message contains "oom" | Retry 3x with backoff | No cleanup (recoverable) |
| **File Process Failure** | Exception in `process_file()` | Send to DLQ after 3 retries | Delete Milvus vectors, Mongo metadata |
| **LLM Timeout** | Circuit breaker open | Fail fast for 60s | Log error event |
| **Docker Sandbox Failure** | ContainerError | Rollback checkpoint | Remove container |
| **Kafka Consumer Crash** | Exception in consumer loop | Restart from last commit | Manual offset reset if needed |

### Dead Letter Queue

- Topic: `task_generation_dlq`
- Triggers: Validation failure, max retries exceeded
- Contains: Original payload + error details + traceback
- Action Required: Manual inspection and reprocessing

---

## 4. State Management

### Workflow State Lifecycle

```
pending → running → (pause | vlm_input | completed | failed | canceled)
```

### Redis Keys (TTL=3600s)

- `workflow:{task_id}` - Status, result, end_time
- `workflow:{task_id}:nodes` - Node execution status
- `workflow:{task_id}:state` - Full state snapshot (for rollback)
- `workflow:{task_id}:operator` - Cancellation status
- `workflow:events:{task_id}` - Event stream (SSE to frontend)

### Checkpoint Triggers

- `before_node` - Before execution (for rollback)
- `after_node` - After successful execution
- `loop_complete` - After each loop iteration
- `gate` - After conditional routing

### Rollback Limitations

**What's Restored**: global_variables, execution_status, context, execution_stack

**What's Lost**: Docker container state, external API calls, MCP tool results, LLM token usage

---

## 5. Upload Flow Summary

```
User → FastAPI → MinIO (parallel upload) → Kafka → Consumer → [Conversion → Embedding → Milvus + MinIO + MongoDB]
       │                                                              │
       └─ Returns: task_id, knowledge_db_id, files                    └─ Updates: Redis progress
```

**Data Transformations**:
- `UploadFile` → `bytes` → `List[BytesIO]` (PNG images) → `List[List[float]]` (vectors)

**Bottlenecks**:
- User waits for ALL files to upload before response
- PDF conversion blocks event loop (up to 10min)
- Embedding batches processed sequentially

**Consistency**: Eventual (no atomic transaction across services)

---

## 6. Query Flow Summary

```
User → FastAPI → (Image Replacement) → Embedding → Milvus Search → Context Building → LLM → SSE Stream
       │               │                        │                  │
       │               └─ MinIO download        └─ MaxSim rerank   └─ Provider client
       │               (synchronous)           (CPU-bound)
       │
       └─ Returns: Streaming response chunks
```

**Data Transformations**:
- MinIO URLs → base64 data URIs → Query vectors → Top-k results → LLM context

**Bottlenecks**:
- Image replacement blocks query processing
- MaxSim reranking in Python (no GPU)
- Sequential vector fetch from Milvus (pagination)

**Consistency**: Read-committed (Milvus eventually consistent with uploads)

---

## 7. Workflow Flow Summary

```
Frontend → FastAPI → Kafka → Consumer → WorkflowEngine → (Code Node | VLM Node | Condition | Loop) → Redis Events
                                      │
                                      ├─ Code: Security scan → Docker exec → Parse output
                                      ├─ VLM: MCP tools → LLM call → Stream response
                                      ├─ Condition: Safe eval → Route children
                                      └─ Loop: Check condition → Execute body → Update index
```

**Bottlenecks**:
- Sequential node execution (no parallelism)
- Synchronous Docker operations per node
- In-memory context accumulation (cleanup during execution)

**Consistency**: Eventual with rollback (checkpoint-based, limited to Redis state)

---

## 8. Key Configuration

### Batch Sizes & Limits

```python
EMBED_BATCH_SIZE = 16          # Embeddings per batch
MAX_CONCURRENT = 10           # Max Kafka consumer tasks
MAX_CONTEXT_ENTRIES = 1000    # Max workflow context entries
MAX_CONTEXT_SIZE = 50         # Max entries per node
LOOP_LIMITS = {"condition": 1000}  # Max loop iterations
```

### Timeouts (seconds)

```python
pdf_conversion_timeout = 600      # 10 minutes
embedding_service_timeout = 1200  # 20 minutes
docker_exec_timeout = 3600        # 1 hour
circuit_breaker_timeout = 60      # 1 minute
```

### TTL (seconds)

```python
IDEMPOTENCY_TTL = 86400      # 24 hours (Redis)
WORKFLOW_STATE_TTL = 3600    # 1 hour (Redis)
```

---

## 9. File Path Reference

### Upload Flow

```
/backend/app/api/endpoints/chat.py
  └─ upload_multiple_files()      # Entry point

/backend/app/rag/convert_file.py
  ├─ save_file_to_minio()         # MinIO upload
  └─ convert_file_to_images()     # PDF/Office → PNG

/backend/app/rag/utils.py
  ├─ process_file()               # Consumer handler
  ├─ generate_embeddings()        # Embedding service call
  └─ insert_to_milvus()           # Vector insertion

/backend/app/utils/kafka_consumer.py
  └─ KafkaConsumerManager          # Message consumption
```

### Query Flow

```
/backend/app/rag/utils.py
  └─ replace_image_content()       # MinIO → base64

/backend/app/rag/get_embedding.py
  └─ get_embeddings_from_httpx()   # Query embedding

/backend/app/db/milvus.py
  └─ MilvusManager.search()        # MaxSim search
```

### Workflow Flow

```
/backend/app/workflow/workflow_engine.py
  ├─ WorkflowEngine                # Main orchestrator
  ├─ execute_workflow()            # Node execution loop
  └─ execute_node()                # Node-specific logic

/backend/app/workflow/sandbox.py
  └─ CodeSandbox                   # Docker execution

/backend/app/workflow/components/checkpoint_manager.py
  └─ WorkflowCheckpointManager     # State snapshots
```

---

## 10. Circuit Breaker

### States

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Fail fast, raise exception immediately (5 failures trigger)
- **HALF_OPEN**: Allow one request to test recovery (after 60s timeout)

### Protected Services

- Embedding service (`@embedding_service_circuit`)
- LLM service (`@llm_service_circuit`)

### Configuration

```python
failure_threshold = 5      # Failures before opening
recovery_timeout = 60      # Seconds before half-open
expected_exception = Exception  # Catch-all (broad)
```

### Monitoring

- Export state to Prometheus
- Alert on circuit open
- Track failure rate per service

---

## 11. Optimization Roadmap

### Phase 1: Quick Wins (1-2 weeks)

- [ ] Cache converted images in Redis (TTL=1hr)
- [ ] Move MaxSim reranking to GPU
- [ ] Add Docker container pooling
- [ ] Implement streaming upload progress

### Phase 2: Parallelization (2-4 weeks)

- [ ] Multiprocessing for PDF conversion
- [ ] Pipeline embedding batches with Milvus inserts
- [ ] Parallel node execution in workflows
- [ ] Concurrent Docker exec with thread pool

### Phase 3: Consistency (4-6 weeks)

- [ ] Implement Saga pattern for file upload
- [ ] Add orphan detection scheduled job
- [ ] Archive workflow state to MongoDB
- [ ] Add processing status to search results

### Phase 4: Monitoring (1-2 weeks)

- [ ] Circuit breaker metrics dashboard
- [ ] DLQ monitoring and alerting
- [ ] Bottleneck latency tracking
- [ ] Data consistency health checks

---

## 12. Troubleshooting

### File Stuck in "Processing"

**Symptoms**: Redis task status shows "processing" indefinitely

**Diagnosis**:
1. Check Kafka consumer logs for errors
2. Verify embedding service is healthy
3. Check Milvus connection
4. Look for orphaned task in DLQ

**Resolution**:
- If consumer crashed: Restart consumer, it will retry
- If embedding OOM: Increase GPU memory or reduce batch size
- If DLQ: Manually reprocess message

### Search Returns No Results

**Symptoms**: Uploaded file not found in search

**Diagnosis**:
1. Check Redis task status (is it completed?)
2. Verify Milvus collection exists
3. Check MongoDB file metadata
4. Validate MinIO file exists

**Resolution**:
- If not completed: Wait for processing
- If Milvus empty: Re-ingest file
- If orphaned: Run orphan detection job

### Workflow Fails to Resume

**Symptoms**: "Workflow expired!" error

**Diagnosis**:
1. Check `workflow:{task_id}:state` in Redis
2. Verify TTL hasn't expired (3600s)
3. Check if checkpoint exists

**Resolution**:
- If expired: State lost, must restart workflow
- Future: Implement MongoDB archival

---

## 13. Metrics to Monitor

### Throughput

- Files processed per hour
- Queries per second
- Workflows completed per day
- Kafka messages consumed per minute

### Latency

- End-to-end upload time (user → completed)
- Query response time (request → first chunk)
- Workflow node execution time
- Embedding generation time

### Errors

- Circuit breaker open count
- DLQ message count
- Orphaned file count
- Workflow failure rate

### Resource Usage

- GPU utilization (embedding service)
- Docker container count
- Redis memory usage
- Milvus collection size

---

## 14. Architecture Strengths & Weaknesses

### Strengths ✓

1. **Event-Driven Design**: Kafka enables async processing
2. **Idempotency**: Redis keys prevent duplicate processing
3. **Fault Tolerance**: Circuit breakers, retries, DLQ
4. **Streaming**: Real-time feedback via Redis streams
5. **Sandboxing**: Docker isolation for code execution

### Weaknesses ✗

1. **No Distributed Transactions**: Cross-system consistency is best-effort
2. **Sequential Bottlenecks**: Many operations are synchronous
3. **Limited Parallelism**: Commented-out parallel code suggests failed attempts
4. **Memory Pressure**: In-memory context accumulation
5. **TTL-Based Cleanup**: No graceful shutdown for expiring data

---

## Appendix: Quick Command Reference

### Check Kafka Consumer Status

```bash
# Consumer metrics
curl http://localhost:8000/health/kafka

# DLQ message count
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic task_generation_dlq --from-beginning --timeout-ms 1000 | wc -l
```

### Check Redis State

```bash
# Active workflow tasks
redis-cli KEYS "workflow:*:operator"

# Task status
redis-cli HGETALL "task:{task_id}"

# Workflow state
redis-cli GET "workflow:{task_id}:state"
```

### Check Milvus Collections

```python
from app.db.vector_db import vector_db_client

# List collections
collections = vector_db_client.client.list_collections()

# Collection stats
stats = vector_db_client.client.get_collection_stats("colqwen_kb_123")
```

### Check Orphaned Data

```python
# Find Milvus vectors without MongoDB metadata
# (Run this as a scheduled job)
from app.db.mongo import get_mongo
from app.db.vector_db import vector_db_client

async def find_orphans():
    db = await get_mongo()
    files = await db.db.files.find({}, {"file_id": 1}).to_list(None)
    file_ids = [f["file_id"] for f in files]

    # Query Milvus for file_ids not in MongoDB
    # (Implementation depends on Milvus query capabilities)
    pass
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-28
**Companion Documents**:
- `DATA_FLOW_ANALYSIS.md` - Detailed textual analysis
- `DATA_FLOW_DIAGRAMS.md` - Visual ASCII diagrams

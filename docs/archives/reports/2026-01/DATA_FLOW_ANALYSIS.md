# RAG System Data Flow Analysis

## Executive Summary

This document traces the complete data flow through the Layra RAG system, identifying bottlenecks, error propagation patterns, and data consistency boundaries. The system uses an event-driven architecture with Kafka for asynchronous processing, Redis for state management, and MongoDB/Milvus/MinIO for persistent storage.

---

## 1. Upload Flow: File → MinIO → Kafka → Embedding → Milvus

### 1.1 Data Flow Diagram

```
┌─────────────┐
│ Frontend    │
│ (User Upload)│
└──────┬──────┘
       │ POST /upload/{username}/{conversation_id}
       │ files: List[UploadFile]
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/api/endpoints/chat.py                           │
│ upload_multiple_files()                                     │
│                                                              │
│ 1. Create temp knowledge_base_id                            │
│ 2. Initialize Redis task status                             │
│ 3. Generate task_id                                          │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Parallel MinIO Upload (asyncio.gather)
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/rag/convert_file.py                             │
│ save_file_to_minio()                                        │
│                                                              │
│ Data: UploadFile → MinIO object                             │
│ Returns: (minio_filename, minio_url)                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Kafka Message (per file)
       │ {task_id, username, knowledge_db_id, file_meta}
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Kafka Topic: "task_generation"                              │
│                                                              │
│ Idempotency Key: file:{file_id}                             │
│ TTL: 24 hours                                               │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Consumer Group: backend-consumer
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/utils/kafka_consumer.py                         │
│ KafkaConsumerManager.consume_messages()                     │
│                                                              │
│ Concurrency: MAX_CONCURRENT=10                              │
│ Manual commit AFTER processing                              │
│ Retry: MAX_RETRIES=3 with exponential backoff              │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ process_file_task()
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/rag/utils.py                                    │
│ process_file()                                              │
│                                                              │
│ 1. Validate MinIO file existence                            │
│ 2. Download file content                                    │
│ 3. Convert to images (PDF/Office/Image)                     │
│ 4. Batch generate embeddings (EMBED_BATCH_SIZE=16)         │
│ 5. Insert vectors to Milvus                                 │
│ 6. Save images to MinIO                                     │
│ 7. Update MongoDB metadata                                  │
│ 8. Update Redis progress                                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Data Transformations

| Stage | Input Format | Output Format | Transformation |
|-------|-------------|---------------|----------------|
| **Upload** | UploadFile (multipart/form-data) | bytes | Raw file extraction |
| **MinIO Storage** | bytes | minio_filename, minio_url | Object storage with presigned URL |
| **File Conversion** | bytes (PDF/DOCX/etc) | List[BytesIO] (PNG images) | DPI adaptation (150-200), A4 resizing |
| **Embedding** | List[BytesIO] | List[List[float]] (multi-vector) | ColQwen2.5 → 128-dim vectors per image |
| **Milvus Insert** | {colqwen_vecs, page_number, image_id, file_id} | Vector embeddings | HNSW indexing with IP metric |
| **MongoDB Metadata** | file_meta, image_metadata | BSON documents | File & image collections |

### 1.3 Bottlenecks

#### Critical Bottleneck #1: Synchronous PDF Conversion
**Location**: `/backend/app/rag/convert_file.py:133-143`
```python
images = await asyncio.wait_for(
    asyncio.to_thread(
        convert_from_bytes,
        file_content,
        dpi=effective_dpi,
        timeout=pdf_conversion_timeout,
        thread_count=1
    ),
    timeout=pdf_conversion_timeout  # 600 seconds
)
```

**Impact**:
- Blocks event loop for up to 10 minutes per file
- No parallelization across files (only within batches)
- Memory-intensive for large PDFs (>50 pages)

**Mitigation**: Adaptive DPI (150-200), but still synchronous per file

#### Critical Bottleneck #2: Sequential Embedding Generation
**Location**: `/backend/app/rag/utils.py:110-151`
```python
for batch_start in range(0, len(images_buffer), EMBED_BATCH_SIZE):
    batch_embeddings = await generate_embeddings(batch_buffers, ...)
    await insert_to_milvus(collection_name, batch_embeddings, ...)
    # Sequential batch processing
```

**Impact**:
- Embedding service calls are sequential (batch-by-batch)
- Model server may have GPU capacity for parallel batches
- Network latency accumulates per batch

#### Critical Bottleneck #3: MinIO Upload Before Kafka
**Location**: `/backend/app/api/endpoints/chat.py:266-267`
```python
upload_tasks = [save_file_to_minio(username, file) for file in files]
upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
```

**Impact**:
- User waits for ALL files to upload before response
- No streaming progress feedback during upload
- Large files block the entire request

---

## 2. Query Flow: User Query → Embedding → Milvus Search → Context Building → LLM

### 2.1 Data Flow Diagram

```
┌─────────────┐
│ Frontend    │
│ (User Query)│
└──────┬──────┘
       │ POST /chat (WebSocket/SSE)
       │ {query, conversation_id, temp_db_id}
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/api/endpoints/chat.py (hypothetical endpoint)   │
│                                                              │
│ 1. Authenticate user                                        │
│ 2. Load conversation history                                │
│ 3. Identify temp_kb_id                                      │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ If query contains images:
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/rag/utils.py                                    │
│ replace_image_content()                                     │
│                                                              │
│ For each image_url in messages:                             │
│   - Download from MinIO                                     │
│   - Convert to base64                                       │
│   - Replace URL with data:image/png;base64,{...}           │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Query embedding generation
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/rag/get_embedding.py                            │
│ get_embeddings_from_httpx(endpoint="embed_image")          │
│                                                              │
│ @embedding_service_circuit                                  │
│ POST {model_server_url}/embed_image                         │
│ Returns: List[List[float]] (multi-vector)                  │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Vector search
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/db/milvus.py                                    │
│ MilvusManager.search()                                      │
│                                                              │
│ 1. Candidate generation (topk * 10, max 200)               │
│ 2. Approximate MaxSim scoring                               │
│ 3. Fetch candidate vectors (paginated, 8192/page)          │
│ 4. Exact MaxSim reranking                                   │
│ 5. Return top-k results                                     │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Context building
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Context Assembly                                            │
│                                                              │
│ 1. Retrieve image metadata from MongoDB                    │
│ 2. Build context with:                                      │
│    - User query text/images                                 │
│    - Retrieved document images                              │
│    - Conversation history (parent messages)                 │
│    - System prompt                                          │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ LLM invocation
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/rag/provider_client.py                          │
│ ProviderClient.create_client()                              │
│                                                              │
│ Provider auto-detection:                                    │
│   - openai, deepseek, anthropic, gemini                    │
│   - moonshot, zhipu, minimax, cohere, ollama               │
│                                                              │
│ Returns: AsyncOpenAI client                                 │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Streaming response
       ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM Streaming Response                                      │
│                                                              │
│ Chunks sent via:                                            │
│   - Server-Sent Events (SSE)                                │
│   - Redis Streams (for workflows)                           │
│                                                              │
│ Chunk types:                                                │
│   - text: Delta content                                     │
│   - image_url: Retrieved document images                   │
│   - user_images: User uploaded images                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Transformations

| Stage | Input Format | Output Format | Transformation |
|-------|-------------|---------------|----------------|
| **Query** | User text + optional images | UserMessage object | Structured message format |
| **Image Replacement** | MinIO URLs | base64 data URIs | Inline image data for LLM |
| **Query Embedding** | Text/images | Multi-vector (ColQwen) | Same model as documents |
| **Milvus Search** | Query vectors | Top-k image results | MaxSim similarity scoring |
| **Context Building** | Search results + history | List[Message] | Prompt construction |
| **LLM Response** | Context | Streaming text chunks | Token-by-token streaming |

### 2.3 Bottlenecks

#### Critical Bottleneck #4: Synchronous Image Replacement
**Location**: `/backend/app/rag/utils.py:260-290`
```python
async def replace_image_content(messages):
    for message in messages:
        for item in message["content"]:
            if item.get("type") == "image_url":
                image_base64 = await async_minio_manager.download_image_and_convert_to_base64(...)
```

**Impact**:
- Blocks query processing until ALL images downloaded
- No caching of converted images
- Re-downloads same images across conversations

#### Critical Bottleneck #5: Sequential Vector Fetch
**Location**: `/backend/app/db/milvus.py:191-210`
```python
for chunk_ids in _chunks(candidate_image_ids, 50):
    batch = self.client.query(
        collection_name=collection_name,
        filter=filter_expr,
        output_fields=[...],
        limit=8192,
        offset=offset,
    )
```

**Impact**:
- Paginated queries for large candidate sets
- Multiple round-trips to Milvus
- No parallel chunk fetching

#### Critical Bottleneck #6: MaxSim Reranking in Python
**Location**: `/backend/app/db/milvus.py:236-243`
```python
for img_id, doc_data in docs_map.items():
    doc_vecs = np.asarray(doc_data["vectors"], dtype=np.float32)
    score = np.dot(query_vecs, doc_vecs.T).max(axis=1).sum()
```

**Impact**:
- CPU-bound computation in Python event loop
- No GPU acceleration for matrix operations
- Scales poorly with candidate count

---

## 3. Workflow Flow: Trigger → Node Execution → State Management → Output

### 3.1 Data Flow Diagram

```
┌─────────────┐
│ Frontend    │
│ (Workflow   │
│  Trigger)   │
└──────┬──────┘
       │ POST /workflows/execute
       │ {nodes, edges, global_variables, ...}
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Kafka Message: workflow task                                │
│                                                              │
│ {                                                           │
│   type: "workflow",                                         │
│   task_id: "{workflow_id}",                                 │
│   username: "...",                                          │
│   workflow_data: {nodes, edges, start_node, ...}          │
│ }                                                           │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Kafka Consumer
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/utils/kafka_consumer.py                         │
│ process_workflow_task()                                     │
│                                                              │
│ 1. Check cancellation status                               │
│ 2. Initialize WorkflowEngine context                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ async with WorkflowEngine(...) as engine:
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/workflow/workflow_engine.py                     │
│ WorkflowEngine.__aenter__()                                 │
│                                                              │
│ 1. Initialize CodeSandbox (Docker container)               │
│ 2. Build workflow graph (validation)                       │
│ 3. Initialize checkpoint manager                           │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ engine.start()
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Node Execution Loop                                        │
│                                                              │
│ for node in execution_stack:                                │
│   - Check breakpoints (pause for debug)                    │
│   - Check cancellation                                     │
│   - Execute node (code/vlm/condition/loop)                 │
│   - Update Redis status                                    │
│   - Checkpoint after key nodes                             │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Node Types:
       ├─────────────────────────────────────────────────────┤
       │                                                       │
       │ CODE NODE:                                           │
       │  - Scan code for security                            │
       │  - Execute in Docker sandbox                         │
       │  - Parse output for global variables                │
       │  - Update context                                    │
       │                                                       │
       │ VLM NODE:                                            │
       │  - MCP tool selection (optional)                     │
       │  - LLM call with retry + circuit breaker            │
       │  - Stream response to Redis                          │
       │  - Extract JSON for variables                       │
       │                                                       │
       │ CONDITION NODE:                                      │
       │  - Safe eval of conditions                           │
       │  - Route to matching children                        │
       │  - Auto-checkpoint                                   │
       │                                                       │
       │ LOOP NODE:                                           │
       │  - Track loop index                                  │
       │  - Execute loop body                                 │
       │  - Check exit condition                             │
       │  - Checkpoint after iteration                       │
       │                                                       │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ State Management
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Redis State Storage                                        │
│                                                              │
│ Keys:                                                       │
│   - workflow:{task_id} (status, result, end_time)          │
│   - workflow:{task_id}:nodes (node execution status)       │
│   - workflow:{task_id}:state (full state snapshot)         │
│   - workflow:{task_id}:operator (cancellation status)      │
│   - workflow:events:{task_id} (event stream)               │
│                                                              │
│ TTL: 3600 seconds (1 hour)                                 │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Checkpoint & Recovery
       ▼
┌─────────────────────────────────────────────────────────────┐
│ backend/app/workflow/components/checkpoint_manager.py     │
│ WorkflowCheckpointManager                                   │
│                                                              │
│ Triggers:                                                   │
│   - before_node (for rollback)                             │
│   - after_node (for recovery)                              │
│   - loop_complete (iteration boundary)                     │
│   - gate (conditional routing)                             │
│                                                              │
│ Storage: Redis workflow:{task_id}:state                    │
│                                                              │
│ Recovery:                                                   │
│   - Load state on debug_resume/input_resume                │
│   - Rebuild execution stack                                │
│   - Continue from checkpoint                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Transformations

| Stage | Input Format | Output Format | Transformation |
|-------|-------------|---------------|----------------|
| **Workflow Trigger** | JSON (nodes, edges) | WorkflowGraph object | Validation + tree building |
| **Code Execution** | Python code string | stdout/stderr | Docker sandbox execution |
| **VLM Input** | Template + variables | Resolved prompt | Variable substitution |
| **LLM Response** | Streaming chunks | Extracted JSON | Variable extraction |
| **Condition Eval** | Expression string | Boolean | Safe eval with context |
| **Loop Index** | Integer → Integer+1 | Loop counter | Iteration tracking |
| **Checkpoint** | Full execution state | JSON blob | State serialization |

### 3.3 Bottlenecks

#### Critical Bottleneck #7: Sequential Node Execution
**Location**: `/backend/app/workflow/workflow_engine.py:577-583`
```python
for child in node.children:
    await self.execute_workflow(child)
```

**Impact**:
- No parallel execution of independent branches
- Sequential processing even when nodes could run concurrently
- Long workflows block entirely

**Commented Code**: Evidence of attempted parallelization (lines 536-543, 578-582)

#### Critical Bottleneck #8: Synchronous Docker Operations
**Location**: `/backend/app/workflow/sandbox.py:223-239`
```python
async def _exec_container(self, command: str, timeout: int):
    def _sync_exec():
        exec_id = self.container.exec_run(cmd=f"sh -c '{command}'", demux=True)
        return exec_id

    exit_code, (stdout, stderr) = await asyncio.wait_for(
        loop.run_in_executor(None, _sync_exec), timeout=timeout
    )
```

**Impact**:
- Each code node blocks on Docker exec_run
- Thread pool executor used but still blocking per node
- No container reuse for multiple executions

#### Critical Bottleneck #9: In-Memory Context Accumulation
**Location**: `/backend/app/workflow/workflow_engine.py:243-258`
```python
def _cleanup_context_if_needed(self):
    if self._total_context_entries > MAX_CONTEXT_ENTRIES:
        # Remove oldest entries...
```

**Impact**:
- Context grows unbounded until cleanup threshold
- Cleanup happens DURING execution (adds latency)
- MAX_CONTEXT_ENTRIES=1000, MAX_CONTEXT_SIZE=50 per node

---

## 4. Error Propagation Analysis

### 4.1 Error Propagation Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ ERROR SOURCES                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. FILE UPLOAD ERRORS                                      │
│    - Invalid file format                                    │
│    - MinIO connection failure                               │
│    - File size exceeds limits                               │
│    ↓                                                        │
│    HTTP 400/500 → User feedback                            │
│                                                             │
│ 2. KAFKA PRODUCER ERRORS                                   │
│    - Broker unavailable                                     │
│    - Message serialization failure                          │
│    ↓                                                        │
│    Logged + HTTP 500                                       │
│    (No retry at producer level)                            │
│                                                             │
│ 3. KAFKA CONSUMER ERRORS                                   │
│    - Deserialization failure                                │
│    → DLQ (task_generation_dlq)                             │
│    - Processing failure (retriable)                        │
│    → Retry 3x with backoff                                 │
│    - Processing failure (non-retriable)                    │
│    → DLQ + cleanup metadata                                │
│                                                             │
│ 4. EMBEDDING SERVICE ERRORS                                │
│    - Connection timeout                                     │
│    → Circuit breaker OPEN                                  │
│    → Fail fast for 60s                                     │
│    - OOM / CUDA errors                                      │
│    → Recoverable (no cleanup)                              │
│    - Model load failure                                     │
│    → Non-recoverable (cleanup Milvus/Mongo)                │
│                                                             │
│ 5. MILVUS ERRORS                                           │
│    - Collection not found                                   │
│    → Auto-create (if during upload)                        │
│    - Insert failure                                         │
│    → Logged + partial rollback                             │
│    - Search timeout                                         │
│    → Empty results + fallback to LLM without context      │
│                                                             │
│ 6. MONGODB ERRORS                                          │
│    - Duplicate key                                          │
│    → Return error status                                   │
│    - Connection pool exhausted                              │
│    → Retry + log                                           │
│    - Update failure                                         │
│    → Continue (eventual consistency)                       │
│                                                             │
│ 7. WORKFLOW EXECUTION ERRORS                               │
│    - Sandbox execution failure                              │
│    → Rollback to checkpoint                               │
│    - LLM timeout/failure                                    │
│    → Retry 3x + circuit breaker                           │
│    - Loop limit exceeded                                    │
│    → Forced break (LOOP_LIMITS['condition']=1000)         │
│    - User cancellation                                      │
│    → Cleanup + status='canceled'                           │
│                                                             │
│ 8. LLM PROVIDER ERRORS                                     │
│    - API timeout                                            │
│    → Retry with backoff                                    │
│    - Rate limit (429)                                       │
│    → Circuit breaker + exponential backoff                │
│    - Invalid response                                       │
│    → Logged + error chunk to Redis                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Error Recovery Strategies

| Error Type | Detection | Recovery | Cleanup |
|------------|-----------|----------|---------|
| **File Processing Failure** | Exception in process_file() | Skip file, update Redis | Delete Milvus vectors, Mongo metadata |
| **Embedding OOM** | "out of memory" in error | Retry (recoverable) | No cleanup |
| **Docker Sandbox Failure** | ContainerError | Rollback checkpoint | Remove container |
| **LLM Failure** | Circuit breaker | Retry 3x → fail | Log error event |
| **Kafka Consumer Crash** | Exception in consume_messages() | Restart consumer | Commit last successful offset |
| **Workflow Node Failure** | Exception in execute_node() | Rollback checkpoint | Restore state from Redis |

### 4.3 Error Propagation Antipatterns

#### Antipattern #1: Silent Failures in Context Building
**Location**: `/backend/app/rag/utils.py:276-288`
```python
if image_base64:
    new_item = copy.deepcopy(item)
    new_item["image_url"] = {"url": f"data:image/png;base64,{image_base64}"}
    new_content.append(new_item)
else:
    # Missing else branch - image silently dropped
```

**Impact**: Images fail to load but query continues without context

#### Antipattern #2: Partial Rollback Without Transaction
**Location**: `/backend/app/rag/utils.py:189-211`
```python
try:
    db = await get_mongo()
    if kb_file_added:
        await db.delete_file_from_knowledge_base(...)
    elif file_record_created:
        await db.delete_files_bulk([file_meta["file_id"]])
except Exception as cleanup_error:
    logger.warning(f"failed to cleanup mongo/minio: {cleanup_error}")
    # Cleanup failure is logged but not propagated
```

**Impact**: Orphaned data in Mongo/MinIO/Milvus on partial failures

#### Antipattern #3: Circuit Bypass in Workflows
**Location**: `/backend/app/workflow/workflow_engine.py:930-966`
```python
@llm_service_circuit
async def _llm_call_with_circuit_breaker(...):
    # Circuit breaker decorated
    return ChatService.create_chat_stream(...)

async def _llm_call_with_retry(...):
    async def _do_call():
        return await self._llm_call_with_circuit_breaker(...)
    return await retry_with_backoff(_do_call, max_retries=3)
```

**Impact**: Retry after circuit breaker could flood degraded service

---

## 5. Data Consistency Analysis

### 5.1 Transaction Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│ TRANSACTION BOUNDARIES                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. FILE UPLOAD (No Transaction)                            │
│    MinIO upload → Kafka message → Response                 │
│                                                             │
│    CONSISTENCY: EVENTUAL                                    │
│    - MinIO: Immediate                                      │
│    - Kafka: Immediate (fire-and-forget)                   │
│    - Milvus: Async (after Kafka consumption)              │
│    - Mongo: Async (after Kafka consumption)               │
│                                                             │
│    FAILURE MODE:                                            │
│    - Kafka succeeds, consumer fails → Orphaned MinIO file  │
│    - Consumer succeeds, Milvus fails → Orphaned Mongo doc  │
│                                                             │
│ 2. QUERY EXECUTION (No Transaction)                        │
│    Milvus search → Context build → LLM call               │
│                                                             │
│    CONSISTENCY: READ-COMMITTED                              │
│    - Milvus: Eventually consistent with uploads            │
│    - LLM: External consistency (idempotent)                │
│                                                             │
│ 3. WORKFLOW EXECUTION (Checkpoint-Based)                   │
│    Node execution → State update → Checkpoint             │
│                                                             │
│    CONSISTENCY: EVENTUAL WITH ROLLBACK                     │
│    - Redis: Immediate (state, events)                      │
│    - Sandbox: Volatile (lost on rollback)                 │
│    - MongoDB: Async (if chatflow output)                  │
│                                                             │
│    ROLLBACK SCOPE:                                          │
│    - Restore: global_variables, execution_status, context  │
│    - Lost: Sandbox container state, external API calls     │
│                                                             │
│ 4. KAFKA CONSUMPTION (Manual Commit)                       │
│    Process → Mark processed → Commit offset               │
│                                                             │
│    CONSISTENCY: AT-LEAST-ONCE                               │
│    - Idempotency keys prevent double-processing            │
│    - Manual commit ensures no data loss                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Data Consistency Issues

#### Issue #1: MinIO-Milvus-Mongo Orphan Detection
**Problem**: No atomic transaction across storage systems

**Scenario**:
1. File uploaded to MinIO ✓
2. Kafka message sent ✓
3. Consumer starts processing
4. Milvus insert succeeds ✓
5. Mongo insert fails ✗

**Result**: Vectors exist in Milvus with no metadata in Mongo

**Mitigation**: Cleanup logic in `process_file()` exception handler, but best-effort only

#### Issue #2: Redis State Expiration
**Problem**: Workflow state expires after 1 hour

**Scenario**:
1. Workflow pauses for user input
2. User doesn't resume within 1 hour
3. State expires in Redis
4. User tries to resume → "Workflow expired!"

**Impact**: Lost work, no recovery mechanism

#### Issue #3: Eventual Consistency in Search
**Problem**: Milvus search may miss recently uploaded files

**Scenario**:
1. User uploads file
2. User immediately queries
3. File still being processed by Kafka consumer
4. Search returns no results for uploaded file

**Current Mitigation**: None (file appears in search after processing)

#### Issue #4: Checkpoint Rollback Limitations
**Problem**: Checkpoint doesn't capture external state

**What's Saved**:
- global_variables
- execution_status
- execution_stack
- loop_index
- context
- nodes, edges

**What's NOT Saved**:
- Docker container state (sandbox)
- External API call results
- MCP tool call results
- LLM token usage

**Impact**: Rollback loses sandbox modifications

---

## 6. Recommendations

### 6.1 High-Priority Bottleneck Fixes

1. **Parallelize PDF Conversion**
   - Use multiprocessing pool for file conversion
   - Implement per-file progress callbacks
   - Target: Reduce conversion time by 60%

2. **Pipeline Embedding Generation**
   - Overlap embedding batches with Milvus insertion
   - Use background threads for network I/O
   - Target: Reduce embedding latency by 40%

3. **Cache Converted Images**
   - Store base64 images in Redis after first conversion
   - Use TTL matching conversation duration
   - Target: Eliminate redundant MinIO downloads

4. **GPU-Accelerated MaxSim**
   - Move reranking to embedding service (GPU)
   - Return pre-ranked results from Milvus
   - Target: Reduce reranking time by 80%

### 6.2 Data Consistency Improvements

1. **Implement Saga Pattern for File Upload**
   - Define compensating transactions for each step
   - Track saga state in Redis
   - Automatic cleanup on failure

2. **Add Orphan Detection Job**
   - Scheduled task to find Milvus vectors without Mongo metadata
   - Find MinIO files without Mongo metadata
   - Cleanup or alert based on age

3. **Extend Workflow State TTL**
   - Implement checkpoint archival to MongoDB
   - Allow state restoration after Redis expiration
   - Add user notification for expiring workflows

4. **Add Search Indexing Status**
   - Track file processing status in Mongo
   - Return "processing" status in search results
   - Allow user to wait for completion

### 6.3 Error Handling Enhancements

1. **Structured Error Responses**
   - Define error taxonomy (recoverable/non-recoverable)
   - Include recovery suggestions in error messages
   - Standardize error codes across services

2. **Dead Letter Queue Processing**
   - Implement DLQ monitoring dashboard
   - Add automated retry for transient errors
   - Manual intervention workflow for permanent failures

3. **Circuit Breaker Monitoring**
   - Export circuit breaker state to Prometheus
   - Alert when circuit opens
   - Automated health checks when closed

---

## 7. Architecture Observations

### Strengths

1. **Event-Driven Design**: Kafka enables asynchronous processing
2. **Idempotency**: Redis keys prevent duplicate processing
3. **Fault Tolerance**: Circuit breakers, retries, DLQ
4. **Streaming**: Real-time feedback via Redis streams
5. **Sandboxing**: Docker isolation for code execution

### Weaknesses

1. **No Distributed Transactions**: Cross-system consistency is best-effort
2. **Sequential Bottlenecks**: Many operations are synchronous
3. **Limited Parallelism**: Commented-out parallel code suggests failed attempts
4. **Memory Pressure**: In-memory context accumulation
5. **TTL-Based Cleanup**: No graceful shutdown for expiring data

### Technical Debt

1. **1500-line MongoDB class**: Needs repository pattern (see TODO comment)
2. **Context Cleanup**: Triggered during execution, not proactively
3. **Error Swallowing**: Some cleanup failures are logged but not propagated
4. **Hardcoded Limits**: Batch sizes, timeouts, loop limits scattered in code

---

## Appendix: File Reference

| Component | File Path | Key Functionality |
|-----------|-----------|-------------------|
| Chat API | `/backend/app/api/endpoints/chat.py` | File upload, conversation management |
| File Conversion | `/backend/app/rag/convert_file.py` | PDF/Office → Images, DPI adaptation |
| Embedding | `/backend/app/rag/get_embedding.py` | ColQwen/Jina API integration |
| File Processing | `/backend/app/rag/utils.py` | Embed generation, Milvus insert, Mongo update |
| Kafka Consumer | `/backend/app/utils/kafka_consumer.py` | Message consumption, retry, DLQ |
| Milvus Client | `/backend/app/db/milvus.py` | MaxSim search, vector insert |
| MongoDB Client | `/backend/app/db/mongo.py` | Metadata persistence |
| Workflow Engine | `/backend/app/workflow/workflow_engine.py` | Node execution, state management |
| Sandbox | `/backend/app/workflow/sandbox.py` | Docker container execution |
| LLM Provider | `/backend/app/rag/provider_client.py` | Multi-provider client factory |

---

**Document Version**: 1.0
**Last Updated**: 2026-01-28
**Author**: Data Engineering Analysis

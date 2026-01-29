# Complete Database Schema Documentation

## Architecture Overview

This system uses a **polyglot persistence architecture** with 5 specialized databases:

```
+----------------+     +----------------+     +----------------+
|   MongoDB      |     |    Milvus      |     |    Redis       |
| (Document)     |     |  (Vector DB)   |     |  (Cache/Store) |
+----------------+     +----------------+     +----------------+
| knowledge_base |     | colqwen_*      |     | token:*        |
| files          |---->| collections    |     | task:*         |
| conversations  |     | (HNSW Index)   |     | model_config:* |
| chatflows      |     +----------------+     | user:*         |
| workflows      |             |             | kb:*           |
| model_config   |             |             | search:*       |
| nodes          |             |             +----------------+
+----------------+             |
          |                    |
          v                    v
+----------------+     +----------------+     +----------------+
|    MinIO       |     |     MySQL      |     |   Qdrant*      |
| (Object Store) |     | (Session Log)  |     |  (Alt Vector)  |
+----------------+     +----------------+     +----------------+
| Bucket:        |     | sessions       |     | (Optional)     |
| layra-bucket   |     | (Alembic)      |     +----------------+
+----------------+     +----------------+
```

*Qdrant is an alternative vector database (configured via VECTOR_DB env var)

---

## 1. MongoDB Collections

### Collection: `knowledge_bases`

**Purpose**: Central metadata for all knowledge bases (document repositories)

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "knowledge_base_id": "uuid",          // Primary Key
  "knowledge_base_name": "string",
  "username": "string",                 // Owner (multi-tenant)
  "files": [{                           // Embedded array
    "file_id": "uuid",
    "filename": "string",
    "minio_filename": "string",
    "minio_url": "string",
    "created_at": ISODate("...")
  }],
  "used_chat": ["kb_id1", "kb_id2"],    // Referenced KBs
  "created_at": ISODate("..."),
  "last_modify_at": ISODate("..."),
  "is_delete": false
}
```

**Indexes**:
```python
# Unique indexes
create_index([("knowledge_base_id", 1)], unique=True)  # Primary key
create_index([("username", 1)], unique=True)           # For model_config

# Compound indexes
create_index([("username", 1), ("is_delete", 1)])      # User KB queries
create_index([("files.filename", 1)])                  # Filename search

# TTL Index (missing but recommended)
# create_index([("created_at", 1)], expireAfterSeconds=7776000)  # 90 days
```

**Relationships**:
- `files.file_id` -> `files.file_id` (logical reference, not enforced)
- `username` -> `model_config.username` (user ownership)
- `used_chat[]` -> `knowledge_bases.knowledge_base_id` (cascading delete)

**Data Growth**: ~1KB per KB + ~500B per file reference

---

### Collection: `files`

**Purpose**: File metadata with embedded image/page references

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "file_id": "uuid",                    // Primary Key
  "filename": "string",
  "username": "string",
  "minio_filename": "string",
  "minio_url": "string",
  "knowledge_db_id": "uuid",            // FK: knowledge_bases
  "images": [{                          // Embedded array
    "images_id": "uuid",
    "minio_filename": "string",
    "minio_url": "string",
    "page_number": "int"
  }],
  "created_at": ISODate("..."),
  "last_modify_at": ISODate("..."),
  "is_delete": false
}
```

**Indexes**:
```python
create_index([("file_id", 1)], unique=True)
create_index([("knowledge_db_id", 1)])              # KB lookup
create_index([("filename", 1)])                    # Filename search
# Missing: compound index for (knowledge_db_id, is_delete)
```

**Relationships**:
- `knowledge_db_id` -> `knowledge_bases.knowledge_base_id` (soft reference)
- `images[]` -> Milvus vectors via `image_id`

**Data Growth**: ~800B per file + ~300B per image

---

### Collection: `conversations`

**Purpose**: Chat sessions with turn history and model config

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "conversation_id": "uuid",             // Primary Key
  "conversation_name": "string",
  "username": "string",
  "model_config": {
    "model_id": "string",
    "temperature": 0.7,
    "max_length": 2048,
    // ... model params
  },
  "turns": [{                            // Embedded array
    "message_id": "uuid",
    "parent_message_id": "uuid",         // Threaded conversations
    "user_message": "string",
    "ai_message": "string",
    "temp_db": "kb_id",                  // Temporary KB reference
    "file_used": ["file_id1", ...],
    "status": "completed",
    "timestamp": ISODate("..."),
    "total_token": 1500,
    "completion_tokens": 800,
    "prompt_tokens": 700
  }],
  "created_at": ISODate("..."),
  "last_modify_at": ISODate("..."),
  "is_read": false,
  "is_delete": false
}
```

**Indexes**:
```python
create_index([("conversation_id", 1)], unique=True)
create_index([("username", 1), ("last_modify_at", -1)])  # User conversations
# Missing: index on turns.temp_db for temp KB cleanup
```

**Relationships**:
- `turns.temp_db` -> `knowledge_bases.knowledge_base_id` (cascading delete)
- `turns.file_used[]` -> `files.file_id`

**Data Growth**: ~1KB per conversation + ~500B per turn

---

### Collection: `chatflows`

**Purpose**: Workflow execution instances (similar to conversations)

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "chatflow_id": "uuid",                // Primary Key
  "workflow_id": "uuid",                // FK: workflows
  "chatflow_name": "string",
  "username": "string",
  "turns": [{ /* same structure as conversations */ }],
  "created_at": ISODate("..."),
  "last_modify_at": ISODate("..."),
  "is_read": false,
  "is_delete": false
}
```

**Indexes**:
```python
create_index([("chatflow_id", 1)], unique=True)
create_index([("workflow", 1), ("last_modify_at", -1)])  # Bug: should be workflow_id
```

**Relationships**:
- `workflow_id` -> `workflows.workflow_id`

---

### Collection: `workflows`

**Purpose**: Workflow definitions (nodes, edges, variables)

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "workflow_id": "uuid",                // Primary Key (composite)
  "username": "string",                 // Owner (composite key)
  "workflow_name": "string",
  "nodes": [{                           // Embedded array
    "id": "node_1",
    "type": "code|condition|http|...",
    "data": { /* node-specific config */ }
  }],
  "edges": [{                           // Graph structure
    "id": "edge_1",
    "source": "node_1",
    "target": "node_2",
    "condition": null
  }],
  "start_node": "node_start",
  "global_variables": {},
  "workflow_config": {},
  "created_at": ISODate("..."),
  "last_modify_at": ISODate("..."),
  "is_delete": false
}
```

**Indexes**:
```python
# Composite unique index (user-scoped workflows)
create_index([("username", 1), ("workflow_id", 1)], unique=True)
create_index([("username", 1), ("last_modify_at", -1)])  # User workflows
```

**Relationships**:
- `(username, workflow_id)` -> `chatflows.workflow_id` (one-to-many)

---

### Collection: `model_config`

**Purpose**: User's LLM model configurations

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "username": "string",                 // Primary Key
  "selected_model": "model_id",
  "models": [{                          // Embedded array
    "model_id": "uuid",
    "model_name": "string",
    "model_url": "string",
    "api_key": "********",
    "base_used": ["knowledge_base_id1", ...],
    "system_prompt": "string",
    "temperature": 0.7,
    "max_length": 2048,
    "top_P": 0.9,
    "top_K": 50,
    "score_threshold": 0.5
  }]
}
```

**Indexes**:
```python
create_index([("username", 1)], unique=True)
```

---

### Collection: `nodes`

**Purpose**: Custom node definitions per user

**Schema**:
```javascript
{
  "_id": ObjectId("..."),
  "username": "string",                 // Primary Key
  "custom_nodes": {
    "node_name_1": {
      "type": "function",
      "config": { /* node definition */ }
    },
    "node_name_2": { ... }
  }
}
```

**Indexes**:
```python
create_index([("username", 1)], unique=True)
```

---

## MongoDB Index Analysis

### Current Index Coverage

| Collection | Covered Queries | Missing Indexes | Performance Impact |
|------------|----------------|-----------------|-------------------|
| knowledge_bases | KB by ID, user KBs | `files.filename` search slow | Low-Medium |
| files | File by ID, KB files | `(knowledge_db_id, is_delete)` | Medium |
| conversations | Conv by ID, user conversations | `turns.temp_db` cleanup | Low |
| chatflows | Chatflow by ID | `workflow_id` lookup (bug) | **High** |
| workflows | User workflows | None | Good |
| model_config | User config | None | Good |
| nodes | User nodes | None | Good |

### Recommended New Indexes

```python
# knowledge_bases
await db.knowledge_bases.create_index([("last_modify_at", -1)])  # For sorting

# files
await db.files.create_index([("knowledge_db_id", 1), ("is_delete", 1)])
await db.files.create_index([("username", 1), ("is_delete", 1)])

# conversations
await db.conversations.create_index([("turns.temp_db", 1)], sparse=True)

# chatflows - FIX BUG
await db.chatflows.drop_index("workflow_chatflows")
await db.chatflows.create_index([("workflow_id", 1), ("last_modify_at", -1)])

# TTL indexes for cleanup
await db.conversations.create_index(
    [("last_modify_at", 1)],
    expireAfterSeconds=7776000  # 90 days
)
```

---

## 2. Milvus Vector Collections

### Collection Naming Pattern

```
colqwen{knowledge_base_id}
```

Example: `colqwen123e4567-e89b-12d3-a456-426614174000` (hyphens replaced with underscores)

### Collection Schema

```python
# Fixed schema for all KB collections
schema = MilvusSchema(
    auto_id=True,                       # Auto-generate pk (INT64)
    enable_dynamic_fields=True          # Allow additional fields
)

fields = [
    FieldSchema("pk", DataType.INT64, is_primary=True),
    FieldSchema("vector", DataType.FLOAT_VECTOR, dim=128),  # ColQwen embedding
    FieldSchema("image_id", DataType.VARCHAR, max_length=65535),
    FieldSchema("page_number", DataType.INT64),
    FieldSchema("file_id", DataType.VARCHAR, max_length=65535),
]
```

### Index Configuration (HNSW)

```python
index_params = {
    "index_type": "HNSW",
    "metric_type": "IP",                # Inner Product (cosine-like)
    "params": {
        "M": 32,                        # Max connections per node (default: 16)
        "efConstruction": 500           # Build-time candidates (default: 200)
    }
}
```

**HNSW Tuning**:
- `M=32`: Higher recall, more memory (good for <1M vectors)
- `efConstruction=500`: Better index quality, slower build
- Search `ef=100`: Tradeoff between speed/accuracy

### Vector Statistics

| Metric | Value | Notes |
|--------|-------|-------|
| Dimension | 128 | ColQwen page-image embeddings |
| Metric | Inner Product | Normalized vectors |
| Index Type | HNSW | Hierarchical Navigable Small World |
| Vectors per Page | ~10-50 | One per image token |
| Collection Growth | ~50KB/page | 128 floats * 4 bytes |

### Collection Lifecycle

```
1. KB Created      -> create_collection(kb_id)
2. Files Uploaded  -> insert(vectors, image_id, page_number, file_id)
3. Query           -> search(query_vectors, topk) -> MaxSim reranking
4. File Deleted    -> delete_files(collection_name, [file_id])
5. KB Deleted      -> drop_collection(collection_name)
```

### Missing Milvus Features

1. **No scalar indexes**: Only `pk` and `vector` are indexed
2. **No filtering support**: `file_id` filter scans all vectors
3. **No partitioning**: All KBs in same collection would need partition key

---

## 3. MySQL Schema

### Current Status

- **Engine**: SQLAlchemy Async (PostgreSQL-compatible syntax)
- **Migration Tool**: Alembic
- **Current Revision**: `3c4c5bdddb2c_init_mysql.py` (EMPTY - no tables defined)
- **Purpose**: Session logging (planned, not implemented)

### Configuration

```python
# Connection pooling
engine = create_async_engine(
    settings.db_url,
    echo=settings.debug_mode,          # Query logging
    pool_size=settings.db_pool_size,   # Default: 10
    max_overflow=settings.db_max_overflow,  # Default: 20
    pool_pre_ping=True,                # Health check
)
```

### Planned Schema (Not Yet Implemented)

Based on code analysis, MySQL should store:

```sql
-- Session logging (suggested)
CREATE TABLE sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    INDEX idx_username (username),
    INDEX idx_session_id (session_id)
);

-- Audit log (suggested)
CREATE TABLE audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB,
    INDEX idx_username_time (username, timestamp),
    INDEX idx_resource (resource_type, resource_id)
);
```

### MySQL Usage Patterns

Currently **NOT USED** for application data. Only configured for future session logging.

---

## 4. Redis Data Structures

### Database Isolation

```python
# Redis databases (logical separation)
redis_token_db = 0      # JWT token blacklist
redis_task_db = 1       # Background task progress
redis_lock_db = 2       # Distributed locks
redis_cache_db = 3      # Application cache (default)
```

### Key Patterns and TTLs

#### Token Management (DB: 0)

```
Pattern:      token:{jwt_token}
Type:         String
Value:        "valid" | "blacklisted"
TTL:          Token expiration (~7 days default)
Purpose:      Token blacklist for logout
Operations:   GET, SETEX
```

#### Task Progress Tracking (DB: 1)

```
Pattern:      task:{task_id}
Type:         Hash
Fields:       {
                status: "pending" | "processing" | "completed" | "failed",
                message: "Processing file 3/10...",
                processed: 3,
                total: 10
              }
TTL:          3600s (1 hour)
Purpose:      SSE-based progress updates for file ingestion
Operations:   HSET, HGET, HINCRBY, EXPIRE
```

#### Model Config Cache (DB: 3)

```
Pattern:      model_config:{username}
Type:         String (JSON)
Value:        {models: [...], selected_model: "..."}
TTL:          1800s (30 minutes)
Purpose:      Cache frequently accessed model configs
Operations:   GET, SETEX
```

#### User Data Cache (DB: 3)

```
Pattern:      user:{username}
Type:         String (JSON)
Value:        {email: "...", created_at: "...", ...}
TTL:          3600s (1 hour)
Purpose:      Reduce MongoDB queries for user profile
Operations:   GET, SETEX
```

#### Knowledge Base Metadata Cache (DB: 3)

```
Pattern:      kb:{kb_id}
Type:         String (JSON)
Value:        {name: "...", file_count: 5, ...}
TTL:          1800s (30 minutes)
Purpose:      Cache KB metadata for listing
Operations:   GET, SETEX
```

#### Search Results Cache (DB: 3)

```
Pattern:      search:{query_hash}
Type:         String (JSON)
Value:        {results: [...], score: ...}
TTL:          600s (10 minutes)
Purpose:      Deduplicate identical RAG queries
Operations:   GET, SETEX
```

### Redis Memory Estimation

| Pattern | Keys | Avg Size | Total Memory | TTL Strategy |
|---------|------|----------|--------------|--------------|
| `token:*` | ~100/user | 200B | ~20KB/user | Auto-expire |
| `task:*` | ~1/ingestion | 500B | ~500B (transient) | 1 hour |
| `model_config:*` | ~1/user | 2KB | ~2KB/user | 30 min |
| `user:*` | ~1/user | 1KB | ~1KB/user | 1 hour |
| `kb:*` | ~5/user | 800B | ~4KB/user | 30 min |
| `search:*` | ~10/user | 5KB | ~50KB/user | 10 min |
| **Total/User** | | | **~77KB/user** | |

**For 1000 users**: ~77MB (comfortable for 512MB Redis instance)

### Missing Redis Patterns

1. **Rate limiting**: No `ratelimit:*` pattern found
2. **Distributed locks**: `lock:*` DB configured but no usage found
3. **Session storage**: No `session:*` pattern (using MongoDB)

---

## 5. MinIO Object Storage

### Bucket Configuration

```
Bucket Name:    layra-bucket
Endpoint:       {MINIO_URL}
Access Key:     {MINIO_ACCESS_KEY}
Secret Key:     {MINIO_SECRET_KEY}
Public URL:     {MINIO_PUBLIC_URL}
SSL:            false (development)
```

### Object Naming Convention

```
{original_filename}_{uuid}.{ext}

Examples:
- document_abc123.pdf
- page_image_def456.png
- uploaded_file_ghi789.pdf
```

### Object Types

| Type | Prefix | Size Range | Retention |
|------|--------|------------|-----------|
| Original Files | `{filename}_{uuid}` | 100KB-50MB | Referenced by MongoDB |
| Page Images | `page_*_{uuid}.png` | 50KB-500KB | Embedded in files.images[] |
| Thumbnails | `thumb_*_{uuid}.png` | 10KB-50KB | Not implemented |

### Presigned URL Generation

```python
# Long-lived URLs (default)
expires = 3153600000  # 100 years (effectively permanent)

# Public URL fallback
MINIO_PUBLIC_URL or {server_ip}:{minio_public_port}
```

**Security Issue**: 100-year expiration effectively makes all objects public if URL leaks.

### Storage Estimation

| Resource | Avg Size | Files/KB | Total Size/KB |
|----------|----------|----------|---------------|
| PDF Document | 2MB | 10 | 20MB |
| Page Image | 150KB | 200 | 30MB |
| **Per KB** | | | **50MB** |
| **1000 KBs** | | | **50GB** |

---

## 6. Entity-Relationship Diagram (Text-Based)

```
                      +------------------+
                      |   MongoDB Core   |
                      +------------------+

+----------------+     +----------------+     +----------------+
| knowledge_bases|<--->|      files      |     |   conversations|
|                |     |                |     |                |
| - kb_id (PK)   |     | - file_id (PK) |     | - conv_id (PK) |
| - username     |     | - kb_id (FK)   |     | - username     |
| - files[]      |     | - username     |     | - turns[]      |
| - used_chat[]  |     | - images[]     |     | - model_config |
+----------------+     +----------------+     +----------------+
       |                                                    |
       | .files[]                                           | .turns.temp_db
       v                                                    v
+----------------+                                  +----------------+
|   MinIO Bucket  |                                  |  Temp KBs      |
|                |                                  | (auto-created) |
| - {uuid}.pdf   |                                  +----------------+
| - page_{n}.png |
+----------------+
       ^
       | .images[].minio_url
       |
+----------------+     +----------------+     +----------------+
|     Milvus     |     |    chatflows    |     |    workflows   |
|                |     |                |     |                |
| colqwen{kb_id} |     | - cf_id (PK)   |     | - wf_id (PK)   |
|                |     | - wf_id (FK)   |<----| - username     |
| - vector[]     |     | - turns[]      |     | - nodes[]      |
| - image_id     |     +----------------+     | - edges[]      |
| - file_id      |                            +----------------+
+----------------+                                     ^
       ^                                              |
       | .images[]                                     | .username
       |                                              |
       |                                    +------------------+
       |                                    |    model_config   |
       |                                    |                  |
       |                                    | - username (PK)  |
       |                                    | - models[]       |
       |                                    | - selected_model |
       |                                    +------------------+
       |                                              ^
       |                                              |
       |                                    +------------------+
       |                                    |      nodes       |
       |                                    |                  |
       +------------------------------------| - username (PK)  |
                                             | - custom_nodes{} |
                                             +------------------+


                      +------------------+
                      |     Redis        |
                      +------------------+

token:*       -> JWT blacklist (DB: 0)
task:*        -> Ingestion progress (DB: 1)
model_config:*-> Config cache (DB: 3)
user:*        -> User profile cache (DB: 3)
kb:*          -> KB metadata cache (DB: 3)
search:*      -> Query result cache (DB: 3)
```

---

## 7. Data Consistency Patterns

### Current Consistency Model

| Relationship | Type | Enforcement | Cascade Actions |
|--------------|------|-------------|-----------------|
| KB -> Files | 1:N | Application-level | Delete KB deletes files |
| Files -> Images | 1:N | Embedded array | Delete file deletes MinIO images |
| KB -> Milvus | 1:1 | Application-level | Delete KB drops collection |
| Conversation -> Temp KB | 1:1 | Reference in turns | Delete conv deletes temp KB |
| Workflow -> Chatflow | 1:N | Application-level | Delete workflow deletes chatflows |
| User -> Model Config | 1:1 | Unique index | Delete user deletes config |

### Consistency Gaps

1. **No foreign keys**: All relationships are application-enforced
2. **Orphaned vectors**: If MinIO image deleted before Milvus cleanup
3. **Stale cache**: No cache invalidation on updates
4. **Partial deletes**: File deletion may leave MongoDB records if MinIO fails

### Recommended Improvements

```python
# 1. Transactional cleanup
async def delete_knowledge_base(kb_id: str):
    async with asyncio.TaskGroup() as tg:
        # Parallel cleanup
        tg.create_task(delete_milvus_collection(kb_id))
        tg.create_task(delete_mongo_kb(kb_id))
        tg.create_task(delete_minio_files(kb_id))
        tg.create_task(invalidate_cache(kb_id))

# 2. Cache invalidation
async def update_kb_metadata(kb_id: str, metadata: dict):
    await mongo.update_kb(kb_id, metadata)
    await redis.delete(f"kb:{kb_id}")

# 3. Soft delete with cleanup job
await mongo.update_kb(kb_id, {"is_delete": True})
# Background job deletes actual data after 7 days
```

---

## 8. Index Effectiveness Analysis

### MongoDB Query Patterns vs Indexes

| Query | Index Used | Performance | Recommendation |
|-------|------------|-------------|----------------|
| `db.knowledge_bases.find_one({"knowledge_base_id": ...})` | `unique_kb_id` | **O(1)** | Optimal |
| `db.knowledge_bases.find({"username": ..., "is_delete": False})` | `user_kb_query` | **O(log n)** | Optimal |
| `db.knowledge_bases.aggregate([{"$unwind": "$files"}, ...])` | None | **O(n)** | Add compound index |
| `db.conversations.find({"username": ...}).sort("last_modify_at", -1)` | `user_conversations` | **O(log n)** | Optimal |
| `db.chatflows.find({"workflow_id": ...})` | `workflow_chatflows` (BUG) | **O(n)** | Fix index name |
| `db.files.find({"knowledge_db_id": ...})` | `kb_file_query` | **O(log n)** | Optimal |

### Milvus Query Performance

| Operation | Complexity | Factors |
|-----------|------------|---------|
| `search()` | `O(log n)` | HNSW index |
| MaxSim reranking | `O(k * d)` | k=candidates, d=vectors/page |
| `delete_files()` | `O(n)` | Filter expression scans all |

### Redis Access Patterns

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `GET/SETEX` | O(1) | Hash-based |
| `HSET/HGET` | O(1) | Hash fields |
| `KEYS pattern` | **O(n)** | AVOID in production |
| `DELETE key` | O(1) | Single key |

---

## 9. Scalability Recommendations

### MongoDB Scaling

| Metric | Current | Threshold | Action |
|--------|---------|-----------|--------|
| Documents/collection | <100K | 1M | Add sharding |
| Document size | <10KB | 16MB | Chunk large arrays |
| Index size | <100MB | 1GB | Remove unused indexes |
| Connections | 1000 | pool_size | Increase pool |

**Recommendations**:
```python
# 1. Shard by username (multi-tenant)
sh.shardCollection("layra.knowledge_bases", {"username": 1})

# 2. Time-series partition for conversations
sh.shardCollection("layra.conversations", {"username": 1, "created_at": 1})

# 3. Archive old conversations
db.conversations.delete_many({
    "last_modify_at": {"$lt": datetime.now() - timedelta(days=90)},
    "is_delete": True
})
```

### Milvus Scaling

| Metric | Current | Threshold | Action |
|--------|---------|-----------|--------|
| Vectors/collection | <1M | 10M | Add replicas |
| Collection count | <100 | 1000 | Use partition keys |
| Memory usage | <4GB | RAM | M=16 (increase) |

**Recommendations**:
```python
# 1. Enable partitioning (one partition per KB)
collection.create_partition(kb_id)

# 2. Increase index parameters for larger collections
index_params = {
    "M": 32,          # Keep for now
    "efConstruction": 500  # Increase to 1000 for >1M vectors
}

# 3. Search-time tuning
search_params = {
    "metric_type": "IP",
    "params": {"ef": 200}  # Increase for better recall
}
```

### Redis Scaling

| Metric | Current | Threshold | Action |
|--------|---------|-----------|--------|
| Memory usage | 100MB | 400MB | Add eviction policy |
| Keys | 10K | 1M | Use Redis Cluster |
| Ops/sec | 1K | 10K | Pipeline operations |

**Recommendations**:
```python
# 1. Add eviction policy
maxmemory-policy allkeys-lru

# 2. Pipeline batch operations
pipe = redis.pipeline()
for key in keys:
    pipe.get(key)
results = await pipe.execute()

# 3. Separate cache/session stores
redis_cache = Redis(db=3)
redis_sessions = Redis(db=4)
```

---

## 10. Migration Strategy

### Database Backup Commands

```bash
# MongoDB
mongodump --uri="mongodb://user:pass@host:27017/layra" --out=/backup/mongo

# Milvus (collection backup)
curl -X POST http://milvus:19530/backup/create \
  -d '{"collection_names": ["colqwen_kb1"]}'

# Redis
redis-cli --rdb /backup/redis/dump.rdb

# MinIO
mc mirror minio/layra-bucket /backup/minio/
```

### Rollback Strategy

```python
# 1. Versioned migrations (Alembic for MySQL)
alembic downgrade -1

# 2. MongoDB change log
db.migration_log.insert_one({
    "version": "v1.2.3",
    "changes": ["added index on files.knowledge_db_id"],
    "timestamp": datetime.now(),
    "rollback": "db.files.drop_index('kb_file_query_v2')"
})

# 3. Feature flags
settings.enable_new_indexes = True  # Gradual rollout
```

---

## 11. Critical Issues Summary

| Severity | Issue | Impact | Fix |
|----------|-------|--------|-----|
| **HIGH** | `chatflows` index uses `workflow` instead of `workflow_id` | All workflow queries are full table scans | Drop and recreate index |
| **MEDIUM** | No index on `files(knowledge_db_id, is_delete)` | KB file list queries slow | Add compound index |
| **MEDIUM** | MinIO presigned URL expires in 100 years | Security risk if URL leaked | Reduce to 24 hours |
| **LOW** | No TTL indexes for old conversations | Storage growth over time | Add 90-day TTL |
| **LOW** | Redis `KEYS` pattern usage (potential) | Blocks Redis during scan | Use `SCAN` instead |

---

## 12. File Locations Reference

| Database | Config | Schema | Manager |
|----------|--------|--------|---------|
| MongoDB | `/backend/app/core/config.py` | `/backend/app/db/mongo.py:23-105` | `/backend/app/db/mongo.py:18-1673` |
| Milvus | `/backend/app/core/config.py` | `/backend/app/db/milvus.py:68-87` | `/backend/app/db/milvus.py:7-285` |
| Redis | `/backend/app/core/config.py` | `/backend/app/db/redis.py` | `/backend/app/db/cache.py` |
| MySQL | `/backend/app/core/config.py` | `/backend/migrations/versions/*.py` | `/backend/app/db/mysql_session.py` |
| MinIO | `/backend/app/core/config.py` | N/A (object store) | `/backend/app/db/miniodb.py` |

---

## 13. Query Optimization Quick Reference

### MongoDB Optimization

```python
# Before: Collection scan
files = db.files.find({"knowledge_db_id": kb_id})

# After: Index scan
await db.files.create_index([("knowledge_db_id", 1), ("is_delete", 1)])
files = db.files.find({"knowledge_db_id": kb_id, "is_delete": False})

# Projection optimization
file = db.files.find_one(
    {"file_id": file_id},
    projection={"filename": 1, "minio_url": 1}  # Only return needed fields
)
```

### Milvus Optimization

```python
# Before: Fetch all vectors
results = client.search(collection, query_vectors, topk=100)

# After: Limit output fields
results = client.search(
    collection,
    query_vectors,
    topk=100,
    output_fields=["image_id", "file_id", "page_number"]  # Exclude vector
)
```

### Redis Optimization

```python
# Before: N+1 queries
for kb_id in kb_ids:
    kb = await redis.get(f"kb:{kb_id}")

# After: Pipeline/MGET
kb_data = await redis.mget([f"kb:{kb_id}" for kb_id in kb_ids])
```

---

**Generated**: 2026-01-28
**Database Version**: Current production schema
**Status**: Analysis complete - See critical issues for immediate action

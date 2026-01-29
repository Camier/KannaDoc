# Database Operations Quick Reference

## Connection Strings and Credentials

### MongoDB
```python
# Connection
mongodb://username:password@host:27017/layra

# Database Name
layra

# Collections
- knowledge_bases
- files
- conversations
- chatflows
- workflows
- model_config
- nodes

# Connection Pool
maxPoolSize: 50
minPoolSize: 10
```

### Milvus
```python
# Connection
milvus://localhost:19530

# Collection Pattern
colqwen{knowledge_base_id}

# Vector Dimension
128 (ColQwen embeddings)

# Index Type
HNSW (M=32, efConstruction=500)
```

### Redis
```python
# Connection
redis://:password@localhost:6379

# Databases
DB 0: Token blacklist
DB 1: Task progress tracking
DB 2: Distributed locks
DB 3: Application cache

# Default DB for operations: 3
```

### MySQL
```python
# Connection
mysql+aiomysql://user:pass@host:3306/layra

# Pool Settings
pool_size: 10
max_overflow: 20
pool_pre_ping: True

# Status: Not implemented (empty schema)
```

### MinIO
```python
# Connection
http://localhost:9000

# Bucket
layra-bucket

# Access
Access Key: {MINIO_ACCESS_KEY}
Secret Key: {MINIO_SECRET_KEY}

# Public URL
{MINIO_PUBLIC_URL} or {server_ip}:{minio_public_port}
```

---

## Common CRUD Operations

### MongoDB Operations

```python
from app.db.mongo import mongodb
await mongodb.connect()

# Knowledge Base
await mongodb.create_knowledge_base(username, name, kb_id, is_delete=False)
kb = await mongodb.get_knowledge_base_by_id(kb_id)
kbs = await mongodb.get_knowledge_bases_by_user(username)
await mongodb.update_knowledge_base_name(kb_id, new_name)
await mongodb.delete_knowledge_base(kb_id)

# Files
await mongodb.create_files(file_id, username, filename, minio_fn, url, kb_id)
await mongodb.add_images(file_id, img_id, minio_fn, url, page_num)
file_info = await mongodb.get_file_and_image_info(file_id, img_id)
await mongodb.delete_files_bulk([file_id1, file_id2])

# Conversations
await mongodb.create_conversation(conv_id, username, name, model_config)
conv = await mongodb.get_conversation(conv_id)
convs = await mongodb.get_conversations_by_user(username)
await mongodb.add_turn(conv_id, msg_id, parent, user_msg, ai_msg, files, temp_db)
await mongodb.delete_conversation(conv_id)

# Workflows
await mongodb.update_workflow(username, wf_id, name, config, nodes, edges)
wf = await mongodb.get_workflow(wf_id)
wfs = await mongodb.get_workflows_by_user(username)
await mongodb.delete_workflow(wf_id)

# Model Config
await mongodb.create_model_config(username, selected, models...)
await mongodb.add_model_config(username, model_id, ...)
await mongodb.update_model_config(username, model_id, ...)
config = await mongodb.get_selected_model_config(username)
await mongodb.delete_model_config(username, model_id)
```

### Milvus Operations

```python
from app.db.milvus import milvus_client

# Collection Management
milvus_client.create_collection(kb_id, dim=128)
milvus_client.check_collection(f"colqwen{kb_id}")
milvus_client.load_collection(f"colqwen{kb_id}")
milvus_client.delete_collection(f"colqwen{kb_id}")

# Insert Vectors
data = {
    "colqwen_vecs": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
    "image_id": "img_123",
    "page_number": 1,
    "file_id": "file_456"
}
milvus_client.insert(data, f"colqwen{kb_id}")

# Search
query_vectors = [[0.1, 0.2, ...], ...]  # Multi-vector (MaxSim)
results = milvus_client.search(f"colqwen{kb_id}", query_vectors, topk=10)

# Delete
milvus_client.delete_files(f"colqwen{kb_id}", ["file_123", "file_456"])
```

### Redis Operations

```python
from app.db.redis import redis
from app.db.cache import cache_service

# Token Management
conn = await redis.get_token_connection()
await conn.setex(f"token:{jwt}", 3600, "valid")
status = await conn.get(f"token:{jwt}")

# Task Progress
conn = await redis.get_task_connection()
await conn.hset(f"task:{task_id}", mapping={
    "status": "processing",
    "message": "Processing file 3/10",
    "processed": 3,
    "total": 10
})
await conn.expire(f"task:{task_id}", 3600)
task_data = await conn.hgetall(f"task:{task_id}")

# Cache Operations
await cache_service.set_model_config(username, config)
config = await cache_service.get_model_config(username)
await cache_service.invalidate_model_config(username)
await cache_service.invalidate_all_kb_metadata()
```

### MinIO Operations

```python
from app.db.miniodb import async_minio_manager

# Initialize (on startup)
await async_minio_manager.init_minio()

# Upload File
await async_minio_manager.upload_file(
    "document_abc123.pdf",
    upload_file_object
)

# Upload Image
await async_minio_manager.upload_image(
    "page_1_img_def456.png",
    image_stream
)

# Generate Presigned URL
url = await async_minio_manager.create_presigned_url(
    "document_abc123.pdf",
    expires=3600
)

# Download
file_data = await async_minio_manager.get_file_from_minio("document_abc123.pdf")

# Bulk Delete
await async_minio_manager.bulk_delete([
    "file1.pdf",
    "file2.pdf",
    "page_1.png"
])

# Check Existence
exists = await async_minio_manager.validate_file_existence("file.pdf")
```

---

## Query Examples

### Find All User Data

```python
# Get complete user profile
async def get_user_profile(username: str):
    model_config = await mongodb.db.model_config.find_one({"username": username})
    custom_nodes = await mongodb.db.nodes.find_one({"username": username})

    kbs = await mongodb.db.knowledge_bases.find({
        "username": username,
        "is_delete": False
    }).to_list(length=None)

    conversations = await mongodb.db.conversations.find({
        "username": username,
        "is_delete": False
    }).sort("last_modify_at", -1).to_list(length=None)

    workflows = await mongodb.db.workflows.find({
        "username": username,
        "is_delete": False
    }).sort("last_modify_at", -1).to_list(length=None)

    return {
        "username": username,
        "model_config": model_config,
        "custom_nodes": custom_nodes,
        "knowledge_bases": kbs,
        "conversations": conversations,
        "workflows": workflows
    }
```

### Search KB with Vector Query

```python
async def search_knowledge_base(kb_id: str, query_text: str, topk: int = 10):
    # 1. Get collection name
    collection_name = f"colqwen{kb_id.replace('-', '_')}"

    # 2. Generate query vectors (using embedding service)
    from app.core.embeddings import get_colqwen_embedding
    query_vectors = await get_colqwen_embedding(query_text)

    # 3. Search Milvus
    results = milvus_client.search(collection_name, query_vectors, topk)

    # 4. Fetch file metadata from MongoDB
    file_ids = [r["file_id"] for r in results]
    files_cursor = mongodb.db.files.find({"file_id": {"$in": file_ids}})
    files_dict = {f["file_id"]: f for f in await files_cursor.to_list(length=None)}

    # 5. Combine results
    return [
        {
            "score": r["score"],
            "image_id": r["image_id"],
            "page_number": r["page_number"],
            "file": files_dict.get(r["file_id"])
        }
        for r in results
    ]
```

### Cleanup Orphaned Data

```python
async def cleanup_orphaned_temp_kbs():
    """Find and delete temp KBs not referenced by any conversation"""
    # 1. Get all temp KB IDs from conversations
    pipeline = [
        {"$match": {"is_delete": False}},
        {"$unwind": "$turns"},
        {"$group": {"_id": "$turns.temp_db"}},
        {"$match": {"_id": {"$ne": "", "$ne": None}}}
    ]
    referenced_temp_kbs = await mongodb.db.conversations.aggregate(pipeline).to_list(length=None)
    referenced_ids = {kb["_id"] for kb in referenced_temp_kbs}

    # 2. Find all temp KBs
    all_temp_kbs = await mongodb.db.knowledge_bases.find({
        "knowledge_base_id": {"$regex": "^temp_"},
        "is_delete": False
    }).to_list(length=None)

    # 3. Delete orphaned ones
    orphaned = [kb for kb in all_temp_kbs if kb["knowledge_base_id"] not in referenced_ids]

    for kb in orphaned:
        await mongodb.delete_knowledge_base(kb["knowledge_base_id"])
        print(f"Deleted orphaned temp KB: {kb['knowledge_base_id']}")

    return len(orphaned)
```

---

## Backup and Restore

### MongoDB Backup

```bash
# Backup
mongodump \
  --uri="mongodb://user:pass@host:27017/layra" \
  --out=/backup/mongo/$(date +%Y%m%d)

# Restore
mongorestore \
  --uri="mongodb://user:pass@host:27017/layra" \
  /backup/mongo/20260128
```

### Milvus Backup

```python
# Via Milvus Backup tool (if installed)
# Or manual: Export all vectors

async def backup_milvus_collection(collection_name: str):
    all_data = []
    offset = 0
    limit = 1000

    while True:
        batch = milvus_client.client.query(
            collection_name=collection_name,
            filter="",  # All vectors
            output_fields=["vector", "image_id", "page_number", "file_id"],
            limit=limit,
            offset=offset
        )
        if not batch:
            break
        all_data.extend(batch)
        offset += limit

    # Save to file
    import json
    with open(f"/backup/milvus/{collection_name}.json", "w") as f:
        json.dump(all_data, f)

    return len(all_data)
```

### Redis Backup

```bash
# Trigger RDB snapshot
redis-cli BGSAVE

# Copy RDB file
cp /var/lib/redis/dump.rdb /backup/redis/

# Restore
redis-cli --rdb /backup/redis/dump.rdb
```

### MinIO Backup

```bash
# Using mc (MinIO Client)
mc mirror minio/layra-bucket /backup/minio/$(date +%Y%m%d)

# Restore
mc mirror /backup/minio/20260128 minio/layra-bucket
```

---

## Performance Tuning

### MongoDB Slow Query Log

```python
# Enable profiling
await mongodb.db.command("profile", 2)  # Log all operations

# Check slow queries
slow_queries = await mongodb.db.system.profile.find({
    "millis": {"$gt": 100}  # Slower than 100ms
}).sort({"ts": -1}).limit(10).to_list(length=None)

for q in slow_queries:
    print(f"Slow query took {q['millis']}ms")
    print(f"Query: {q['query']}")
```

### Redis Memory Analysis

```python
async def analyze_redis_memory():
    conn = await redis.get_redis_connection()

    # Get memory usage
    info = await conn.info("memory")
    print(f"Used memory: {info['used_memory_human']}")

    # Get key count
    key_count = 0
    for db_num in range(4):
        await conn.select(db_num)
        db_size = await conn.dbsize()
        key_count += db_size
        print(f"DB {db_num}: {db_size} keys")

    # Find large keys
    large_keys = []
    for key in await conn.keys("*"):
        size = await conn.memory_usage(key)
        if size > 10000:  # >10KB
            large_keys.append((key, size))

    print(f"Total keys: {key_count}")
    print(f"Large keys (>10KB): {len(large_keys)}")
```

### Milvus Collection Stats

```python
def get_milvus_stats(collection_name: str):
    from pymilvus import utility

    # Collection info
    info = utility.get_collection_stats(collection_name)
    print(f"Rows: {info['row_count']}")

    # Index info
    indexes = utility.list_indexes(collection_name)
    for idx in indexes:
        print(f"Index: {idx.index_name}")
        print(f"  Type: {idx.index_type}")
        print(f"  Params: {idx.params}")
```

---

## Troubleshooting

### Common Issues and Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| MongoDB connection pool exhausted | "Connection pool closed" | Increase maxPoolSize or check for connection leaks |
| Milvus collection not found | "collection doesn't exist" | Check if collection needs loading: `load_collection()` |
| Redis out of memory | "OOM command not allowed" | Configure maxmemory-policy: `allkeys-lru` |
| MinIO presigned URL expires | 403 Forbidden | Check MINIO_PUBLIC_URL setting, ensure URL is accessible |
| Chatflow queries slow | >500ms response | Fix index: change "workflow" to "workflow_id" |
| Temp KBs accumulate | Storage growth | Run cleanup job for orphaned temp KBs |

---

## Monitoring Queries

```python
# System health check
async def health_check():
    status = {
        "mongodb": False,
        "milvus": False,
        "redis": False,
        "minio": False
    }

    try:
        await mongodb.db.command("ping")
        status["mongodb"] = True
    except Exception as e:
        status["mongodb_error"] = str(e)

    try:
        milvus_client.client.list_collections()
        status["milvus"] = True
    except Exception as e:
        status["milvus_error"] = str(e)

    try:
        conn = await redis.get_redis_connection()
        await conn.ping()
        status["redis"] = True
    except Exception as e:
        status["redis_error"] = str(e)

    try:
        await async_minio_manager.validate_file_existence("health_check")
        status["minio"] = True
    except Exception as e:
        status["minio_error"] = str(e)

    return status
```

---

**Generated**: 2026-01-28
**Version**: 1.0

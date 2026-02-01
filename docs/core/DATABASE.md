# LAYRA Database Schema Documentation

**Version**: 2.0.0  
**Last Updated**: 2026-01-23  

---

## Overview

LAYRA uses **6 databases** optimized for different data access patterns:

| Database | Type | Purpose | Technology |
|----------|------|---------|-----------|
| **MySQL** | Relational | User accounts, authentication | SQLAlchemy + asyncmy |
| **MongoDB** | Document | Conversations, knowledge bases | Motor (async) |
| **Milvus** | Vector | Embeddings for semantic search | pymilvus |
| **Redis** | Cache/KV | Sessions, task progress | redis-py async |
| **MinIO** | Object Storage | Files, documents, images | aioboto3 |

---

## MySQL Database

**Purpose**: User authentication and account management  
**Connection**: `mysql+asyncmy://user:pass@host:3306/layra_db`  
**Connection Pool**: 10 base, 20 max overflow  

### Users Table

```sql
CREATE TABLE users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE,
  hashed_password VARCHAR(255) NOT NULL,
  password_migration_required BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  INDEX idx_username (username),
  INDEX idx_email (email)
);
```

**Fields**:
- `id`: Auto-increment primary key
- `username`: Unique username (3-50 chars)
- `email`: Optional unique email
- `hashed_password`: bcrypt hashed (salted)
- `password_migration_required`: Legacy password migration flag (DEADLINE: 2026-02-23)
- `created_at`: Account creation timestamp
- `updated_at`: Last modification timestamp
- `is_active`: Account status

**Indexes**: 
- Primary: `id`
- Unique: `username`, `email`
- Search: `username`, `email`

**Example Query**:
```python
# Get user by username
user = await db.execute(
    select(User).where(User.username == "john_doe")
)

# Create user
new_user = User(
    username="jane_doe",
    email="jane@example.com",
    hashed_password=get_password_hash("secure_pass"),
    password_migration_required=False
)
await db.add(new_user)
await db.commit()
```

---

## MongoDB Database

**Purpose**: Document storage for conversations, knowledge bases, files  
**Connection**: `mongodb://user:pass@host:27017`  
**Default DB**: `chat_mongodb`  

### Collections

#### conversations

Stores conversation threads with turn-by-turn messages.

```javascript
{
  "_id": ObjectId("..."),
  "conversation_id": "conv_user123_abc123",
  "username": "user123",
  "conversation_name": "Project Q Discussion",
  "model_config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "turns": [
    {
      "message_id": "msg_1",
      "parent_message_id": null,
      "sender_role": "user",
      "message": "What is the project scope?",
      "files": ["file_1", "file_2"],
      "knowledge_db_ids": ["kdb_123"],
      "created_time": ISODate("2026-01-20T10:00:00Z")
    },
    {
      "message_id": "msg_2",
      "parent_message_id": "msg_1",
      "sender_role": "assistant",
      "message": "Based on the documents provided...",
      "sources": [
        {
          "file_id": "file_1",
          "page": 5,
          "snippet": "..."
        }
      ],
      "created_time": ISODate("2026-01-20T10:01:00Z")
    }
  ],
  "created_at": ISODate("2026-01-20T10:00:00Z"),
  "last_modify_at": ISODate("2026-01-23T15:30:00Z")
}
```

**Fields**:
- `conversation_id`: Unique conversation identifier
- `username`: Owner of conversation
- `conversation_name`: User-friendly name
- `model_config`: LLM configuration for this conversation
- `turns`: Array of messages (user + assistant alternating)
- `created_at`: Conversation start time
- `last_modify_at`: Last message timestamp

**Indexes**:
```javascript
db.conversations.createIndex({ "username": 1, "conversation_id": 1 })
db.conversations.createIndex({ "created_at": -1 })
```

---

#### knowledge_bases

Stores document collections for each conversation/knowledge base.

```javascript
{
  "_id": ObjectId("..."),
  "knowledge_base_id": "kdb_user123_abc",
  "username": "user123",
  "knowledge_base_name": "Project Documentation",
  "description": "All project-related documents",
  "is_delete": false,
  "created_at": ISODate("2026-01-20T10:00:00Z"),
  "updated_at": ISODate("2026-01-23T15:30:00Z"),
  "files": [
    {
      "file_id": "file_1",
      "filename": "project_scope.pdf",
      "size": 1024576,
      "pages": 25,
      "created_at": ISODate("2026-01-20T10:05:00Z"),
      "status": "processed"
    }
  ],
  "metadata": {
    "total_files": 5,
    "total_pages": 120,
    "total_size_bytes": 5242880
  }
}
```

**Fields**:
- `knowledge_base_id`: Unique KB identifier
- `username`: Owner
- `knowledge_base_name`: Display name
- `is_delete`: Soft delete flag
- `files`: Array of file metadata
- `metadata`: Aggregate statistics

---

#### files

Individual file records with metadata.

```javascript
{
  "_id": ObjectId("..."),
  "file_id": "file_1",
  "knowledge_base_id": "kdb_user123_abc",
  "username": "user123",
  "original_filename": "project_scope.pdf",
  "minio_filename": "user123/kdb_abc/file_1.pdf",
  "file_type": "application/pdf",
  "size": 1024576,
  "pages": 25,
  "status": "processed",
  "created_at": ISODate("2026-01-20T10:05:00Z"),
  "processed_at": ISODate("2026-01-20T10:12:00Z"),
  "error_message": null
}
```

---

#### images

Processed images from PDFs/documents.

```javascript
{
  "_id": ObjectId("..."),
  "image_id": "img_file1_001",
  "file_id": "file_1",
  "page_number": 1,
  "minio_url": "http://minio:9000/bucket/user123/img_file1_001.png",
  "image_type": "page_image",
  "width": 1024,
  "height": 1536,
  "created_at": ISODate("2026-01-20T10:06:00Z")
}
```

---

## Milvus Vector Database

**Purpose**: Semantic search using ColBERT embeddings  
**Connection**: `http://milvus:19530`  
**Vector Dimension**: 128  

### Collection Schema

Each knowledge base has a collection: `colqwen_temp_{knowledge_db_id}`

```python
fields = [
    FieldSchema(
        name="pk",
        dtype=DataType.INT64,
        is_primary=True,
        auto_id=True
    ),
    FieldSchema(
        name="vector",
        dtype=DataType.FLOAT_VECTOR,
        dim=128  # ColBERT embedding dimension
    ),
    FieldSchema(
        name="image_id",
        dtype=DataType.VARCHAR,
        max_length=255
    ),
    FieldSchema(
        name="page_number",
        dtype=DataType.INT64
    ),
    FieldSchema(
        name="file_id",
        dtype=DataType.VARCHAR,
        max_length=255
    ),
    FieldSchema(
        name="chunk_index",
        dtype=DataType.INT64
    )
]

# Index configuration
index_params = {
    "index_type": "HNSW",
    "metric_type": "IP",  # Inner Product for ColBERT
    "params": {
        "M": 32,              # Max connections per node
        "efConstruction": 500 # Search width during construction
    }
}
```

**Fields**:
- `pk`: Auto-increment primary key
- `vector`: ColBERT embedding (128 dims)
- `image_id`: Reference to source image
- `page_number`: Source page
- `file_id`: Source file
- `chunk_index`: Chunk sequence

**Index**: HNSW (Hierarchical Navigable Small World)
- Metric: Inner Product (IP) for ColBERT
- M=32: Degree of connectivity
- efConstruction=500: Construction parameter

**Example Insert**:
```python
# Insert vectors
vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
data = {
    "vector": vectors,
    "image_id": ["img_1", "img_2"],
    "page_number": [1, 2],
    "file_id": ["file_1", "file_1"]
}
collection.insert(data)

# Search
results = collection.search(
    data=[query_vector],
    anns_field="vector",
    param={"metric_type": "IP", "params": {"ef": 64}},
    limit=10,
    output_fields=["image_id", "page_number"]
)
```

---

## Redis Database

**Purpose**: Session management, task progress, caching  
**Connection**: `redis://host:6379`  
**Password**: Configured in `.env`  

### Database Structure

Redis uses 3 logical databases (DB 0-2):

#### DB 0: Tokens
Stores JWT tokens for session management.

```
KEY: token:{jwt_token}
VALUE: {username}
TTL: 11520 minutes (8 days)

Example:
token:eyJhbGciOiJIUzI1NiIs... → "john_doe"
```

#### DB 1: Task Progress
Tracks file processing and workflow execution progress.

```
KEY: task:{task_id}
TYPE: Hash
VALUE: {
  "status": "processing|completed|failed",
  "processed": 2,
  "total": 5,
  "message": "Processing document 2 of 5",
  "created_at": 1674172800,
  "updated_at": 1674173900
}
TTL: 3600 seconds (1 hour after completion)

Example:
task:user123_upload_abc → {
  "status": "processing",
  "processed": 2,
  "total": 3,
  "message": "Processed document.pdf (Page 1-50)"
}
```

#### DB 2: Locks
Distributed locks for concurrent operations.

```
KEY: lock:{resource_id}
VALUE: "1"
TTL: 30 seconds (auto-release)

Example:
lock:user123_knowledge_base_abc → 1
```

**Example Code**:
```python
# Store token
redis_conn = await redis.get_token_connection()
await redis_conn.setex(
    f"token:{jwt_token}",
    11520 * 60,  # TTL in seconds
    username
)

# Update task progress
task_conn = await redis.get_task_connection()
await task_conn.hset(
    f"task:{task_id}",
    mapping={
        "status": "processing",
        "processed": 2,
        "total": 5,
        "message": "Processing file 2 of 5..."
    }
)
```

---

## MinIO Object Storage

**Purpose**: File storage for documents, images, generated content  
**Connection**: `http://minio:9000`  
**Bucket**: `minio-file`  

### Directory Structure

```
minio-file/
├── {username}/
│   ├── conversations/
│   │   ├── conv_abc/{file_1.pdf}
│   │   └── conv_def/{file_2.docx}
│   └── temp_uploads/
│       └── {temp_file_123}
├── images/
│   ├── img_file1_001.png
│   ├── img_file1_002.png
│   └── ...
└── exports/
    └── {username}/report_2026_01_23.xlsx
```

**Key Characteristics**:
- Organized by username and conversation
- Images extracted to dedicated folder
- All file URLs are generated via presigned URLs
- Presigned URLs expire after 100 days (default)

**Example Presigned URL**:
```
GET http://minio:9000/minio-file/user123/conversations/conv_abc/file_1.pdf?
  X-Amz-Algorithm=AWS4-HMAC-SHA256&
  X-Amz-Credential=...&
  X-Amz-Date=20260123T163000Z&
  X-Amz-Expires=8640000&
  X-Amz-SignedHeaders=host&
  X-Amz-Signature=...
```

**Example Code**:
```python
from app.db.miniodb import async_minio_manager

# Upload file
await async_minio_manager.upload_file("user123/doc.pdf", upload_file)

# Get presigned URL for download
url = await async_minio_manager.create_presigned_url("user123/doc.pdf")

# Download as base64
base64_data = await async_minio_manager.download_image_and_convert_to_base64(
    "images/img_file1_001.png"
)
```

---

## Data Flow Diagram

```
File Upload
    ↓
MinIO (store file)
    ↓
Kafka (create task)
    ↓
Consumer Process
    ├─ Extract images → MinIO
    ├─ Convert to embeddings (ColBERT)
    ├─ Store vectors → Milvus
    ├─ Update metadata → MongoDB
    └─ Update progress → Redis
    ↓
User Query
    ├─ Search embeddings → Milvus (semantic)
    ├─ Rerank results (MaxSim)
    ├─ Fetch context → MongoDB
    ├─ Query LLM (with context)
    └─ Stream response → Frontend
```

---

## Indexing Strategy

### MongoDB Indexes

```javascript
// conversations
db.conversations.createIndex({ "username": 1, "conversation_id": 1 })
db.conversations.createIndex({ "created_at": -1 })
db.conversations.createIndex({ "conversation_id": 1 })

// knowledge_bases
db.knowledge_bases.createIndex({ "username": 1, "knowledge_base_id": 1 })
db.knowledge_bases.createIndex({ "is_delete": 1 })

// files
db.files.createIndex({ "knowledge_base_id": 1 })
db.files.createIndex({ "file_id": 1 })
```

### Milvus Indexes

- **Type**: HNSW (Hierarchical Navigable Small World)
- **Metric**: IP (Inner Product) - optimized for ColBERT
- **Parameters**:
  - M=32 (max connections)
  - efConstruction=500 (construction width)
  - efSearch=64 (search width)

---

## Migration Strategy

### Adding New Fields

**MySQL Example**:
```bash
# Generate migration
alembic revision --autogenerate -m "Add new_field to users"

# Apply migration
alembic upgrade head
```

**MongoDB Example**:
```python
# Add field with default value
await db.update_many(
    {},
    {"$set": {"new_field": default_value}}
)
```

### Legacy Password Migration

**Timeline**: By 2026-02-23  
**Status**: Currently allowing both legacy (SHA256+salt) and new (bcrypt) passwords

**Automatic Migration**:
- When user logs in with legacy password, auto-upgrade to bcrypt
- Set `password_migration_required = False`
- After deadline, remove legacy support

```python
async def authenticate_user(username: str, password: str):
    user = await db.get(User, username=username)
    
    if user.password_migration_required:
        # Try legacy password verification
        if verify_password_legacy(password, user.hashed_password):
            # Auto-upgrade to bcrypt
            user.hashed_password = get_password_hash(password)
            user.password_migration_required = False
            await db.commit()
            return user
    
    # Try new password verification
    if verify_password(password, user.hashed_password):
        return user
    
    return None
```

---

## Backup Strategy

### MySQL Backups
```bash
# Daily backup
mysqldump -u root -p layra_db > /backups/layra_db_$(date +%Y%m%d).sql

# Restore
mysql -u root -p layra_db < /backups/layra_db_20260123.sql
```

### MongoDB Backups
```bash
# Backup
mongodump --db chat_mongodb --out /backups/mongodb_20260123

# Restore
mongorestore --db chat_mongodb /backups/mongodb_20260123
```

### MinIO Backups
```bash
# Mirror to backup bucket
mc mirror minio/minio-file minio/backup-bucket
```

---

## Performance Tuning

### Query Optimization

**MongoDB Aggregation Pipeline**:
```javascript
db.conversations.aggregate([
  { $match: { "username": "john_doe" } },
  { $sort: { "created_at": -1 } },
  { $limit: 10 },
  { $project: { "turns": 0 } }  // Exclude large field
])
```

**Milvus Search Optimization**:
```python
# Use smaller search width for better performance
results = collection.search(
    data=[query_vector],
    param={"metric_type": "IP", "params": {"ef": 32}},  # Lower ef = faster
    limit=5
)
```

### Connection Pooling

**MySQL**:
- Pool size: 10
- Max overflow: 20
- Pool pre-ping: Enabled (detects stale connections)

**Redis**:
- Connection pooling automatic (redis-py)
- Separated into 3 logical databases for isolation

---

**Related Documentation**:
- [API.md](./API.md) - API endpoints
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration options

# LAYRA Data Inventory - Comprehensive Analysis

Generated: 2026-01-27

---

## Executive Summary

| Data Store | Total Items | Size | Status |
|------------|-------------|------|--------|
| MongoDB | 651 documents | ~MB | Active |
| Redis | 4,792 keys | ~MB | Active |
| MinIO | 20,634 objects | 11.1 GB | Active |
| Milvus | 143,508 vectors | ~GB | Active |

---

## 1. MongoDB (NoSQL Document Store)

### Collections Overview

| Collection | Count | Description |
|-----------|-------|-------------|
| `files` | 487 | File metadata records |
| `conversations` | 19 | Chat conversations |
| `knowledge_bases` | 5 | Knowledge base definitions |
| `model_config` | 9 | User model configurations |
| `workflows` | 2 | Workflow definitions |
| `chatflows` | 0 | Chatflow templates (empty) |
| `nodes` | 0 | Workflow nodes (empty) |
| `users` | ~ | User accounts (SQL) |

---

### 1.1 Conversations Analysis

**Total: 19 conversations across 5 users**

| User | Conversations | Total Turns | Avg Turns | Models Used |
|------|---------------|-------------|-----------|-------------|
| `testuser` | 8 | 9 | 1.1 | GLM, glm-4.7, gpt-4o, deepseek-chat |
| `miko` | 6 | 7 | 1.2 | glm-4.7, deepseek-v3.2 |
| `testuser4287` | 1 | 2 | 2.0 | deepseek-reasoner |
| `testuser4714` | 1 | 1 | 1.0 | deepseek-reasoner |
| `testuser9451` | 1 | 0 | 0.0 | N/A |
| `testuser5894` | 1 | 0 | 0.0 | N/A |

**Key Findings:**
- 12/19 conversations have **zero turns** (created but never used)
- Only 7 conversations have actual chat history
- Most active conversation: `thesis_test_conv_1` with 7 turns
- Models: GLM-4.7 most popular, DeepSeek Reasoner for testing

**Conversation with most turns:**
```
ID: thesis_test_conv_1
User: testuser
Turns: 7
Model: glm-4.7
Created: 2026-01-25 19:03:15
```

---

### 1.2 Knowledge Bases Analysis

**Total: 5 knowledge bases**

| KB ID | Name | User | Files | Status |
|-------|------|------|-------|--------|
| `miko_e6643365-8b03_4bea-a69b-7a1df00ec653` | Thesis Corpus | thesis | 128 | Active |
| `miko_e6643365-8b03-4bea-a69b-7a1df00ec653` | Thesis Corpus (Copy) | miko | 129 | Active |
| `testuser9451_43828f95-8ce8-47c4-9e50-d14a136f3183` | Test KB | testuser9451 | 1 | Active |
| `testuser4714_3d97435c-9771-4153-bc59-79283b7adacb` | Test KB | testuser4714 | 1 | Active |
| `testuser4287_73ace8eb-7aad-47fe-9832-0a034b4863fc` | Test KB | testuser4287 | 1 | Active |

**Note:** Duplicate KB IDs with different separators (underscore vs hyphen) - potential data inconsistency issue.

---

### 1.3 Files Analysis

**Total: 487 file records**

**File distribution by knowledge base:**
| KB | Files |
|----|-------|
| miko thesis KB | 128 files |
| testuser9451 | 1 file |
| testuser4714 | 1 file |
| testuser4287 | 1 file |

**File extensions:**
- `.pdf`: 487 files (100%)

**Note:** All files are PDFs. All owned by `miko` or test users.

---

### 1.4 Model Configurations

**Total: 9 users with model configs**

Configured users:
- `thesis`, `miko`, `testuser`, `testuser4287`, `testuser4714`, `testuser9451`, and 3 others

Each user has:
- Multiple model configurations (GLM-4.7, DeepSeek, GPT-4o, etc.)
- Selected model preference
- API keys and endpoint configurations

---

## 2. Redis Cache

### Cache Key Distribution

| Prefix | Count | Description | TTL |
|--------|-------|-------------|-----|
| `cache:embed` | 4,729 | Image embedding vectors (ColQwen) | ~22 hours |
| `token` | 52 | JWT authentication tokens | Variable |
| `user` | 11 | User session data | ~7.8 days |

### Cache Details

**Embedding Cache (`cache:embed:image:*`)**
- Format: `cache:embed:image:<sha256_hash>`
- Content: Multi-dimensional vectors (ColBERT embeddings)
- Purpose: Avoid recomputing embeddings for already-processed images
- Hit rate: High (4729/4792 = 98.7% of cache is embeddings)

**Authentication Tokens (`token:eyJ...`)**
- JWT tokens for active sessions
- Linked to usernames via separate keys
- Valid users: `thesis`, `miko`, `testuser4287`

**User Sessions (`user:<username>`)**
- Currently active: 11 users
- Stores JWT references

### TTL Statistics
- Average TTL: 19.8 hours
- Min TTL: 8.1 hours
- Max TTL: 7.8 days
- Zero keys without expiry (good for memory management)

---

## 3. MinIO Object Storage

### Bucket Overview

| Bucket | Objects | Size | Purpose |
|--------|---------|------|---------|
| `minio-file` | 20,633 | 11.1 GB | Main storage |
| `layra` | 1 | <1 MB | New/thesis bucket |

### Content Breakdown

**By user prefix:**
| Prefix | Objects | Type |
|--------|---------|------|
| `thesis/` | 1,070 | PDF thesis documents |
| `miko/` | 128 | PDF research papers |
| `testuser4287_` | ~19,400 | Historical page images (PNG) |

**File types:**
- `.png`: 19,206 files (93%) - Document page images
- `.pdf`: 1,427 files (7%) - Source documents

**Total storage:** 11.1 GB

### Key Findings

1. **Historical data:** Most PNGs are from historical document processing (testuser4287)
2. **Recent activity:** thesis/ and miko/ folders show recent uploads
3. **Redundancy:** Many PNG files may be duplicates of the same PDF pages

---

## 4. Milvus Vector Database

### Collections Overview

| Collection | Vectors | Knowledge Base | Status |
|-----------|---------|----------------|--------|
| `colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653` | **137,748** | miko thesis KB | **Active** |
| `colqwentestuser4287_*` | 1,920 | testuser4287 test KB | Active |
| `colqwentestuser9451_*` | 1,920 | testuser9451 test KB | Active |
| `colqwentestuser4714_*` | 1,920 | testuser4714 test KB | Active |

**Total vectors: 143,508**

### Collection Schema
All collections use the same schema:
- `pk`: Primary key (int64)
- `vector`: Embedding vector (float32, dim=128) - ColBERT embeddings
- `image_id`: Image identifier
- `page_number`: Page number in source document
- `file_id`: Source file identifier

### Indexing
- All collections have `vector_index` (HNSW/IVF_FLAT)
- Optimized for similarity search

### Key Findings

1. **Dominant collection:** miko's thesis KB has 137,748 vectors (96% of total)
2. **Test collections:** Each test KB has exactly 1,920 vectors (likely 10 pages × 192 tokens per page)
3. **Empty collections:** None - all collections have data
4. **Vector type:** ColBERT multi-vector embeddings (128-dimensional)

---

## 5. Data Relationships & Orphan Detection

### Consistency Checks

| Check | Status | Details |
|-------|--------|---------|
| KB → Files | ⚠️ Inconsistent | MongoDB has 487 files, KB shows 260 total |
| KB → Milvus | ⚠️ Partial | Only 2 of 5 KBs have corresponding Milvus collections |
| Files → MinIO | ⚠️ Unknown | Need to verify all file_ids exist in MinIO |
| Conversations → KBs | ✅ Consistent | temp_db references valid |

### Orphaned Data Detection

**Potential orphans:**
1. **MinIO PNG files** (19,206) - May not have corresponding vector embeddings
2. **MongoDB file records** without MinIO objects
3. **Milvus vectors** without MongoDB file records

---

## 6. Storage Summary

| Component | Records | Size | Cost |
|-----------|---------|------|------|
| MongoDB docs | 651 | ~50 MB | Low |
| Redis keys | 4,792 | ~500 MB | Medium |
| MinIO objects | 20,634 | 11.1 GB | High |
| Milvus vectors | 143,508 | ~1-2 GB | Medium |

**Total estimated storage: ~12-13 GB**

---

## 7. Recommendations

### Immediate Actions

1. **Clean up empty conversations** - Delete 12/19 conversations with zero turns
2. **Verify file integrity** - Cross-reference MongoDB files with MinIO objects
3. **Standardize KB IDs** - Fix underscore/hyphen inconsistency
4. **Archive historical data** - Move testuser4287's 19K PNGs to cold storage

### Data Quality

1. **Vector completeness** - Verify all PDF pages have corresponding embeddings
2. **Cache warming** - Pre-compute embeddings for frequently accessed files
3. **Orphan cleanup** - Remove orphaned MinIO objects and MongoDB records

### Monitoring

1. **Set up metrics** - Track cache hit rates, query latency, storage growth
2. **Alert on anomalies** - Detect data inconsistencies automatically

---

## Appendix: Data Schema Reference

### MongoDB - files collection
```json
{
  "file_id": "uuid",
  "filename": "document.pdf",
  "username": "miko",
  "minio_filename": "path/to/object",
  "minio_url": "http://minio:9000/bucket/path",
  "knowledge_db_id": "kb_uuid",
  "images": [{"images_id": "uuid", "page_number": 1}],
  "created_at": "2026-01-27T00:00:00",
  "is_delete": false
}
```

### Redis - cache key format
```
cache:embed:image:<sha256_hash> -> [[float]]
token:<jwt_token> -> username
user:<username> -> jwt_token
```

### Milvus - collection schema
```
pk: int64 (primary key)
vector: float32[128] (ColBERT embedding)
image_id: varchar (UUID)
page_number: int32
file_id: varchar (UUID)
```

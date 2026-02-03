# LAYRA SSOT - Clean State

Generated: 2026-01-30 (Consolidated)

## Single Source of Truth (SSOT)

**Knowledge Base:** `miko_e6643365-8b03_4bea-a69b_7a1df00ec653`
**Name:** Thesis Corpus
**Owner:** thesis user
**Status:** Active, Consolidated

---

## Data Inventory (Consolidated 2026-01-30)

| Data Store | Count | Size | Status |
|------------|-------|------|--------|
| MongoDB KBs | 1 active | - | SSOT |
| MongoDB Files | 129 | ~50 MB | SSOT |
| Milvus Vectors | 3,562,057 | ~2-3 GB | SSOT |
| Milvus Collections | 1 | - | Consolidated |
| MinIO PDFs | 129 | ~500 MB | SSOT |
| MinIO Images | 5,733 | ~1.5 GB | SSOT |
| Redis Cache | dynamic | - | Active |
| Conversations | preserved | - | Active |

---

## SSOT Breakdown

### 1. Knowledge Base
```
ID: miko_e6643365-8b03_4bea-a69b_7a1df00ec653
Name: Thesis Corpus
Files: 129 PDF documents
User: thesis
is_delete: false
```

### 2. Files (MongoDB)
```
Collection: files
Count: 129 active files
All associated with SSOT KB
Type: PDF documents
Images per file: ~44 average (5,732 total)
Fields: file_id, filename, minio_url, images[], knowledge_db_id
```

### 3. Vectors (Milvus)
```
Collection: colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653
Vectors: 3,562,057 ColQwen multi-vector embeddings
Dimension: 128
Vectors per image: ~621 average
Index: HNSW (M=48, efConstruction=1024)
Sparse vectors: Present (hybrid search ready)
Schema:
  - pk: int64 (primary key)
  - vector: float32[128] (dense embedding)
  - sparse_vector: sparse (BM25-style)
  - image_id: varchar
  - page_number: int32
  - file_id: varchar
```

### 4. Objects (MinIO)
```
Bucket: minio-file
Path: miko/
PDFs: 129 files
Images: 5,733 PNG files
Total objects: 5,862
```

---

## Consolidation History (2026-01-30)

### Deleted Data

| Category | Deleted | Details |
|----------|---------|---------|
| thesis_fbd KB (MongoDB) | 1 KB doc | Duplicate with schema drift |
| thesis_fbd files (MongoDB) | 396 docs | 3x duplicate ingestion |
| thesis Milvus collection | 4,304,352 vectors | Legacy duplicate |
| empty miko_0ecb collection | 0 vectors | Smoke test artifact |
| MinIO thesis/ prefix | 129 PDFs | Duplicate files |

### Preserved Data

| Category | Count | Reason |
|----------|-------|--------|
| miko KB (MongoDB) | 1 KB + 129 files | Clean metadata |
| miko Milvus collection | 3,562,057 vectors | Better index params |
| Shared images | 5,733 | Referenced by miko KB |

---

## Data Consistency

- Files: 129 in MongoDB = 129 in MinIO
- Images: 5,732 in MongoDB = 5,733 in MinIO (+1 misc)
- Vectors: 3,562,057 = 5,732 images x 621 avg vectors
- Orphans: 0 orphaned records
- Duplicates: 0 duplicate KBs

---

## KB ID Reference

```
MongoDB KB:   miko_e6643365-8b03_4bea-a69b_7a1df00ec653
Milvus:       colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653
MinIO path:   miko/
File count:   129
Image count:  5,732
Vector count: 3,562,057
```

---

## Quick Verification Commands

```bash
# Milvus collections
docker exec layra-backend python3 -c "
from pymilvus import MilvusClient
c = MilvusClient('http://milvus-standalone:19530')
for col in c.list_collections():
    print(f'{col}: {c.get_collection_stats(col)}')"

# MongoDB KBs
docker exec layra-mongodb mongosh 'mongodb://thesis:<mongodb_password>@localhost:27017/chat_mongodb?authSource=admin' --quiet --eval '
db.knowledge_bases.find({}, {knowledge_base_id:1, is_delete:1}).forEach(printjson)'

# MinIO objects
docker exec layra-minio sh -c '
mc alias set m http://localhost:9000 thesis_minio thesis_minio_2d1105118d28bc4eedf9aec29b678e70566dc9e58f43df4e 2>/dev/null
mc ls m/minio-file/ --recursive | wc -l'

# RAG test
curl -s http://localhost:8090/api/v1/health/check
```

---

## Notes

- KB ID uses hyphens (`-`) in MongoDB
- Milvus collection name uses underscores (`_`) replacement
- All data is consistent and cross-referenced
- No orphaned or duplicate data remains
- System ready for production use
- thesis user password: `thesis123` (reset 2026-01-30)

---

**Last Updated:** 2026-01-30
**Status:** Consolidated and Verified

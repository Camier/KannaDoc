# LAYRA SSOT - Clean State

Generated: 2026-01-27

## Single Source of Truth (SSOT)

**Knowledge Base:** `miko_e6643365-8b03_4bea-a69b-7a1df00ec653`
**Name:** Thesis Corpus
**Owner:** thesis user

---

## Data Inventory (Clean)

| Data Store | Count | Size | Status |
|------------|-------|------|--------|
| MongoDB KBs | 1 | - | ✅ SSOT |
| MongoDB Files | 128 | ~50 MB | ✅ SSOT |
| Milvus Vectors | 137,748 | ~1-2 GB | ✅ SSOT |
| MinIO Objects | 128 | ~500 MB | ✅ SSOT |
| Redis Cache | 0 | 0 MB | ✅ Cleared |
| Conversations | 0 | - | ✅ Cleared |

---

## SSOT Breakdown

### 1. Knowledge Base
```
ID: miko_e6643365-8b03_4bea-a69b-7a1df00ec653
Name: Thesis Corpus
Files: 128 PDF documents
User: thesis
```

### 2. Files (MongoDB)
```
Collection: files
Count: 128 active files
All associated with SSOT KB
Type: PDF documents
```

### 3. Vectors (Milvus)
```
Collection: colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653
Vectors: 137,748 ColBERT embeddings
Dimension: 128
Index: HNSW (optimized for search)
```

### 4. Objects (MinIO)
```
Bucket: minio-file
Path: miko/
Objects: 128 PDF files
Size: ~500 MB
```

---

## Deleted Data

| Category | Deleted | Size Recovered |
|----------|---------|----------------|
| Test KBs | 4 KBs | - |
| Test files | 3 file records | - |
| Test Milvus collections | 3 collections | ~5-6K vectors |
| Historical MinIO data | 20,344 objects | ~10.5 GB |
| Empty conversations | 19 conversations | - |
| Active conversations | 9 conversations | - |
| Workflows | 2 workflows | - |
| Redis cache | 4,792 keys | ~500 MB |

**Total storage recovered:** ~11 GB

---

## Data Consistency

✅ **Files:** 128 in MongoDB = 128 in MinIO
✅ **Vectors:** 137,748 vectors for 128 PDFs
✅ **Orphans:** 0 orphaned records
✅ **Duplicates:** 0 duplicate KBs

---

## Milvus Collection Details

```
Collection: colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653

Schema:
  - pk: int64 (primary key)
  - vector: float32[128] (ColBERT embedding)
  - image_id: varchar
  - page_number: int32
  - file_id: varchar

Index: vector_index (HNSW)
Entities: 137,748
```

---

## Redis State

```
Keys: 0
Status: Clean (ready for rebuild)
```

Cache will be rebuilt on next embedding/computation operations.

---

## Next Steps

1. ✅ SSOT is isolated and consistent
2. ✅ All test/historical data removed
3. ✅ Cache cleared for fresh start
4. ⏭️ System ready for production use

---

## KB ID Reference

```
MongoDB KB:   miko_e6643365-8b03_4bea-a69b-7a1df00ec653
Milvus:       colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653
MinIO path:   miko/
File count:   128
Vector count: 137,748
```

---

## Notes

- KB ID uses hyphens (`-`) in MongoDB
- Milvus collection name uses underscores (`_`) replacement
- All data is consistent and cross-referenced
- No orphaned or duplicate data remains

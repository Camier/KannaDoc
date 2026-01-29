# Database Index Analysis and Optimization Guide

## Executive Summary

This document provides a comprehensive analysis of all database indexes, their effectiveness, and actionable optimization recommendations.

**Status**:
- MongoDB: 11 indexes across 7 collections
- Milvus: HNSW index on all vector collections
- MySQL: No indexes (schema not implemented)
- Redis: In-memory hash-based O(1) lookups

---

## MongoDB Index Inventory

### Collection: `knowledge_bases`

```python
# Existing Indexes
Index 1: {knowledge_base_id: 1}
  Type: UNIQUE
  Size: ~10KB
  Query Coverage:
    - db.knowledge_bases.find_one({"knowledge_base_id": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

Index 2: {username: 1, is_delete: 1}
  Type: COMPOUND
  Size: ~15KB
  Query Coverage:
    - db.knowledge_bases.find({"username": "...", "is_delete": False})
  Performance: O(log n) - Good
  Status: KEEP

Index 3: {files.filename: 1}
  Type: SINGLE (on embedded array field)
  Size: ~5KB
  Query Coverage:
    - db.knowledge_bases.aggregate([{$unwind: "$files"}, {$match: {"files.filename": /pattern/}}])
  Performance: O(n) - Inefficient for embedded arrays
  Status: REVIEW - Consider moving files to separate collection

# RECOMMENDED ADDITIONS
Index 4: {last_modify_at: -1}
  Type: SINGLE
  Rationale: Optimize sorting for user KB listings
  Priority: LOW
  Expected Impact: 10-20% improvement on sorted queries

Index 5: {created_at: 1}
  Type: TTL
  Rationale: Auto-cleanup deleted KBs after 90 days
  Priority: MEDIUM
  Implementation:
    db.knowledge_bases.create_index(
        [("created_at", 1)],
        expireAfterSeconds=7776000,
        partialFilterExpression={"is_delete": True}
    )
```

---

### Collection: `files`

```python
# Existing Indexes
Index 1: {file_id: 1}
  Type: UNIQUE
  Size: ~20KB
  Query Coverage:
    - db.files.find_one({"file_id": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

Index 2: {knowledge_db_id: 1}
  Type: SINGLE
  Size: ~15KB
  Query Coverage:
    - db.files.find({"knowledge_db_id": "..."})
  Performance: O(log n) - Good
  Status: KEEP

Index 3: {filename: 1}
  Type: SINGLE
  Size: ~12KB
  Query Coverage:
    - db.files.find({"filename": /pattern/})
  Performance: Partial (regex scans)
  Status: KEEP

# CRITICAL MISSING INDEX
Index 4: {knowledge_db_id: 1, is_delete: 1}
  Type: COMPOUND
  Priority: HIGH
  Rationale: Most KB queries filter by both fields
  Current Behavior: Index-only on knowledge_db_id, then filters is_delete
  Expected Impact: 50-70% improvement on KB file listings
  Implementation:
    await db.files.create_index([("knowledge_db_id", 1), ("is_delete", 1)])

# RECOMMENDED ADDITIONS
Index 5: {username: 1, is_delete: 1}
  Type: COMPOUND
  Priority: MEDIUM
  Rationale: User file listings across all KBs
  Expected Impact: 30-40% improvement
```

---

### Collection: `conversations`

```python
# Existing Indexes
Index 1: {conversation_id: 1}
  Type: UNIQUE
  Size: ~15KB
  Query Coverage:
    - db.conversations.find_one({"conversation_id": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

Index 2: {username: 1, last_modify_at: -1}
  Type: COMPOUND
  Size: ~20KB
  Query Coverage:
    - db.conversations.find({"username": "..."}).sort("last_modify_at", -1)
  Performance: O(log n) - Optimal (covered index)
  Status: KEEP

# RECOMMENDED ADDITIONS
Index 3: {turns.temp_db: 1}
  Type: SPARSE (only indexes documents with temp_db field)
  Priority: LOW
  Rationale: Cleanup queries for orphaned temp KBs
  Current Behavior: Collection scan
  Expected Impact: Significant for large conversation sets
  Implementation:
    await db.conversations.create_index(
        [("turns.temp_db", 1)],
        sparse=True
    )

Index 4: {last_modify_at: 1}
  Type: TTL
  Priority: MEDIUM
  Rationale: Auto-archive old conversations
  Implementation:
    await db.conversations.create_index(
        [("last_modify_at", 1)],
        expireAfterSeconds=7776000  # 90 days
    )
```

---

### Collection: `chatflows` ⚠️ CRITICAL BUG

```python
# Existing Indexes
Index 1: {chatflow_id: 1}
  Type: UNIQUE
  Size: ~10KB
  Query Coverage:
    - db.chatflows.find_one({"chatflow_id": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

Index 2: {workflow: 1, last_modify_at: -1}  ⚠️ BUG!!!
  Type: COMPOUND
  Size: ~15KB
  Query Coverage:
    - NONE (field "workflow" doesn't exist in schema)
  Current Behavior: Index created but never used
  Performance Impact: All workflow-based queries do COLLECTION SCAN
  Priority: CRITICAL
  Fix Required:
    await db.chatflows.drop_index("workflow_chatflows")
    await db.chatflows.create_index([("workflow_id", 1), ("last_modify_at", -1)])
  Expected Impact: 90%+ improvement on workflow listing queries
```

---

### Collection: `workflows`

```python
# Existing Indexes
Index 1: {username: 1, workflow_id: 1}
  Type: UNIQUE (composite)
  Size: ~15KB
  Query Coverage:
    - db.workflows.find_one({"workflow_id": "...", "username": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

Index 2: {username: 1, last_modify_at: -1}
  Type: COMPOUND
  Size: ~18KB
  Query Coverage:
    - db.workflows.find({"username": "..."}).sort("last_modify_at", -1)
  Performance: O(log n) - Optimal
  Status: KEEP

# NO ADDITIONAL INDEXES NEEDED
```

---

### Collection: `model_config`

```python
# Existing Indexes
Index 1: {username: 1}
  Type: UNIQUE
  Size: ~5KB
  Query Coverage:
    - db.model_config.find_one({"username": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

# NO ADDITIONAL INDEXES NEEDED
```

---

### Collection: `nodes`

```python
# Existing Indexes
Index 1: {username: 1}
  Type: UNIQUE
  Size: ~3KB
  Query Coverage:
    - db.nodes.find_one({"username": "..."})
  Performance: O(1) - Optimal
  Status: KEEP

# NO ADDITIONAL INDEXES NEEDED
```

---

## Milvus Index Analysis

### Collection Schema

```
All collections: colqwen{knowledge_base_id}

Fields:
  - pk (INT64, Primary Key, Auto-generated)
  - vector (FLOAT_VECTOR, dim=128)
  - image_id (VARCHAR, max_length=65535)
  - page_number (INT64)
  - file_id (VARCHAR, max_length=65535)
```

### Vector Index Configuration

```python
Index: vector_index
  Type: HNSW (Hierarchical Navigable Small World)
  Metric: IP (Inner Product)
  Parameters:
    M: 32                    # Max connections per node
                             # - Higher: Better recall, more memory
                             # - Recommendation: Keep at 32 for <1M vectors

    efConstruction: 500      # Candidates during index build
                             # - Higher: Better index quality, slower build
                             # - Recommendation: Increase to 1000 for >500K vectors

  Search Parameters:
    ef: 100                  # Candidates during search
                             # - Higher: Better recall, slower search
                             # - Recommendation: Increase to 200 for better precision

Index Size: ~50MB per 100K vectors (128-dim floats)
Memory Usage: ~100MB per 100K vectors (index + data)
```

### Query Performance Analysis

```python
# Search Operation
search(collection, query_vectors, topk=10)

Complexity Breakdown:
  1. HNSW graph traversal: O(log n)
  2. Candidate retrieval: topk * 10 = 100 vectors
  3. MaxSim reranking: O(100 * vectors_per_page)
     - Vectors per page: ~10-50
     - Reranking cost: ~500-2500 dot products
  4. Full vector fetch: Paged, 8192 per batch

Total Time: ~100-500ms (depending on collection size)

Optimization Opportunities:
  1. Reduce search_limit from topk*10 to topk*5
  2. Decrease candidate_images_limit from topk*20 to topk*10
  3. Cache frequently searched pages in Redis
```

### Missing Indexes

```
Scalar Indexes: None
  - image_id: No index (filter expressions scan all vectors)
  - file_id: No index (delete operations scan all vectors)
  - page_number: No index

Recommendation:
  - Add scalar indexes if Milvus version supports it
  - Otherwise, implement application-side caching
```

---

## Redis Key Patterns Analysis

### Key Distribution by Database

```
DB 0 (Tokens):
  Pattern: token:{jwt_token}
  Count: ~1 per active session
  Size: ~200 bytes
  Access Pattern: Write once, read many
  TTL: Token expiration (7 days default)
  Index: Hash-based O(1)

DB 1 (Tasks):
  Pattern: task:{task_id}
  Count: ~1 per background job
  Size: ~500 bytes
  Access Pattern: Frequent writes (progress updates)
  TTL: 3600s (1 hour)
  Index: Hash-based O(1)

DB 3 (Cache):
  Pattern: model_config:{username}
  Count: ~1 per user
  Size: ~2KB
  Hit Rate: Unknown (monitoring needed)
  TTL: 1800s (30 minutes)

  Pattern: user:{username}
  Count: ~1 per user
  Size: ~1KB
  Hit Rate: Unknown (monitoring needed)
  TTL: 3600s (1 hour)

  Pattern: kb:{kb_id}
  Count: ~5 per user
  Size: ~800 bytes
  Hit Rate: Unknown (monitoring needed)
  TTL: 1800s (30 minutes)

  Pattern: search:{query_hash}
  Count: ~10 per user
  Size: ~5KB
  Hit Rate: Likely low (queries are unique)
  TTL: 600s (10 minutes)
  Recommendation: Remove if hit rate < 10%
```

### Redis Memory Optimization

```
Current Estimate: ~77KB per user
  1000 users: ~77MB
  10000 users: ~770MB

Optimization Opportunities:
  1. Implement LRU eviction policy
     maxmemory-policy allkeys-lru

  2. Reduce search result cache TTL
     From: 600s
     To: 60s or remove entirely

  3. Compress large cached values
     Use: redis.set(key, zlib.compress(json.dumps(value)))

  4. Monitor cache hit rates
     Add metrics for cache hits/misses
```

---

## Optimization Priority Matrix

| Priority | Collection/Index | Issue | Impact | Effort | Status |
|----------|-----------------|-------|--------|--------|--------|
| **P0** | chatflows | Index on wrong field | 90% query slow | Low | ⚠️ BUG |
| **P0** | files | Missing compound index | 50% queries slow | Low | TODO |
| **P1** | conversations | Sparse index for cleanup | Maintenance | Low | TODO |
| **P1** | knowledge_bases | Add TTL for cleanup | Storage growth | Low | TODO |
| **P2** | Milvus | Increase efConstruction | Better recall | Medium | TODO |
| **P2** | Redis | Add eviction policy | Memory control | Low | TODO |
| **P3** | files | Add username index | Cross-KB search | Low | TODO |
| **P3** | Redis | Remove search cache | Memory savings | Low | TODO |

---

## Index Implementation Scripts

### Critical Fixes (Run Immediately)

```python
# File: backend/scripts/migrations/fix_indexes.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def fix_critical_indexes():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db]

    print("Applying critical index fixes...")

    # Fix chatflows index
    print("1. Fixing chatflows index...")
    try:
        await db.chatflows.drop_index("workflow_chatflows")
        print("   - Dropped buggy index 'workflow_chatflows'")
    except Exception as e:
        print(f"   - Index not found or error: {e}")

    await db.chatflows.create_index(
        [("workflow_id", 1), ("last_modify_at", -1)],
        name="workflow_chatflows_fixed"
    )
    print("   - Created correct index on (workflow_id, last_modify_at)")

    # Add compound index for files
    print("2. Adding compound index for files...")
    await db.files.create_index(
        [("knowledge_db_id", 1), ("is_delete", 1)],
        name="kb_file_status"
    )
    print("   - Created index on (knowledge_db_id, is_delete)")

    print("Critical fixes applied successfully!")

if __name__ == "__main__":
    asyncio.run(fix_critical_indexes())
```

### Recommended Additions

```python
# File: backend/scripts/migrations/add_recommended_indexes.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def add_recommended_indexes():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db]

    print("Adding recommended indexes...")

    # Sparse index for temp KB cleanup
    await db.conversations.create_index(
        [("turns.temp_db", 1)],
        sparse=True,
        name="temp_kb_cleanup"
    )
    print("1. Added sparse index on turns.temp_db")

    # TTL index for old conversations
    await db.conversations.create_index(
        [("last_modify_at", 1)],
        expireAfterSeconds=7776000,  # 90 days
        name="conv_ttl"
    )
    print("2. Added TTL index for conversations (90 days)")

    # Compound index for user files
    await db.files.create_index(
        [("username", 1), ("is_delete", 1)],
        name="user_files"
    )
    print("3. Added compound index for user files")

    # Sorting index for KBs
    await db.knowledge_bases.create_index(
        [("last_modify_at", -1)],
        name="kb_sort"
    )
    print("4. Added sorting index for KBs")

    print("Recommended indexes added!")

if __name__ == "__main__":
    asyncio.run(add_recommended_indexes())
```

---

## Index Monitoring Query

```python
# File: backend/scripts/monitor_indexes.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def monitor_index_usage():
    """Check index statistics and usage"""
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db]

    collections = ["knowledge_bases", "files", "conversations",
                   "chatflows", "workflows", "model_config", "nodes"]

    for coll_name in collections:
        print(f"\n=== {coll_name} ===")
        coll = db[coll_name]

        # Get index info
        indexes = await coll.index_information()
        for idx_name, idx_info in indexes.items():
            print(f"Index: {idx_name}")
            print(f"  Keys: {idx_info.get('key')}")
            print(f"  Unique: {idx_info.get('unique', False)}")
            print(f"  Sparse: {idx_info.get('sparse', False)}")

        # Get collection stats
        stats = await db.command("collstats", coll_name)
        print(f"\nCollection Stats:")
        print(f"  Document Count: {stats.get('count', 0)}")
        print(f"  Total Index Size: {stats.get('totalIndexSize', 0) / 1024:.2f} KB")
        print(f"  Avg Doc Size: {stats.get('avgObjSize', 0)} bytes")

if __name__ == "__main__":
    asyncio.run(monitor_index_usage())
```

---

## Index Validation Queries

```javascript
// MongoDB Shell - Validate index effectiveness

// 1. Check which indexes are used
db.setProfilingLevel(2)  // Log all operations
// Run queries...
db.system.profile.find().sort({ts: -1}).limit(10)

// 2. Find unused indexes
db.aggregate([
  {$indexStats: {}},
  {$match: {"accesses.ops": {$eq: 0}}}
])

// 3. Check index sizes
db.knowledge_bases.stats().indexSizes

// 4. Explain query plan
db.conversations.find({
  "username": "test_user",
  "is_delete": false
}).sort({"last_modify_at": -1}).explain("executionStats")
```

---

## Performance Benchmarks

### Expected Improvements After Index Fixes

| Query | Before | After | Improvement |
|-------|--------|-------|-------------|
| Get chatflows by workflow | 500ms (full scan) | 5ms (index seek) | **100x** |
| List KB files | 100ms | 30ms | **3.3x** |
| User file listing | N/A | 50ms | **New capability** |
| Temp KB cleanup | 2000ms (scan) | 100ms | **20x** |
| Old conversation cleanup | Manual | Auto | **Automated** |

---

## Summary of Action Items

### Immediate (This Week)
1. Fix chatflows index bug
2. Add compound index on files(knowledge_db_id, is_delete)

### Short-term (This Month)
3. Add sparse index on conversations.turns.temp_db
4. Implement TTL indexes for cleanup
5. Configure Redis eviction policy

### Long-term (This Quarter)
6. Add Milvus scalar indexes (if supported)
7. Implement cache monitoring
8. Benchmark and tune Milvus HNSW parameters
9. Consider sharding strategy for >1M documents

---

**Generated**: 2026-01-28
**Next Review**: After index migrations complete
**Monitoring**: Run monitor_indexes.py weekly for first month

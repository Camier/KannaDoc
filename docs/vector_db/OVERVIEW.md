# Vector Database Configuration & Migration Guide

**Version:** 2.1.0  
**Last Updated:** 2026-01-26  
**Status:** Milvus Active, Qdrant Migration Ready

---

## 📊 Current State

### Active Configuration
- **Vector Database:** `Milvus` (`VECTOR_DB=milvus`)
- **Patch vectors:** 3,561,575 (dense, dim=128) in `colpali_kanna_128`
- **Sparse pages:** 4,691 (page-level sidecar) in `colpali_kanna_128_pages_sparse`
- **KB handle (alias):** `colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1` -> `colpali_kanna_128`
- **Wrapper:** `vector_db_client` routes to `MilvusManager`

**Networking notes:**
- Inside Docker: `MILVUS_URI=http://milvus-standalone:19530`
- From host (debug): `http://127.0.0.1:19531`

### Qdrant Migration Status
- **Code:** Supported (experimental)
- **Deployment:** Not deployed by default (no `qdrant` service in `docker-compose.yml`)
- **Collections:** N/A unless you deploy Qdrant and migrate/ingest embeddings
- **Backup:** Only applies if you deploy Qdrant with a persistent volume

---

## 🔄 Switching Between Vector Databases

### Environment Variable
```bash
# In .env file
VECTOR_DB=milvus    # Use Milvus (current)
VECTOR_DB=qdrant    # Use Qdrant (empty, migration needed)
```

### Quick Switch Commands

```bash
# Switch to Milvus
# Edit .env and set:
#   VECTOR_DB=milvus
./scripts/compose-clean up -d --force-recreate backend

# Switch to Qdrant (fresh deployment, empty unless migrated)
# Edit .env and set:
#   VECTOR_DB=qdrant
./scripts/compose-clean up -d --force-recreate backend
```

### Verification
```bash
# Check active vector database
docker exec layra-backend python3 -c "
import os
print('VECTOR_DB:', os.getenv('VECTOR_DB'))
from app.db.vector_db import vector_db_client
print('Client type:', type(vector_db_client.client).__name__)
"
```

---

## 🏗️ Architecture

### Unified Wrapper System
```
┌─────────────────────────────────────────────────┐
│            Application Code                      │
│  (chat.py, base.py, llm_service.py, etc.)       │
└──────────────────────┬──────────────────────────┘
                       │ vector_db_client
                       ▼
┌─────────────────────────────────────────────────┐
│            VectorDBClientWrapper                 │
│  • Routes to MilvusManager or QdrantManager      │
│  • Based on VECTOR_DB environment variable       │
│  • Same interface for both backends              │
└───────────────┬─────────────────────────────────┘
                │
    ┌───────────┴─────────────┐
    ▼                         ▼
┌─────────┐             ┌─────────┐
│ Milvus  │             │ Qdrant  │
│ Manager │             │ Manager │
└─────────┘             └─────────┘
    │                         │
    ▼                         ▼
┌─────────┐             ┌─────────┐
│ Milvus  │             │ Qdrant  │
│ v2.6.9  │             │ v1.16.2 │
└─────────┘             └─────────┘
```

### Key Files
```
/LAB/@thesis/layra/
├── backend/app/db/
│   ├── vector_db.py          # Unified wrapper factory
│   ├── milvus.py             # Milvus implementation
│   └── qdrant.py             # Qdrant implementation
├── docker-compose.yml        # Both services defined
├── .env                      # VECTOR_DB configuration
└── scripts/snapshot_data.sh  # Backup includes both volumes
```

---

## 📁 Qdrant Implementation Details

### Features
- **Multivector Support:** `dense` (mean-pooled) + `colbert` (token-level) vectors
- **MAX_SIM Comparator:** Native late interaction scoring
- **2-Stage Search:** Dense prefetch (fast) → ColBERT rerank (accurate)
- **Stable Point IDs:** UUIDv5 from `file_id:page_number` for idempotent ingestion
- **Health Monitoring:** `/healthz` endpoint + Prometheus metrics (port 6333)

### Collection Schema
```python
{
    "dense": VectorParams(size=128, distance=COSINE),  # L2-normalized
    "colbert": VectorParams(
        size=128, 
        distance=COSINE,
        multivector_config=MultiVectorConfig(
            comparator=MultiVectorComparator.MAX_SIM
        ),
        hnsw_config=HnswConfigDiff(m=0)  # Disable indexing for multivector
    )
}
```

### Critical Fixes Applied
1. **Embedding Shape Normalization:** `list[1][n_tokens][128]` → `list[n_tokens][128]`
2. **L2 Normalization:** Required for cosine distance with dense vectors
3. **Point ID Format:** Random UUID → deterministic UUIDv5 from file:page
4. **Version Alignment:** Qdrant server v1.16.2, client v1.16.2

---

## 📊 Performance Comparison

| Feature | Milvus | Qdrant |
|---------|--------|--------|
| **Current Usage** | ✅ Active (6.4M embeddings) | ❌ Code complete, not used |
| **Multivector Support** | Custom (MaxSim comparator) | Native (MAX_SIM comparator) |
| **2-Stage Search** | Implemented in application | Native query prefetch |
| **Monitoring** | Basic health checks | Prometheus metrics (port 6333) |
| **Backup** | Volume snapshot | Volume snapshot |
| **Memory Usage** | ~139MB + etcd/minio | ~100-200MB (estimated) |
| **Dependencies** | 3 containers (standalone+etcd+minio) | 1 container |

---

## 🔄 Migration Procedures

### Option 1: Manual Migration (Recommended)
```bash
# 1. Ensure both services are running
cd /LAB/@thesis/layra
docker-compose up -d milvus-standalone qdrant

# 2. Create migration script
cat > /tmp/migrate_milvus_to_qdrant.py << 'EOF'
import asyncio
from pymilvus import connections, Collection
from app.db.qdrant import qdrant_client

# Connect to Milvus
connections.connect(alias='default', host='milvus-standalone', port='19530')

# Query Milvus in batches, transform, insert to Qdrant
# Implementation depends on specific Milvus schema
EOF

# 3. Run migration inside backend container
docker cp /tmp/migrate_milvus_to_qdrant.py layra-backend:/tmp/
docker exec layra-backend python3 /tmp/migrate_milvus_to_qdrant.py
```

### Option 2: Fresh Start with Qdrant
```bash
# 1. Switch to Qdrant (empty)
echo "VECTOR_DB=qdrant" >> .env
docker-compose up -d backend --force-recreate

# 2. Re-ingest documents via API
curl -X POST http://localhost:8090/api/v1/base/upload/{knowledge_db_id} \
  -H "Authorization: Bearer <token>" \
  -F "files=@your_document.pdf"
```

### Option 3: Dual-Mode Operation
- Keep both databases running
- New data goes to Qdrant
- Legacy queries fall back to Milvus
- Requires application-level routing logic

---

## 🚀 First-Time Qdrant Setup

### 1. Enable Qdrant
```bash
cd /LAB/@thesis/layra
echo "VECTOR_DB=qdrant" >> .env
docker-compose up -d qdrant backend --force-recreate
```

### 2. Verify Health
```bash
# Qdrant health
curl -f http://localhost:6333/healthz

# Backend wrapper
docker exec layra-backend python3 -c "
from app.db.vector_db import vector_db_client
print('Client type:', type(vector_db_client.client).__name__)
print('Health check:', vector_db_client.health_check())
"
```

### 3. Create First Collection (via API upload)
```bash
# Upload a test document
curl -X POST http://localhost:8090/api/v1/base/upload/{kb_id} \
  -H "Authorization: Bearer <token>" \
  -F "files=@test.pdf"
```

### 4. Verify Collection Creation
```bash
# Check Qdrant collections
curl -s http://localhost:6333/collections | jq .

# Or via Python
docker exec layra-backend python3 -c "
from app.db.qdrant import qdrant_client
import json
print(json.dumps(qdrant_client.client.get_collections(), indent=2))
"
```

---

## 📈 Monitoring & Operations

### Qdrant Metrics
- **Endpoint:** `http://localhost:6333/metrics`
- **Prometheus Job:** `qdrant` (configured in `monitoring/prometheus.yml`)
- **Key Metrics:**
  - `qdrant_collection_points_count` - Number of vectors
  - `qdrant_memory_usage_bytes` - Memory consumption
  - `qdrant_query_duration_seconds` - Query latency

### Health Checks
```bash
# Qdrant health
curl -f http://localhost:6333/healthz

# Via wrapper
docker exec layra-backend python3 -c "
from app.db.vector_db import vector_db_client
print('Health:', vector_db_client.health_check())
"
```

### Backup Strategy
Both volumes are backed up via `scripts/snapshot_data.sh`:
```bash
# Included volumes
VOLUMES=(
  "layra_minio_data"
  "layra_milvus_data" 
  "layra_milvus_etcd"
  "layra_milvus_minio"
  "layra_qdrant_data"      # Added for Qdrant support
)
```

---

## ⚠️ Known Issues & Limitations

### Qdrant
1. **Version Mismatch:** Previously server v1.12.2, client v1.16.2 - **RESOLVED** (both v1.16.2)
2. **No Production Data:** Collections empty, needs migration or fresh ingestion
3. **Backup Testing:** Restore procedure not yet validated

### Milvus
1. **Complex Deployment:** 3 containers (standalone + etcd + minio)
2. **Limited Monitoring:** Basic health checks only, no detailed metrics
3. **Resource Intensive:** Higher memory footprint than Qdrant

---

## 🔮 Future Recommendations

### Short-term (1-2 weeks)
1. **Test Qdrant Migration:** Migrate small subset of embeddings (100K) to validate
2. **Performance Benchmark:** Compare query latency, memory usage
3. **Backup Validation:** Test Qdrant volume restore procedure

### Medium-term (1 month)
1. **Complete Migration:** Move all 6.4M embeddings to Qdrant
2. **Decommission Milvus:** Remove services from docker-compose.yml
3. **Enhanced Monitoring:** Grafana dashboard for vector DB metrics

### Long-term
1. **Multi-Vector Optimization:** Tune dense vs. colbert vector ratios
2. **Hybrid Search:** Combine semantic + keyword search
3. **Sharding/Replication:** Scale Qdrant for larger datasets

---

## 📞 Support & Troubleshooting

### Common Issues

**Q: Switching to Qdrant but collections are empty**
A: This is expected. Qdrant starts fresh. You need to either:
   - Migrate existing embeddings from Milvus
   - Re-ingest documents via API

**Q: Health check fails for Qdrant**
```bash
# Check container status
docker-compose ps qdrant

# Check logs
docker-compose logs qdrant

# Verify port mapping
netstat -tlnp | grep 6333
```

**Q: Wrapper not switching databases**
```bash
# Force backend rebuild
docker-compose up -d backend --build --force-recreate

# Check environment variable
docker exec layra-backend env | grep VECTOR_DB
```

### Debug Commands
```bash
# List all collections in both databases
docker exec layra-backend python3 -c "
# Milvus
from pymilvus import connections, utility
connections.connect(alias='default', host='milvus-standalone', port='19530')
print('Milvus:', utility.list_collections())

# Qdrant
from app.db.qdrant import qdrant_client
print('Qdrant:', qdrant_client.client.get_collections().collections)
"
```

---

## 📚 Related Documentation

- [`docs/ssot/stack.md`](../ssot/stack.md) - System architecture SSOT
- [`docker-compose.yml`](../../docker-compose.yml) - Service definitions
- [`backend/app/db/vector_db.py`](../../backend/app/db/vector_db.py) - Unified wrapper
- [`backend/app/db/qdrant.py`](../../backend/app/db/qdrant.py) - Qdrant implementation
- [`monitoring/prometheus.yml`](../../monitoring/prometheus.yml) - Metrics configuration
- [`scripts/snapshot_data.sh`](../../scripts/snapshot_data.sh) - Backup script

---

## 🎯 Summary

**Current Recommendation:** Stay with Milvus for production use (6.4M embeddings accessible).  
**Migration Ready:** Qdrant code complete, tested, ready for migration when needed.  
**Switch Simple:** Change `VECTOR_DB` environment variable and restart backend.

**Decision Tree:**
```
Need immediate access to 6.4M embeddings? → Milvus (VECTOR_DB=milvus)
Starting fresh or willing to migrate? → Qdrant (VECTOR_DB=qdrant)
Evaluating both options? → Test with subset migration
```

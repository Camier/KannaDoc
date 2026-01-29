# Qdrant Vector Database - Archived

**Date Archived:** 2026-01-28
**Reason:** Not used - all vector operations use Milvus

## Archived File

| Original Location | Archived Name | Lines | Status |
|-------------------|---------------|-------|--------|
| `backend/app/db/qdrant.py` | `archived_qdrant.py` | 309 | UNUSED |

## Why Was This Archived?

The Qdrant vector database implementation was **NOT USED** in the codebase:

### Evidence

1. **Zero imports**: No files import from `qdrant.py` (verified via grep)
2. **Active vector DB**: All RAG operations use Milvus exclusively
3. **Docker service runs but unused**: Qdrant container starts but has 0 collections
4. **Config default**: `VECTOR_DB=milvus` in all configurations

### Milvus vs Qdrant Usage

| Service | Active? | Collections | Import Count |
|---------|----------|-------------|--------------|
| **Milvus** | ✅ Yes | 1 (93MB data) | 7 imports |
| **Qdrant** | ❌ No | 0 | 0 imports |

### Vector DB Configuration

From `backend/app/core/config.py`:
```python
# VECTOR_DB: str = "milvus"  # Default (Milvus is active)
```

From `docker-compose.yml`:
- `milvus-standalone`: Active, contains `colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653`
- `qdrant`: Container runs but completely unused

## Restoration

If you want to switch from Milvus to Qdrant:

1. **Update configuration**: Set `VECTOR_DB=qdrant` in `.env`
2. **Update imports**: Change 7 import sites from `milvus.py` to `qdrant.py`
3. **Test thoroughly**: Verify vector operations work end-to-end
4. **Migrate data**: Export from Milvus, import to Qdrant
5. **Update documentation**: Update SSOT and architecture docs

## Alternatives

If you want to remove Qdrant entirely:

1. Remove Qdrant service from `docker-compose.yml`
2. Remove `QDRANT_URL` from configuration
3. Remove archived files from git history (if desired)

## References

- See `docs/ssot/stack.md` for vector DB configuration
- See `docs/plans/2026-01-28-codebase-remediation.md` for context

# RAG Test Coverage Matrix

> **Generated**: 2026-02-06
> **Test Files**: 23 files in `backend/tests/`
> **Framework**: pytest + pytest-asyncio + pytest-cov

---

## Coverage Summary

| Category | Files | RAG Relevance |
|----------|-------|---------------|
| RAG-Critical | 6 | Direct RAG/retrieval testing |
| Evaluation | 2 | Metrics and eval endpoints |
| Infrastructure | 8 | DB, repositories, config |
| Security | 2 | Auth, encryption |
| Other | 5 | Workflow, utilities |

---

## Test-to-Code Mapping Matrix

### RAG-Critical Tests

| Test File | Code Paths Covered | Type | Notes |
|-----------|-------------------|------|-------|
| `test_rag_pipeline.py` | `app/rag/`, `app/db/milvus.py` | E2E | Full retrieval pipeline |
| `test_rag.py` | `app/rag/get_embedding.py` | Unit | Embedding generation |
| `test_rag_v2.py` | `app/rag/`, V2 schema | Integration | Updated RAG flow |
| `test_hybrid_search.py` | `app/db/milvus.py:_hybrid_search_with_retry` | Unit | RRF/weighted ranking |
| `test_performance.py` | `app/db/milvus.py` | Benchmark | Latency measurements |
| `test_model_config.py` | `app/core/config.py` | Unit | Model configuration |

### Evaluation Tests

| Test File | Code Paths Covered | Type | Notes |
|-----------|-------------------|------|-------|
| `test_eval_metrics.py` | `app/eval/metrics.py` | Unit | MRR, NDCG, P@K, R@K |
| `test_api/test_eval_endpoints.py` | `app/api/endpoints/eval.py` | Unit | 6 eval API endpoints |

### Infrastructure Tests

| Test File | Code Paths Covered | Type | Notes |
|-----------|-------------------|------|-------|
| `test_repositories_crud.py` | `app/db/repositories/` | Integration | CRUD operations |
| `test_repositories/test_repository_factory.py` | `app/db/repositories/factory.py` | Unit | Repository instantiation |
| `test_db/test_miniodb_presigned_url.py` | `app/db/minio.py` | Integration | File storage URLs |
| `test_db/test_mysql_session_logging.py` | `app/db/mysql.py` | Integration | Session management |
| `test_model_config.py` | `app/db/repositories/model_config.py` | Unit | Direct model config (model_name/model_url/api_key) |
| `test_core_utils.py` | `app/core/utils/` | Unit | Utility functions |
| `test_workflow_engine.py` | `app/workflow/` | Integration | Autonomous workflows |
| `conftest.py` | - | Fixtures | Shared test fixtures |

### Security Tests

| Test File | Code Paths Covered | Type | Notes |
|-----------|-------------------|------|-------|
| `test_security/conftest.py` | `app/core/security/` | Fixtures | Security test setup |
| `test_security/__init__.py` | - | Package | Security test module |

---

## RAG Relevance Classification

### RAG-Critical (Direct impact on retrieval quality)
- `test_rag_pipeline.py` - End-to-end retrieval flow
- `test_rag.py` - Embedding generation
- `test_rag_v2.py` - V2 schema retrieval
- `test_hybrid_search.py` - Hybrid dense+sparse search
- `test_eval_metrics.py` - Evaluation metric calculations
- `test_performance.py` - Latency benchmarks

### Infrastructure (Supports RAG but not core retrieval)
- `test_repositories_crud.py` - Database operations
- `test_db/*` - Storage layer tests
- `test_model_config.py` - LLM model configuration
- `test_workflow_engine.py` - Autonomous workflow execution

### Other (Not RAG-related)
- `test_core_utils.py` - General utilities
- `test_model_config.py` - Configuration validation

---

## Coverage Gaps

| Gap | Priority | Notes |
|-----|----------|-------|
| `app/eval/runner.py` | HIGH | Evaluation orchestration not directly tested |
| `app/eval/labeler.py` | MEDIUM | LLM-based labeling not tested |
| `app/eval/query_generator.py` | MEDIUM | Query generation not tested |
| `app/api/endpoints/knowledge_base.py` | LOW | KB endpoints need tests |
| `app/api/endpoints/chat.py` | LOW | Chat endpoints need tests |

---

## Running Tests

```bash
# All tests
cd backend && PYTHONPATH=. pytest tests/ -v

# RAG-critical only
PYTHONPATH=. pytest tests/test_rag*.py tests/test_hybrid_search.py tests/test_eval_metrics.py -v

# With coverage
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html

# Specific test file
PYTHONPATH=. pytest tests/test_eval_metrics.py -v
```

---

## Test Fixtures

### Shared Fixtures (`conftest.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `mock_milvus` | function | Mocked Milvus client |
| `mock_mongo` | function | Mocked MongoDB connection |
| `sample_chunks` | module | Sample document chunks |

### Repository Fixtures (`test_repositories/fixtures.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `db_session` | function | Test database session |
| `sample_entities` | function | Sample entity data |

---

## Recommendations

1. **Add integration tests** for `app/eval/runner.py` (evaluation orchestration)
2. **Add unit tests** for `app/eval/labeler.py` (LLM relevance labeling)
3. **Increase coverage** of `app/api/endpoints/` (currently only eval endpoints tested)
4. **Add E2E tests** that run against actual Milvus instance (Docker-based)

---

*Generated by Sisyphus | OhMyOpenCode*

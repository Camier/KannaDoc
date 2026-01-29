# Unused Code Inventory & Analysis Report

**Generated:** 2026-01-28
**Project:** layra
**Analysis Scope:** Python (backend) and TypeScript (frontend)

---

## Executive Summary

| Category | Python | TypeScript | Total |
|----------|--------|------------|-------|
| Unused Imports | 221 | - | 221 |
| Unused Functions | 123 | - | 123 |
| Unused Classes | 5 | - | 5 |
| Commented Code | 84 | 5 | 89 |
| TODO/FIXME | 10 | 1 | 11 |
| **TOTAL** | **443** | **6** | **449** |

---

## 1. PYTHON UNUSED IMPORTS (221 items)

### Safe to Delete (High Confidence)

#### Backend Core Files
- `/backend/app/api/endpoints/base.py`
  - Line 3: `Query` - FastAPI import not used
- `/backend/app/api/endpoints/chat.py`
  - Line 3: `File` - FastAPI import not used
- `/backend/app/api/endpoints/workflow.py`
  - Lines 3: `File`, `UploadFile` - File upload imports not used
- `/backend/app/core/embeddings.py`
  - Line 7: `Union` - Type hint not used
- `/backend/app/db/milvus.py`
  - Line 3: `concurrent.futures` - Not used after refactoring

#### Database & Utility Files
- `/backend/app/db/cache.py`
  - Line 6: `logging` - Logger imported but not used
  - Line 7: `Any` - Type hint not used
- `/backend/app/db/ultils.py`
  - Line 1: `ObjectId` - MongoDB import not used
  - Line 2: `logger` - Logger not used
- `/backend/app/utils/unoconverter.py`
  - Line 8: `os` - OS module not used

#### Model Files
- `/backend/app/models/user.py`
  - Line 3: `enum` - Enum not used
  - Line 5: `beijing_time_now` - Utility function not used
- `/backend/app/models/knowledge_base.py`
  - Lines 2: `Any`, `Dict`, `List` - Type hints not used

#### Migration Files (Low Priority)
Multiple env.py files in migrations have unused imports:
- Lines 2, 7, 11: `engine_from_config`, `AsyncEngine`, `User`
- **Risk Level:** LOW (migration files are templates)

### Needs Verification (Medium Confidence)

#### Workflow Components
- `/backend/app/workflow/components/__init__.py`
  - Lines 9: `MAX_CONTEXT_SIZE`, `MAX_CONTEXT_ENTRIES`, `PROVIDER_TIMEOUTS`, `LOOP_LIMITS`, `CHECKPOINT_CONFIG` - Constants exported but may be used dynamically
  - Lines 21-22: `WorkflowCheckpointManager`, `LLMClient` - Classes may be used via __all__

#### Workflow Engine
- `/backend/app/workflow/workflow_engine.py`
  - Line 18: `CircuitBreakerConfig` - May be used in type checking
  - Line 20: `datetime` - May be used in string references
  - Line 23: `LLMClient` - May be used in dynamic loading

---

## 2. UNUSED FUNCTIONS (123 items)

### Safe to Delete (High Confidence)

#### Cache Layer - Completely Unused
**File:** `/backend/app/db/cache.py`
- `get_model_config()` - Line 157 (0 usages)
- `set_model_config()` - Line 162 (0 usages)
- `invalidate_model_config()` - Line 167 (0 usages)
- `get_user_data()` - Line 173 (0 usages)
- `set_user_data()` - Line 178 (0 usages)
- `invalidate_user()` - Line 183 (0 usages)
- `get_workflow_data()` - Line 189 (0 usages)
- `set_workflow_data()` - Line 194 (0 usages)
- `invalidate_workflow()` - Line 199 (0 usages)
- `get_kb_metadata()` - Line 204 (0 usages)
- `set_kb_metadata()` - Line 209 (0 usages)
- `invalidate_kb()` - Line 214 (0 usages)
- `get_session_data()` - Line 220 (0 usages)
- `set_session_data()` - Line 225 (0 usages)
- `invalidate_session()` - Line 230 (0 usages)
- `clear_pattern()` - Line 236 (0 usages)
- **Risk Level:** SAFE - None of these functions are called anywhere in the codebase
- **Recommendation:** Delete entire cache.py file or review if Redis caching is planned

#### Base Repository - Unused Base Class
**File:** `/backend/app/db/repositories/base_repository.py`
- `BaseRepository` class - Line 13 (0 usages)
  - `_find_one()` - Line 25
  - `_find_many()` - Line 47
  - `_insert_one()` - Line 75
  - `_update_one()` - Line 95
  - `_delete_one()` - Line 115
  - `_count()` - Line 135
  - `_exists()` - Line 155
  - `__init__()` - Line 17
- **Risk Level:** SAFE - This was a base class for deleted repositories
- **Recommendation:** DELETE - The repository pattern was removed

#### Circuit Breaker - Unused Circuits
**File:** `/backend/app/core/circuit_breaker.py`
- `vector_db_circuit()` - Line 157 (0 usages)
- `mongodb_circuit()` - Line 168 (0 usages)
- `get_circuit_state()` - Line 185 (0 usages)
- `deepseek_reasoner_circuit()` - Line 210 (0 usages)
- `zhipu_llm_circuit()` - Line 221 (0 usages)
- **Risk Level:** SAFE - Specific circuit implementations not used
- **Recommendation:** Delete unused circuit functions

#### Auth Endpoints - Unused Functions
**File:** `/backend/app/api/endpoints/auth.py`
- `verify_token()` - Line 27 (0 usages)
- `login()` - Line 32 (0 usages)
- `login_with_api_key()` - Line 68 (0 usages)
- `register()` - Line 83 (0 usages)
- `logout()` - Line 143 (0 usages)
- **Risk Level:** NEEDS VERIFICATION - May be used by frontend or tests
- **Recommendation:** Check frontend API calls before deleting

### Needs Verification (Medium Confidence)

#### Chat Endpoints
**File:** `/backend/app/api/endpoints/chat.py`
- `re_name()` - Line 52 (0 usages) - Likely typo of `rename()`
- `upload_multiple_files()` - Line 222 (0 usages)
- `select_bases()` - Line 71 (0 usages)

#### Base Endpoints
**File:** `/backend/app/api/endpoints/base.py`
- `re_name()` - Line 80 (0 usages) - Same typo pattern
- `bulk_delete_files()` - Line 99 (0 usages)

---

## 3. UNUSED CLASSES (5 items)

### Deleted Repository Classes (Referenced in Tests)

The following repository classes were deleted but are still referenced in test files:

1. **ChatflowRepository** - Referenced in:
   - `backend/tests/test_repositories/test_repository_factory.py` (3 occurrences)

2. **ConversationRepository** - Referenced in:
   - `backend/tests/test_repositories.py` (1 occurrence)
   - `backend/tests/test_repositories/fixtures.py` (6 occurrences)
   - `backend/tests/test_repositories/test_repository_factory.py` (5 occurrences)

3. **FileRepository** - Referenced in:
   - `backend/tests/test_repositories.py` (1 occurrence)
   - `backend/tests/test_repositories/fixtures.py` (4 occurrences)
   - `backend/tests/test_repositories/test_repository_factory.py` (3 occurrences)

4. **KnowledgeBaseRepository** - Referenced in:
   - `backend/tests/test_repositories.py` (1 occurrence)
   - `backend/tests/test_performance.py` (3 occurrences)
   - `backend/tests/test_repositories/fixtures.py` (4 occurrences)
   - `backend/tests/test_repositories/test_repository_factory.py` (5 occurrences)

5. **ModelConfigRepository** - Referenced in:
   - `backend/tests/test_repositories/test_repository_factory.py` (3 occurrences)

6. **NodeRepository** - Referenced in:
   - `backend/tests/test_repositories/test_repository_factory.py` (3 occurrences)

7. **WorkflowRepository** - Referenced in:
   - `backend/tests/test_repositories/test_repository_factory.py` (3 occurrences)

**Risk Level:** NEEDS VERIFICATION
**Recommendation:** 
- Update test files to remove references
- OR verify if repository pattern should be restored

---

## 4. COMMENTED CODE (84 Python + 5 TypeScript)

### Python Commented Code (84 items)

#### Migration Templates (Low Priority)
Multiple `env.py` files in migrations have commented template code:
```python
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# my_important_option = config.get_main_option("my_important_option")
```
**Risk Level:** KEEP (Alembic template comments)
**Recommendation:** Leave as-is (template documentation)

#### Model Server
**File:** `/model-server/colbert_service.py`
- Lines 76-79: Commented torch.compile code
```python
#     print("🚀 Compiling model with torch.compile (mode='reduce-overhead')...")
#     self.model = torch.compile(self.model, mode='reduce-overhead')
# except Exception as e:
#     print(f"⚠️ Torch compile failed: {e}")
```
**Risk Level:** KEEP (Performance optimization kept for reference)
**Recommendation:** Leave comment with explanation

#### Download Scripts
**File:** `/scripts/archive/download_models.py`
- Lines 63-66: Commented Docker volume copy code
**Risk Level:** DELETE (Outdated deployment pattern)
**Recommendation:** Remove commented code

### TypeScript Commented Code (5 items)

#### Frontend Commented Code
1. **`/frontend/src/app/[locale]/ai-chat/page.tsx`**
   - Line 357: Hardcoded IP address fetch
   ```typescript
   //const response = await fetch("http://192.168.1.5:8000/api/v1/sse/chat", {
   ```
   **Risk Level:** DELETE (Development artifact)
   **Recommendation:** Remove hardcoded IP

2. **`/frontend/src/components/AiChat/LeftSidebar.tsx`**
   - Line 102: Commented rename function
   ```typescript
   //renameChat(chat.conversationId, inputValues[index]);
   ```
   **Risk Level:** DELETE (Incomplete feature)
   **Recommendation:** Remove or implement

3. **`/frontend/src/middlewares/withAuth.tsx`**
   - Line 30: Commented user setting
   ```typescript
   //setUser({ name: data.user.username, email: data.user.email });
   ```
   **Risk Level:** NEEDS VERIFICATION
   **Recommendation:** Verify if user context is needed

4. **`/frontend/src/stores/flowStore.ts`**
   - Lines 254-255: Commented MCP cleanup
   ```typescript
   // if (newTools.length === 0) {
   //   delete updatedMcpUse[name];
   ```
   **Risk Level:** KEEP (Logic kept for reference)
   **Recommendation:** Add explanatory comment

5. **`/frontend/src/utils/imageLoader.ts`**
   - Line 25: Commented decode
   ```typescript
   // internalUrl = decodeURIComponent(internalUrl);
   ```
   **Risk Level:** DELETE (Dead code)
   **Recommendation:** Remove

---

## 5. TODO/FIXME COMMENTS (10 Python + 1 TypeScript)

### Python TODOs (10 items)

1. **`/backend/app/api/endpoints/chat.py`** - Line 197
   ```python
   # NOTE: MongoDB API is delete_conversations_by_user (delete_all_conversation does not exist)
   ```
   **Type:** Documentation Note
   **Risk:** Keep as documentation

2. **`/backend/app/db/mongo.py`** - Line 15
   ```python
   # TODO: This file is 1,566 lines and needs to be split into repositories.
   ```
   **Type:** Technical Debt
   **Priority:** HIGH (Large file needs refactoring)
   **Recommendation:** Create refactoring task

3. **`/backend/app/rag/provider_client.py`** - Line 22
   ```python
   # Note: gpt-4o-mini deprecates Feb 27, 2026 - use gpt-4o instead
   ```
   **Type:** Deprecation Notice
   **Priority:** MEDIUM (Future action needed)
   **Recommendation:** Create calendar reminder for Feb 2026

4. **`/backend/app/workflow/components/__init__.py`** - Line 17
   ```python
   # NOTE: QualityAssessmentEngine was archived to scripts/archive/quality_assessment/
   ```
   **Type:** Documentation
   **Risk:** Keep as reference

5. **`/backend/scripts/legacy_backfill_minio_images.py`** - Line 109
   ```python
   # NOTE: python list repr includes quotes => valid Milvus filter
   ```
   **Type:** Documentation
   **Risk:** Keep as explanation

6. **`/backend/find_orphan_host.py`** - Line 9
   ```python
   # Note: Connecting to container IP since port not exposed
   ```
   **Type:** Documentation
   **Risk:** Keep as infrastructure note

7. **`/backend/remediate_pdf.py`** - Line 36
   ```python
   # Note: Filename might be in a sub-field or just 'filename'
   ```
   **Type:** Documentation
   **Risk:** Keep as data structure note

8. **`/backend/scripts/check_new_schema.py`** - Line 64
   ```python
   # Note: Milvus 2.4+ allows multiple vector fields in one collection
   ```
   **Type:** Documentation
   **Risk:** Keep as version note

9. **`/backend/scripts/archive/reingest_optimized.py`** - Line 23
   ```python
   # Note: OAuth2PasswordRequestForm expects data, not json
   ```
   **Type:** Documentation
   **Risk:** Keep as API note

10. **`/scripts/validate_env.py`** - Line 22
    ```python
    # Note: These are conservative patterns to avoid false positives
    ```
    **Type:** Documentation
    **Risk:** Keep as validation note

### TypeScript TODOs (1 item)

1. **`/frontend/next-env.d.ts`** - Line 4
   ```typescript
   // NOTE: This file should not be edited
   ```
   **Type:** Auto-generated warning
   **Risk:** Keep (Next.js auto-generated file)

---

## 6. DELETION RECOMMENDATIONS BY RISK LEVEL

### SAFE TO DELETE (No Risk)

1. **Entire file:** `/backend/app/db/cache.py`
   - 16 unused functions
   - Zero usages across codebase
   - Redis caching not implemented
   - **Savings:** ~236 lines

2. **Base repository:** `/backend/app/db/repositories/base_repository.py`
   - Unused base class + 8 methods
   - Repository pattern removed
   - **Savings:** ~180 lines

3. **Circuit breaker functions:** `/backend/app/core/circuit_breaker.py`
   - 5 unused circuit functions
   - **Savings:** ~80 lines

4. **Type hint imports:** Multiple files
   - 221 unused import statements
   - **Savings:** ~221 lines

5. **Commented code:**
   - Frontend hardcoded IP (1 line)
   - Frontend unused functions (3 lines)
   - Python download script comments (4 lines)
   - **Total savings:** ~8 lines

### NEEDS VERIFICATION (Medium Risk)

1. **Auth endpoint functions** - `/backend/app/api/endpoints/auth.py`
   - 5 potentially unused functions
   - May be called by frontend
   - **Action:** Search frontend for API calls

2. **Chat endpoint functions** - `/backend/app/api/endpoints/chat.py`
   - 3 potentially unused functions including `re_name()` typo
   - **Action:** Verify before deletion

3. **MongoDB TODO** - Refactor 1,566-line file
   - **Action:** Create refactoring plan

4. **Deleted repository references** - Update test files
   - 7 repository classes referenced in tests
   - **Action:** Update tests OR restore repositories

### KEEP (Used/Important)

1. **Migration template comments** - Alembic boilerplate
2. **Model server torch.compile comments** - Performance reference
3. **Documentation notes** - All TODO/NOTE comments explaining behavior
4. **Deprecation notice** - gpt-4o-mini (Feb 2026)

---

## 7. IMPACT METRICS

### Potential Code Reduction

| Category | Items | Lines | Risk |
|----------|-------|-------|------|
| Unused Imports | 221 | ~221 | Safe |
| Unused Functions | 123 | ~1,500 | Mixed |
| Unused Classes | 7 | ~350 | Verify |
| Commented Code | 89 | ~100 | Safe |
| **TOTAL POTENTIAL** | **440** | **~2,171** | - |

### Breakdown by Safety

- **Safe to delete:** ~550 lines (unused imports + dead code)
- **Needs verification:** ~1,500 lines (unused functions/classes)
- **Keep for reference:** ~121 lines (TODOs + documentation)

---

## 8. CLEANUP ACTION PLAN

### Phase 1: Safe Deletions (Immediate)
```bash
# Remove unused imports (automated)
autoflake --remove-all-unused-imports --recursive backend/app

# Delete cache.py (completely unused)
rm backend/app/db/cache.py

# Delete base_repository.py (pattern removed)
rm backend/app/db/repositories/base_repository.py

# Remove unused circuit breaker functions
# Edit backend/app/core/circuit_breaker.py manually
```

### Phase 2: Verification Required
```bash
# Search for auth endpoint usage
rg "verify_token|login_with_api_key|/api/v1/auth/login" frontend/src

# Search for chat endpoint usage
rg "re_name|upload_multiple_files|select_bases" frontend/src

# Verify repository references
rg "ChatflowRepository|ConversationRepository" backend/tests
```

### Phase 3: Technical Debt
1. Create task for MongoDB file refactoring (1,566 lines)
2. Add calendar reminder for gpt-4o-mini deprecation (Feb 2026)
3. Review test files for deleted repository references

---

## 9. TESTING STRATEGY

Before deleting any code:

1. **Run test suite:**
   ```bash
   cd backend && python -m pytest tests/ -v
   ```

2. **Check runtime imports:**
   ```bash
   python -c "import app; print('OK')"
   ```

3. **Frontend build:**
   ```bash
   cd frontend && npm run build
   ```

4. **Integration test:**
   - Start services
   - Test API endpoints
   - Verify no import errors

---

## 10. CONCLUSION

**Total Unused Code Detected:** 449 items
**Safe to Delete Immediately:** ~550 lines
**Requires Verification:** ~1,500 lines
**Technical Debt:** 1,566-line MongoDB file

**Recommended Approach:**
1. Start with safe deletions (unused imports, cache.py)
2. Verify endpoint usage before deleting functions
3. Update test files for repository references
4. Plan MongoDB refactoring for next sprint

**Estimated Time Savings:**
- Reduced cognitive load: ~2,000 lines less code to maintain
- Faster imports: ~221 fewer imports to process
- Clearer intent: Remove ambiguity around unused functions

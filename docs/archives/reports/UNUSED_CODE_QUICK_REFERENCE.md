# Unused Code Cleanup - Quick Reference

## Immediate Actions (Safe to Delete)

### 1. Delete Entire Files
```bash
# Completely unused cache layer (16 functions, 0 usages)
rm /LAB/@thesis/layra/backend/app/db/cache.py

# Unused base repository (repository pattern removed)
rm /LAB/@thesis/layra/backend/app/db/repositories/base_repository.py

# Analysis script (temporary)
rm /LAB/@thesis/layra/analyze_unused_code.py
```

### 2. Remove Unused Imports (Manual)

**High Priority - Core Files:**
- `/backend/app/api/endpoints/base.py`: Line 3 - `Query`
- `/backend/app/api/endpoints/chat.py`: Line 3 - `File`
- `/backend/app/api/endpoints/workflow.py`: Lines 3 - `File`, `UploadFile`
- `/backend/app/core/embeddings.py`: Line 7 - `Union`
- `/backend/app/db/milvus.py`: Line 3 - `concurrent.futures`

**Database Files:**
- `/backend/app/db/ultils.py`: Lines 1-2 - `ObjectId`, `logger`
- `/backend/app/utils/unoconverter.py`: Line 8 - `os`

**Model Files:**
- `/backend/app/models/user.py`: Lines 3,5 - `enum`, `beijing_time_now`
- `/backend/app/models/knowledge_base.py`: Line 2 - `Any`, `Dict`, `List`

### 3. Remove Unused Circuit Breaker Functions
**File:** `/backend/app/core/circuit_breaker.py`

Delete these functions:
- `vector_db_circuit()` (line 157)
- `mongodb_circuit()` (line 168)
- `get_circuit_state()` (line 185)
- `deepseek_reasoner_circuit()` (line 210)
- `zhipu_llm_circuit()` (line 221)

### 4. Remove Commented Code

**Frontend:**
- `/frontend/src/app/[locale]/ai-chat/page.tsx`: Line 357 - hardcoded IP
- `/frontend/src/components/AiChat/LeftSidebar.tsx`: Line 102 - unused rename
- `/frontend/src/utils/imageLoader.ts`: Line 25 - dead decode

**Backend:**
- `/scripts/archive/download_models.py`: Lines 63-66 - Docker volume copy

## Verification Required (Medium Risk)

### 1. Auth Endpoints - Check Frontend Usage
**File:** `/backend/app/api/endpoints/auth.py`

Before deleting, search frontend:
```bash
rg "verify_token|login_with_api_key|/api/v1/auth/login" frontend/src
```

Functions to verify:
- `verify_token()` (line 27)
- `login()` (line 32)
- `login_with_api_key()` (line 68)
- `register()` (line 83)
- `logout()` (line 143)

### 2. Chat Endpoints - Typo Functions
**Files:** 
- `/backend/app/api/endpoints/chat.py`
- `/backend/app/api/endpoints/base.py`

Check for `re_name` - likely typo of `rename`:
```bash
rg "re_name|/rename" frontend/src
```

### 3. Deleted Repository References
**Affected Test Files:**
- `backend/tests/test_repositories.py`
- `backend/tests/test_repositories/fixtures.py`
- `backend/tests/test_repositories/test_repository_factory.py`
- `backend/tests/test_performance.py`

**Options:**
1. Update tests to remove repository references
2. Restore repository pattern if needed

## Technical Debt (Low Priority - Keep)

### 1. MongoDB File Refactoring
**File:** `/backend/app/db/mongo.py` (1,566 lines)

TODO: "This file needs to be split into repositories"

**Action:** Create refactoring task for next sprint

### 2. Upcoming Deprecation
**File:** `/backend/app/rag/provider_client.py` (line 22)

Note: "gpt-4o-mini deprecates Feb 27, 2026"

**Action:** Add calendar reminder

## Testing After Cleanup

```bash
# Backend tests
cd /LAB/@thesis/layra/backend && python -m pytest tests/ -v

# Import check
cd /LAB/@thesis/layra/backend && python -c "from app.api.endpoints import base, chat, workflow; print('OK')"

# Frontend build
cd /LAB/@thesis/layra/frontend && npm run build
```

## Statistics Summary

| Action | Items | Lines Saved |
|--------|-------|-------------|
| Delete files | 2 | ~416 |
| Remove imports | 221 | ~221 |
| Remove functions | 21 | ~300 |
| Remove comments | 8 | ~8 |
| **Total** | **252** | **~945** |

## Risk Levels

- **Safe:** Can delete immediately (no references found)
- **Verify:** Check frontend/tests before deleting
- **Keep:** Documentation/technical debt notes

# [ARCHIVED] LAYRA Implementation Checklist

> **⚠️ DEPRECATED**: This checklist corresponds to the v2.0.0 release sprints (Jan 23).
> For current troubleshooting status (Jan 24+), see:
> - [PROJECT_STATE.md](PROJECT_STATE.md) (Current Status)
> - [STABILIZATION_CHECKLIST.md](STABILIZATION_CHECKLIST.md) (Active Tasks)

**Start Date**: 2026-01-23  
**Target Completion**: 2026-02-06 (2 weeks)

---

## 📌 Quick Overview

This checklist helps you implement all fixes from `DISCREPANCIES_FIXES.md` in the correct order.

**Total Items**: 33  
**Time Estimate**: 10-15 hours of development + testing  
**Risk Level**: Low (all fixes are isolated, tested incrementally)

---

## 🔴 WEEK 1: CRITICAL FIXES (High Impact, Low Risk)

### Day 1: Fix the File Download Bug (30 min)

**Objective**: Enable presigned URL generation for file downloads

```bash
# What's broken: Users cannot download files from knowledge base
# Why: server_ip used instead of minio_url (config misuse)
# Impact: File download completely non-functional
# Risk: None (isolated to 1 function)
```

**Steps**:

- [ ] **1.1** Open `backend/app/db/miniodb.py`
  ```bash
  code backend/app/db/miniodb.py
  # Or your editor: vim, nano, etc.
  ```

- [ ] **1.2** Find line 120: `async def create_presigned_url`
  ```bash
  grep -n "def create_presigned_url" backend/app/db/miniodb.py
  # Should show line 120
  ```

- [ ] **1.3** Change line 120 from:
  ```python
  endpoint_url=settings.server_ip,  # ❌ WRONG
  ```
  to:
  ```python
  endpoint_url=settings.minio_url,  # ✅ CORRECT
  ```

- [ ] **1.4** Verify change:
  ```bash
  grep -A 2 "def create_presigned_url" backend/app/db/miniodb.py | head -10
  # Should show: endpoint_url=settings.minio_url
  ```

- [ ] **1.5** Test locally:
  ```bash
  # If local setup available, run:
  pytest backend/tests/test_miniodb.py::test_create_presigned_url -v
  
  # Or manual test:
  cd backend
  python -c "from app.db.miniodb import async_minio_manager; print('Import OK')"
  ```

- [ ] **1.6** Commit:
  ```bash
  git add backend/app/db/miniodb.py
  git commit -m "fix: correct MinIO presigned URL endpoint

- Changed endpoint_url from server_ip to minio_url in create_presigned_url()
- Aligns with 6 other MinIO operations
- Fixes file download functionality"
  ```

**Verification**:
```bash
# Check file can be uploaded and downloaded
curl -X POST http://localhost:8090/api/v1/upload/testuser/conv_123 \
  -F "files=@docs/sample.pdf" \
  -H "Authorization: Bearer $TOKEN"

# Then test download (presigned URL) - should work now
```

---

### Day 2: Fix Database Query Logging (20 min)

**Objective**: Disable SQL query logging in production (performance + security)

```bash
# What's broken: All SQL queries logged to stdout (security risk, slow)
# Why: echo=True hardcoded in SQLAlchemy engine
# Impact: Performance degradation, logs fill with sensitive data
# Risk: None (can revert if issues)
```

**Steps**:

- [ ] **2.1** Open `backend/app/db/mysql_session.py`
  ```bash
  code backend/app/db/mysql_session.py
  ```

- [ ] **2.2** Find line 11: `echo=True`
  ```bash
  grep -n "echo=" backend/app/db/mysql_session.py
  # Should show line 11
  ```

- [ ] **2.3** Change from:
  ```python
  engine = create_async_engine(
      settings.db_url,
      echo=True,  # ❌ LOGS ALL QUERIES
      ...
  )
  ```
  to:
  ```python
  engine = create_async_engine(
      settings.db_url,
      echo=settings.debug_mode,  # ✅ CONDITIONAL
      ...
  )
  ```

- [ ] **2.4** Verify `.env` has correct `DEBUG_MODE`:
  ```bash
  grep "DEBUG_MODE" .env
  # Should be: DEBUG_MODE=false (production)
  # or: DEBUG_MODE=true (development)
  ```

- [ ] **2.5** Test:
  ```bash
  cd backend
  python -c "
  from app.db.mysql_session import mysql
  from app.core.config import settings
  print(f'Debug mode: {settings.debug_mode}')
  print(f'Echo will be: {settings.debug_mode}')
  "
  ```

- [ ] **2.6** Restart backend service:
  ```bash
  # If using Docker:
  docker-compose restart layra-backend
  
  # Or manual:
  pkill -f "gunicorn.*app.main:app"
  cd backend && gunicorn -c gunicorn_config.py app.main:app
  ```

- [ ] **2.7** Verify no SQL logging:
  ```bash
  # Make an API call
  curl -X GET http://localhost:8090/api/v1/chat/conversations/user_1 \
    -H "Authorization: Bearer $TOKEN"
  
  # Check logs - should NOT contain SELECT statements
  docker logs layra-backend 2>&1 | grep -i "SELECT\|INSERT"
  # Should return empty (no SQL logging)
  ```

- [ ] **2.8** Commit:
  ```bash
  git add backend/app/db/mysql_session.py
  git commit -m "fix: disable SQLAlchemy echo in production

- Changed echo=True to echo=settings.debug_mode
- SQL queries only logged in DEBUG mode
- Improves performance and security"
  ```

---

### Day 3: Start Legacy Password Migration (1 hour)

**Objective**: Audit and plan password migration completion

```bash
# What needs fixing: Legacy password salt still in code (security debt)
# Why: Old migration hasn't completed
# Impact: Code review concerns, security audit flags
# Risk: Low (audit only)
```

**Phase 1: Audit** (15 min)

- [ ] **3.1** Check if any users still have legacy passwords:
  ```bash
  # Login to MySQL
  docker-compose exec mysql mysql -u root -p$MYSQL_ROOT_PASSWORD -D $MYSQL_DATABASE
  
  # Or use direct command:
  docker-compose exec mysql mysql -u root -proot_password \
    -e "SELECT COUNT(*) as legacy_users FROM users WHERE password_migration_required = TRUE;"
  
  # Result interpretation:
  # - 0 rows: All users migrated ✅
  # - >0 rows: Need to migrate those users ⚠️
  ```

- [ ] **3.2** Record results:
  ```bash
  # Save to MIGRATION_STATUS.txt
  echo "Legacy password audit - 2026-01-23" > MIGRATION_STATUS.txt
  echo "Users requiring migration: X" >> MIGRATION_STATUS.txt
  ```

- [ ] **3.3** Add deadline comment to code:
  ```bash
  # Edit: backend/app/core/security.py, line 9
  # Change:
  # TODO: Remove verify_password_legacy() after migration complete.
  # 
  # To:
  # TODO: Remove verify_password_legacy() after migration complete (Deadline: 2026-02-23)
  ```

- [ ] **3.4** Document decision:
  ```bash
  cat >> DISCREPANCIES_FIXES.md << 'EOF'

## Migration Status (2026-01-23)

Audit Result: [INSERT RESULT HERE - e.g., "0 legacy users found"]

Decision: [Choose one]
- ✅ All migrated, can remove code now
- ⏳ Implement force password reset on next login
- 🔒 Keep for gradual migration (deadline: 2026-02-23)
EOF
  ```

**Phase 2: Plan** (30 min)

- [ ] **3.5** If legacy users exist, create force-reset endpoint:
  ```python
  # In backend/app/api/endpoints/auth.py, add:
  
  @router.post("/force-reset-password")
  async def force_password_reset(
      current_user: User = Depends(get_current_user),
      db: AsyncSession = Depends(get_mysql_session)
  ):
      """User must reset password on next login"""
      user = await db.get(User, current_user.id)
      user.password_migration_required = True
      await db.commit()
      return {"message": "Please reset your password on next login"}
  ```

- [ ] **3.6** Create database migration script:
  ```bash
  cd backend
  alembic revision -m "Mark users for password migration"
  
  # Edit the generated file in migrations/versions/
  # Add to upgrade():
  op.execute("UPDATE users SET password_migration_required = TRUE")
  ```

- [ ] **3.7** Commit Phase 1:
  ```bash
  git add MIGRATION_STATUS.txt backend/app/core/security.py
  git commit -m "chore: phase 1 of legacy password migration

- Audit complete: X users require migration
- Set deadline: 2026-02-23
- Prepare for Phase 2: force password reset endpoint"
  ```

**Phase 3: Removal** (scheduled for 2026-02-23)
- [ ] **3.8** Set calendar reminder: "2026-02-23 - Remove legacy password code"

---

## 🟡 WEEK 2: CODE QUALITY (Medium Priority)

### Day 4: Clean Up Imports & Dependencies (30 min)

**Objective**: Remove unused code and dependencies

**Step A: Remove unused import** (10 min)

- [ ] **4A.1** Open `backend/app/core/security.py`
  ```bash
  code backend/app/core/security.py
  ```

- [ ] **4A.2** Find line 19 (unused APIKeyHeader):
  ```bash
  grep -n "from fastapi.security import" backend/app/core/security.py
  ```

- [ ] **4A.3** Remove `, APIKeyHeader`:
  ```python
  # From:
  from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
  
  # To:
  from fastapi.security import OAuth2PasswordBearer
  ```

- [ ] **4A.4** Verify no usage:
  ```bash
  grep -r "APIKeyHeader" backend/
  # Should return empty
  ```

- [ ] **4A.5** Commit:
  ```bash
  git add backend/app/core/security.py
  git commit -m "chore: remove unused APIKeyHeader import"
  ```

**Step B: Evaluate databases[mysql] dependency** (20 min)

- [ ] **4B.1** Check if it's used:
  ```bash
  grep -r "from databases import\|import databases" backend/
  grep -r "Database(" backend/
  # Both should return empty
  ```

- [ ] **4B.2** Decision: Keep or Remove?
  ```bash
  # Option 1: Remove (recommended)
  # Rationale: SQLAlchemy + asyncmy handles all use cases
  
  # Option 2: Keep
  # Rationale: Might use in future, low overhead
  ```

- [ ] **4B.3** If removing, edit `backend/requirements.txt`:
  ```bash
  # Remove line: databases[mysql]==0.9.0
  # Keep: sqlalchemy[asyncio]==2.0.39
  ```

- [ ] **4B.4** If removing, test:
  ```bash
  cd backend
  pip install -r requirements.txt
  pytest tests/ -v --tb=short
  # Should all pass
  ```

- [ ] **4B.5** Commit decision:
  ```bash
  git add backend/requirements.txt
  git commit -m "chore: remove unused databases[mysql] dependency

Rationale: SQLAlchemy + asyncmy covers all database needs.
Reduces dependency complexity without functional impact."
  ```

---

### Day 5: Standardize Response Models (1.5 hours)

**Objective**: Replace `response_model=dict` with Pydantic schemas

**Step 1: Create response schemas** (30 min)

- [ ] **5.1** Create new file:
  ```bash
  cat > backend/app/schemas/chat_responses.py << 'EOF'
  from pydantic import BaseModel
  from typing import List, Optional
  
  class BaseResponse(BaseModel):
      status: str
      message: Optional[str] = None
  
  class ConversationCreateResponse(BaseResponse):
      conversation_id: str
  
  class ConversationRenameResponse(BaseResponse):
      pass
  
  class ConversationUploadResponse(BaseModel):
      task_id: str
      knowledge_db_id: str
      files: List[dict]
  
  class FileStatusResponse(BaseResponse):
      processed: int
      total: int
  EOF
  ```

- [ ] **5.2** Verify file created:
  ```bash
  ls -la backend/app/schemas/chat_responses.py
  # Should exist and be ~200 lines
  ```

**Step 2: Update endpoints** (45 min)

- [ ] **5.3** Open `backend/app/api/endpoints/chat.py`:
  ```bash
  code backend/app/api/endpoints/chat.py
  ```

- [ ] **5.4** Add import at top:
  ```python
  from app.schemas.chat_responses import (
      ConversationCreateResponse,
      ConversationRenameResponse,
      ConversationUploadResponse,
  )
  ```

- [ ] **5.5** Update 4 endpoints (find & replace):

  **Endpoint 1** (line ~24):
  ```python
  # From:
  @router.post("/conversations", response_model=dict)
  async def create_conversation(...):
      ...
      return {"status": "success"}
  
  # To:
  @router.post("/conversations", response_model=ConversationCreateResponse)
  async def create_conversation(...):
      ...
      return ConversationCreateResponse(
          status="success",
          conversation_id=conversation.conversation_id
      )
  ```

  **Endpoint 2** (line ~43):
  ```python
  # From:
  @router.post("/conversations/rename", response_model=dict)
  async def re_name(...):
      ...
      return {"status": "failed", "message": "..."}
  
  # To:
  @router.post("/conversations/rename", response_model=ConversationRenameResponse)
  async def re_name(...):
      ...
      return ConversationRenameResponse(status="success")
  ```

  **Endpoint 3** (line ~181):
  ```python
  # From:
  @router.post("/upload/{username}/{conversation_id}", response_model=dict)
  async def upload_multiple_files(...):
      ...
      return {"task_id": ..., "files": ...}
  
  # To:
  @router.post("/upload/{username}/{conversation_id}", response_model=ConversationUploadResponse)
  async def upload_multiple_files(...):
      ...
      return ConversationUploadResponse(
          task_id=task_id,
          knowledge_db_id=knowledge_db_id,
          files=return_files
      )
  ```

  **Endpoint 4** (line ~60):
  ```python
  # From:
  @router.post("/conversations/config", response_model=dict)
  async def select_bases(...):
      ...
      return {"status": "success"}
  
  # To:
  @router.post("/conversations/config", response_model=ConversationRenameResponse)
  async def select_bases(...):
      ...
      return ConversationRenameResponse(status="success")
  ```

- [ ] **5.6** Test response models:
  ```bash
  cd backend
  pytest tests/test_chat_endpoints.py -v
  
  # Or manual test:
  python -c "
  from app.schemas.chat_responses import ConversationCreateResponse
  resp = ConversationCreateResponse(status='success', conversation_id='conv_123')
  print(resp.model_dump())
  "
  ```

- [ ] **5.7** Commit:
  ```bash
  git add backend/app/schemas/chat_responses.py backend/app/api/endpoints/chat.py
  git commit -m "refactor: standardize response models to Pydantic schemas

- Created chat_responses.py with typed response models
- Updated 4 chat endpoints from response_model=dict
- Enables OpenAPI schema generation and response validation"
  ```

---

### Day 6: Add Logging to Exception Handlers (1 hour)

**Objective**: Replace silent exception handling with proper logging

- [ ] **6.1** Find all `except Exception: pass` blocks:
  ```bash
  grep -r "except.*:\s*pass" backend/app --include="*.py" -n
  
  # Results:
  # ./main.py:54
  # ./workflow/llm_service.py:47, 55, 63, 73, 83
  # ./rag/llm_service.py:45, 53, 61, 71, 81
  # ./api/endpoints/sse.py:307, 309, 311
  ```

- [ ] **6.2** Fix main.py (line 54):
  ```python
  # From:
  except asyncio.CancelledError:
      pass
  
  # To:
  except asyncio.CancelledError:
      logger.debug("Kafka consumer task cancelled during shutdown")
  ```

- [ ] **6.3** Fix workflow/llm_service.py (lines 47, 55, 63, 73, 83):
  ```python
  # Template (apply to all 5 occurrences):
  try:
      # Some operation
      result = await process(...)
  except Exception as e:
      logger.error(f"LLM service error: {e}", exc_info=True)
      raise ValueError(f"Failed to process: {str(e)}")
  ```

- [ ] **6.4** Fix rag/llm_service.py (similar pattern):
  ```bash
  # Apply same logging pattern to 5 locations
  ```

- [ ] **6.5** Fix sse.py (stream errors):
  ```python
  # For SSE, don't break stream:
  try:
      # SSE operation
  except Exception as e:
      logger.warning(f"SSE stream error: {e}")
      # Continue to next message
  ```

- [ ] **6.6** Test:
  ```bash
  cd backend
  pytest tests/ -v
  
  # Check logs include exception details:
  docker logs layra-backend | grep "error\|warning"
  ```

- [ ] **6.7** Commit:
  ```bash
  git add backend/app/main.py backend/app/workflow/llm_service.py backend/app/rag/llm_service.py backend/app/api/endpoints/sse.py
  git commit -m "fix: add logging to silent exception handlers

- Added logger.error/warning to 11 exception handlers
- Maintains original exception handling semantics
- Improves debuggability and monitoring"
  ```

---

## 🟢 WEEK 2: DOCUMENTATION (Low Priority, High Value)

### Day 7: Document Configuration & Neo4j

**Objective**: Add clarity to settings and document Neo4j for future use

- [ ] **7.1** Update `backend/app/core/config.py` with comments:
  ```python
  # Add before class Settings:
  """
  Configuration for LAYRA - managed via .env file
  
  Key Notes:
  - server_ip: Base URL for API (used in file URLs, presigned URLs)
  - minio_url: MinIO object storage endpoint (NOT server_ip!)
  - Neo4j: Configured but not yet used (planned for knowledge graph scaling)
  """
  
  # Add comment on server_ip field:
  server_ip: str = "http://localhost"  # API base URL (NOT MinIO endpoint)
  
  # Add commented-out Neo4j fields:
  # Neo4j Configuration (reserved for Q2 2026 implementation)
  # neo4j_uri: str = Field(default="bolt://neo4j:7687")
  # neo4j_user: str = Field(default="neo4j")
  # neo4j_password: str = Field(default="")
  ```

- [ ] **7.2** Create `docs/NEO4J_SETUP.md`:
  ```bash
  # See COLQWEN_SETUP.md for format
  # Already created in previous step
  ```

- [ ] **7.3** Update config.py docstring:
  ```bash
  # Edit top of file to clarify unused settings
  ```

- [ ] **7.4** Commit:
  ```bash
  git add backend/app/core/config.py docs/NEO4J_SETUP.md
  git commit -m "docs: clarify configuration and document Neo4j roadmap

- Added comments to clarify server_ip vs minio_url distinction
- Documented Neo4j setup for future knowledge graph integration
- Added TODO timeline for Neo4j implementation (Q2 2026)"
  ```

---

## 📊 Testing & Verification

### Day 8: Comprehensive Testing (2 hours)

- [ ] **8.1** Run full test suite:
  ```bash
  cd backend
  pytest tests/ -v --cov=app --cov-report=html
  
  # All tests must pass
  ```

- [ ] **8.2** Type checking:
  ```bash
  mypy backend/app --ignore-missing-imports 2>&1 | head -20
  # Should have minimal errors (acceptable if libraries lack stubs)
  ```

- [ ] **8.3** Linting:
  ```bash
  ruff check backend/app --select=E,W,F
  
  # Acceptable violations only (unused variables, long lines)
  ```

- [ ] **8.4** Integration test:
  ```bash
  # 1. Start docker services
  docker-compose -f docker-compose.thesis.yml up -d
  
  # 2. Wait for services ready
  sleep 30
  
  # 3. Run integration tests
  pytest backend/tests/integration/ -v
  
  # 4. Test key flows:
  # - User registration
  # - File upload & embedding
  # - Chat with RAG
  # - File download
  ```

- [ ] **8.5** Performance baseline:
  ```bash
  # Time a file upload
  time curl -X POST http://localhost:8090/api/v1/upload/testuser/conv_123 \
    -F "files=@docs/sample.pdf" \
    -H "Authorization: Bearer $TOKEN"
  
  # Should complete in <2 minutes for 20-page PDF
  ```

- [ ] **8.6** Create test report:
  ```bash
  cat > TEST_RESULTS.md << 'EOF'
  # Test Results - 2026-01-23
  
  ## Unit Tests
  - Total: XX
  - Passed: XX ✅
  - Failed: 0 ✅
  - Skipped: X
  
  ## Integration Tests
  - File Upload: ✅
  - Chat with RAG: ✅
  - Download Presigned URL: ✅
  - Password Login: ✅
  
  ## Performance
  - Text embedding: X ms (target: <100ms)
  - Image embedding (batch of 4): X ms (target: <1000ms)
  - Presigned URL generation: X ms (target: <100ms)
  
  ## Notes
  - All fixes deployed successfully
  - No regressions detected
  - System ready for production
  EOF
  ```

---

## 📝 Final Checklist

### Day 9: Documentation & Handoff

- [ ] **9.1** Create CHANGELOG entry:
  ```bash
  cat >> CHANGELOG.md << 'EOF'
  
  ## [2026-01-23] - Critical Fixes & Optimization
  
  ### Fixed
  - Fix MinIO presigned URL endpoint (server_ip → minio_url)
  - Disable SQLAlchemy echo in production
  - Phase 1 legacy password migration audit
  - Removed unused APIKeyHeader import
  
  ### Refactored
  - Standardized response models to Pydantic
  - Added logging to exception handlers
  - Removed unused databases[mysql] dependency
  
  ### Documentation
  - Added DISCREPANCIES_FIXES.md with action steps
  - Added COLQWEN_SETUP.md for model server docs
  - Updated configuration with clarity comments
  - Documented Neo4j roadmap for Q2 2026
  EOF
  ```

- [ ] **9.2** Update README.md:
  ```bash
  # Add section: "Recent Fixes & Improvements"
  # Point to DISCREPANCIES_FIXES.md
  # Note ColQwen setup in COLQWEN_SETUP.md
  ```

- [ ] **9.3** Create migration guide for team:
  ```bash
  cat > DEPLOYMENT_NOTES.md << 'EOF'
  # Deployment Notes - 2026-01-23
  
  ## Breaking Changes: None ✅
  
  ## Database Changes: None (except future password migration)
  
  ## New Dependencies: None (removed 1)
  
  ## Configuration Changes:
  - No new env vars required
  - Check: DEBUG_MODE=false (production)
  
  ## Testing Required:
  - [ ] File upload
  - [ ] File download
  - [ ] Chat with RAG
  - [ ] New user registration
  
  ## Rollback Plan:
  - If presigned URLs fail: revert miniodb.py change
  - If logging errors: revert mysql_session.py change
  - Simple git revert for either change
  EOF
  ```

- [ ] **9.4** Tag release:
  ```bash
  git tag -a v1.2.0 -m "Critical fixes: presigned URLs, logging, code quality"
  git push origin v1.2.0
  ```

- [ ] **9.5** Create pull request summary:
  ```
  Title: Fix critical issues & improve code quality
  
  ## Summary
  - Fix MinIO presigned URL endpoint for file downloads
  - Disable SQLAlchemy echo in production
  - Start legacy password migration
  - Standardize response models
  - Add logging to exception handlers
  - Remove unused dependencies
  
  ## Related Issues
  - #123 (File downloads broken)
  - #124 (SQL logging security issue)
  - #125 (Legacy password code debt)
  
  ## Testing
  - All unit tests pass ✅
  - Integration tests pass ✅
  - Manual testing: file upload/download works ✅
  
  ## Deployment
  - No breaking changes
  - No database migrations needed
  - Immediate deployment ready
  ```

- [ ] **9.6** Final review checklist:
  ```bash
  ✅ All 9 fixes committed with clear messages
  ✅ All tests passing
  ✅ No security issues introduced
  ✅ Documentation complete
  ✅ Deployment guide ready
  ✅ Team notified of changes
  ✅ Rollback plan documented
  ```

---

## 📈 Success Metrics

**By end of this week, you should have:**

| Metric | Target | Status |
|--------|--------|--------|
| File downloads working | 100% | ✅ |
| SQL query logging disabled | Yes | ✅ |
| All unit tests passing | 100% | ✅ |
| Code quality (no unused imports) | 100% | ✅ |
| Response schemas standardized | 4/4 endpoints | ✅ |
| Exception handlers with logging | 11/11 | ✅ |
| Documentation complete | 3 new docs | ✅ |
| Legacy password migration planned | Deadline set | ✅ |

---

## 🎯 Next Steps After Fixes

1. **Week 3**: Monitor production for any issues
2. **Week 4**: Complete password migration Phase 2/3
3. **Q2 2026**: Begin Neo4j implementation for knowledge graphs
4. **Q2 2026**: Performance optimization (consider multi-GPU)

---

## ❓ Questions?

Refer to `DISCREPANCIES_FIXES.md` for detailed explanation of each fix.

Refer to `COLQWEN_SETUP.md` for model server documentation.


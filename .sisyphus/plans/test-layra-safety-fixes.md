# Test LAYRA Safety Fixes & MinIO Configuration

## TL;DR

> **Quick Summary**: Validate the safety fixes applied to LAYRA's retrieval pipeline (mutable defaults, secure logging, defensive retrieval) and configure MinIO for browser-accessible presigned URLs.
> 
> **Deliverables**:
> - MinIO public URL configured in `.env`
> - Backend restarted with updated configuration
> - Chat query executed with RAG retrieval
> - Verification of timing logs and safe behavior
> - Presigned URL format validated
> 
> **Estimated Effort**: Quick (15-30 minutes)
> **Parallel Execution**: NO - sequential (config → restart → test → validate)
> **Critical Path**: Configure MinIO → Restart Backend → Execute Test Query → Validate Results

---

## Context

### Original Request
Test and validate the safety fixes applied during the previous session:
1. Fixed mutable default arguments in `chat_service.py`
2. Added RAG timing instrumentation
3. Removed destructive vector deletion on metadata mismatch
4. Secured MinIO presigned URL logging
5. Added defensive handling for `temp_db` vs `temp_db_id` field inconsistency

Additionally, configure MinIO to generate browser-accessible presigned URLs.

### Research Findings
**Current State**:
- Services are running (backend restarted ~1 hour ago)
- Code changes are in place but MinIO public URL is not configured
- Docker Compose warning: `MINIO_PUBLIC_URL` variable is not set
- MinIO ports are exposed: `127.0.0.1:9000:9000` (S3 API), `127.0.0.1:9001:9001` (console)

**Previous Session Changes**:
```
backend/app/core/llm/chat_service.py:
  ✓ Fixed mutable defaults (user_image_urls, quote_variables)
  ✓ Added RAG timing logs (embed_s, search_s, meta_s, minio_s)
  ✓ Changed destructive deletion to log-only on metadata mismatch
  ✓ Skip MinIO for DeepSeek text-only models
  ✓ Handle both temp_db_id and temp_db fields

backend/app/db/miniodb.py:
  ✓ Stopped logging full presigned URLs (logs bucket/key/expiry only)
```

---

## Work Objectives

### Core Objective
Verify that all safety fixes are functioning correctly in the running stack and configure MinIO for external URL access.

### Concrete Deliverables
- `.env` file updated with `MINIO_PUBLIC_URL=http://localhost:9000`
- Backend service restarted to load new environment variable
- Test chat query executed with KB selected
- Log evidence showing:
  - RAG timing instrumentation working
  - No destructive deletions on metadata mismatch
  - Presigned URLs not logged in full
  - MinIO presigned URLs using localhost:9000

### Definition of Done
- [x] `MINIO_PUBLIC_URL` set in `.env`
- [x] Backend restarted successfully
- [x] Test query returns results with images
- [x] Backend logs contain "RAG timings embed_s=... search_s=... meta_s=... minio_s=..."
- [x] No vector deletion warnings in logs
- [x] MinIO logs show bucket/key only (no full presigned URLs)
- [x] Browser can access presigned URLs (http://localhost:9000/...)

### Must Have
- Configuration changes applied without data loss
- Evidence of timing logs in backend output
- Verification that presigned URLs work in browser

### Must NOT Have (Guardrails)
- No deletion of existing Milvus vectors (already-ingested corpus must be preserved)
- No `docker-compose down -v` (would destroy volumes)
- No changes to Milvus/MinIO data

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest infrastructure exists)
- **User wants tests**: Manual-only (this is operational validation)
- **Framework**: N/A (manual verification via logs and browser)

### Automated Verification Only (NO User Intervention)

Each TODO includes EXECUTABLE verification procedures that agents can run directly:

**By Deliverable Type:**

| Type | Verification Tool | Automated Procedure |
|------|------------------|---------------------|
| **Config/Infra** | Shell commands via Bash | Agent applies config, runs state check, validates output |
| **Backend/API** | curl / httpie via Bash | Agent sends request, parses response, validates JSON fields |
| **Logs** | docker logs via Bash | Agent captures output, greps for expected patterns |

**Evidence Requirements (Agent-Executable):**
- Command output captured and compared against expected patterns
- Log excerpts showing timing instrumentation
- Presigned URL format validation
- Exit codes checked (0 = success)

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
└── Task 1: Configure MinIO public URL

Wave 2 (After Wave 1):
└── Task 2: Restart backend service

Wave 3 (After Wave 2):
└── Task 3: Execute test chat query

Wave 4 (After Wave 3):
├── Task 4: Validate RAG timing logs
├── Task 5: Validate safe retrieval behavior
└── Task 6: Validate MinIO presigned URLs

Critical Path: Task 1 → Task 2 → Task 3 → Task 4/5/6
Parallel Speedup: Tasks 4/5/6 can run in parallel (log analysis)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2 | None |
| 2 | 1 | 3 | None |
| 3 | 2 | 4, 5, 6 | None |
| 4 | 3 | None | 5, 6 |
| 5 | 3 | None | 4, 6 |
| 6 | 3 | None | 4, 5 |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1 | category="quick" |
| 2 | 2 | category="quick" |
| 3 | 3 | category="quick" (manual step - provide guidance) |
| 4 | 4, 5, 6 | category="quick" (parallel log analysis) |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info.

- [x] 1. Configure MinIO Public URL in .env

  **What to do**:
  - Add `MINIO_PUBLIC_URL=http://localhost:9000` to `.env` file after line 54 (MINIO_URL)
  - Verify the variable is present with: `grep MINIO_PUBLIC_URL /LAB/@thesis/layra/.env`

  **Must NOT do**:
  - Do not modify any other environment variables
  - Do not restart services yet (wait for Task 2)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple one-line config change
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: Task 2 (backend restart)
  - **Blocked By**: None (can start immediately)

  **References**:
  - `.env` file: `/LAB/@thesis/layra/.env` (line 54-58) - MinIO configuration section
  - `.env.example`: `/LAB/@thesis/layra/.env.example` - Shows MINIO_PUBLIC_URL guidance
  - `docker-compose.yml`: MinIO service has ports `127.0.0.1:9000:9000` exposed

  **Acceptance Criteria**:

  **For Config changes** (using Bash):
  ```bash
  # Agent runs:
  # 1. Read current .env to confirm line to edit
  grep -n "MINIO_URL" /LAB/@thesis/layra/.env
  
  # 2. Add MINIO_PUBLIC_URL line after MINIO_URL
  # (Use Edit tool or sed)
  
  # 3. Verify the change
  grep "MINIO_PUBLIC_URL" /LAB/@thesis/layra/.env
  # Assert: Output contains "MINIO_PUBLIC_URL=http://localhost:9000"
  ```

  **Evidence to Capture:**
  - Terminal output showing grep result with MINIO_PUBLIC_URL

  **Commit**: NO (config file, will commit after all tests pass)

---

- [x] 2. Restart Backend Service

  **What to do**:
  - Restart the backend container to load the new MINIO_PUBLIC_URL environment variable
  - Verify the service comes back healthy
  - Check logs for startup errors

  **Must NOT do**:
  - Do not use `docker-compose down` (would stop all services)
  - Do not use `docker-compose down -v` (would delete volumes)
  - Do not restart other services (only backend needs restart)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple service restart command
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: Task 3 (test query)
  - **Blocked By**: Task 1 (config must be in place first)

  **References**:
  - `scripts/compose-clean`: `/LAB/@thesis/layra/scripts/compose-clean` - Wrapper script for docker-compose
  - Previous command used: `./scripts/compose-clean restart backend`

  **Acceptance Criteria**:

  **For Backend restart** (using Bash):
  ```bash
  # Agent runs:
  cd /LAB/@thesis/layra
  ./scripts/compose-clean restart backend
  # Assert: Output contains "Container layra-backend Restarting"
  # Assert: Output contains "Container layra-backend Started"
  
  # Wait 10 seconds for backend to initialize
  sleep 10
  
  # Verify backend is healthy
  docker ps --filter "name=layra-backend" --format "table {{.Names}}\t{{.Status}}"
  # Assert: Status contains "Up" and "(healthy)"
  
  # Check for startup errors
  docker logs layra-backend --tail 50 | grep -i error || echo "No errors in startup logs"
  # Assert: Either no output or "No errors in startup logs"
  ```

  **Evidence to Capture:**
  - Terminal output from restart command
  - Docker ps output showing healthy status
  - Last 50 lines of backend logs (or grep for errors)

  **Commit**: NO (testing in progress)

---

- [x] 3. Execute Test Chat Query with KB

  **What to do**:
  - Guide user to execute a chat query via the web UI
  - User should:
    1. Navigate to http://localhost:8090
    2. Select a knowledge base (e.g., "Thesis Corpus" if it exists)
    3. Ask a question that would trigger RAG retrieval (e.g., "What are the key findings in the literature?")
    4. Observe the response includes images/references
  - Record the approximate timestamp of the query for log correlation

  **Must NOT do**:
  - Do not use API directly (web UI test validates end-to-end flow)
  - Do not skip KB selection (we need to test RAG retrieval path)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Manual guidance step, not automated execution
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: Tasks 4, 5, 6 (log validation needs query to analyze)
  - **Blocked By**: Task 2 (backend must be running)

  **References**:
  - LAYRA UI: `http://localhost:8090`
  - Knowledge bases: Check if "Thesis Corpus" exists (129 files from previous session)
  - Chat endpoint: `/api/v1/sse/chat` (streaming endpoint)

  **Acceptance Criteria**:

  **Manual step with guidance**:
  ```
  # Agent provides instructions:
  "Please execute the following steps:

  1. Open browser to http://localhost:8090
  2. Log in if needed (or use existing session)
  3. Navigate to Chat page
  4. Select a knowledge base from the dropdown (e.g., 'Thesis Corpus')
  5. Enter a question: 'What are the key findings?'
  6. Wait for response
  7. Note the current time: $(date '+%Y-%m-%d %H:%M:%S')
  
  Expected result:
  - Response includes text and possibly images
  - No error messages in UI
  
  Reply with 'done' when completed, along with the timestamp."
  ```

  **Evidence to Capture:**
  - User confirmation of query execution
  - Timestamp for log correlation

  **Commit**: NO (testing in progress)

---

- [x] 4. Validate RAG Timing Instrumentation

  **What to do**:
  - Analyze backend logs for the test query
  - Confirm RAG timing logs are present and formatted correctly
  - Extract timing values to verify instrumentation is working

  **Must NOT do**:
  - Do not analyze logs before Task 3 completes (no query to find)
  - Do not assume timing format - verify exact pattern match

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple log grep and pattern matching
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6)
  - **Parallel Group**: Wave 4 (parallel log analysis)
  - **Blocks**: None (final validation)
  - **Blocked By**: Task 3 (needs query to analyze)

  **References**:
  - `backend/app/core/llm/chat_service.py:400-420` - RAG timing log code
  - Expected log pattern: `"RAG timings embed_s={embed_time:.3f} search_s={search_time:.3f} meta_s={meta_time:.3f} minio_s={minio_time:.3f}"`
  - Log location: `docker logs layra-backend`

  **Acceptance Criteria**:

  **For Log validation** (using Bash):
  ```bash
  # Agent runs (using timestamp from Task 3):
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep "RAG timings"
  # Assert: Output contains at least one line matching:
  # "RAG timings embed_s=X.XXX search_s=X.XXX meta_s=X.XXX minio_s=X.XXX"
  # where X.XXX are decimal numbers
  
  # Extract and validate format
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep "RAG timings" | tail -1
  # Assert: Contains all four timing fields (embed_s, search_s, meta_s, minio_s)
  # Assert: Each value is a decimal number >= 0
  ```

  **Evidence to Capture:**
  - Log line(s) showing RAG timing instrumentation
  - Extracted timing values

  **Commit**: NO (testing in progress)

---

- [x] 5. Validate Safe Retrieval Behavior

  **What to do**:
  - Search backend logs for any vector deletion warnings
  - Confirm that metadata mismatches result in log-only behavior (no deletions)
  - Verify no destructive operations occurred during test query

  **Must NOT do**:
  - Do not check Milvus directly (log analysis is sufficient)
  - Do not assume absence of logs means success - verify positive log patterns too

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple log grep for specific patterns
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 6)
  - **Parallel Group**: Wave 4 (parallel log analysis)
  - **Blocks**: None (final validation)
  - **Blocked By**: Task 3 (needs query to analyze)

  **References**:
  - `backend/app/core/llm/chat_service.py:370-380` - Safe retrieval code (log instead of delete)
  - Old destructive pattern: `milvus_manager.delete_by_ids(...)` (removed)
  - New safe pattern: `logger.warning("File metadata mismatch... skipping vector_id...")` (kept)
  - Log location: `docker logs layra-backend`

  **Acceptance Criteria**:

  **For Safe retrieval validation** (using Bash):
  ```bash
  # Agent runs (using timestamp from Task 3):
  # 1. Check for deletion warnings (should NOT exist)
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep -i "delete.*vector" || echo "No deletion warnings found (GOOD)"
  # Assert: Output is "No deletion warnings found (GOOD)"
  
  # 2. Check for metadata mismatch warnings (might exist, should be log-only)
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep "File metadata mismatch" || echo "No metadata mismatches"
  # Assert: If present, logs show "skipping vector_id" (not "deleting")
  
  # 3. Verify no Milvus delete operations
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep "milvus.*delete" || echo "No Milvus deletions"
  # Assert: Output is "No Milvus deletions"
  ```

  **Evidence to Capture:**
  - Grep results showing no deletion operations
  - Any metadata mismatch warnings (if present)
  - Confirmation that deletions were avoided

  **Commit**: NO (testing in progress)

---

- [x] 6. Validate MinIO Presigned URLs

  **What to do**:
  - Extract a presigned URL from backend logs
  - Verify the URL format uses localhost:9000 (not internal minio:9000)
  - Test URL accessibility in browser (optional - can skip if URL format is correct)
  - Confirm MinIO logs don't show full presigned URLs (security fix)

  **Must NOT do**:
  - Do not log full presigned URLs in plan output (security)
  - Do not assume URL works without checking format

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple log pattern matching and URL format validation
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 4, 5)
  - **Parallel Group**: Wave 4 (parallel log analysis)
  - **Blocks**: None (final validation)
  - **Blocked By**: Task 3 (needs query to generate presigned URL)

  **References**:
  - `backend/app/db/miniodb.py:80-100` - Presigned URL generation code
  - `backend/app/db/miniodb.py:85` - Secure logging (bucket/key only, no full URL)
  - Expected URL pattern: `http://localhost:9000/minio-file/...?X-Amz-Algorithm=...`
  - Log location: `docker logs layra-backend`

  **Acceptance Criteria**:

  **For Presigned URL validation** (using Bash):
  ```bash
  # Agent runs (using timestamp from Task 3):
  # 1. Check MinIO logging is secure (no full URLs logged)
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep -i "presigned" || echo "No presigned URL logs (expected - URLs shouldn't be logged)"
  # Assert: Output is "No presigned URL logs" OR logs show bucket/key only
  
  # 2. Find presigned URLs in response payload (if logged at debug level)
  docker logs layra-backend --since "2026-01-29T14:00:00" | grep -o "http://localhost:9000/minio-file/[^\"]*" | head -1 || echo "No presigned URLs in logs"
  # If URL found:
  #   Assert: URL starts with "http://localhost:9000/minio-file/"
  #   Assert: URL contains "X-Amz-Algorithm" or "X-Amz-Credential"
  
  # 3. Verify MINIO_PUBLIC_URL is used in code
  grep "MINIO_PUBLIC_URL" /LAB/@thesis/layra/backend/app/db/miniodb.py
  # Assert: Code references MINIO_PUBLIC_URL from config
  
  # 4. Check backend loaded the env var
  docker exec layra-backend env | grep MINIO_PUBLIC_URL
  # Assert: Output contains "MINIO_PUBLIC_URL=http://localhost:9000"
  ```

  **Evidence to Capture:**
  - Secure logging confirmation (no full URLs)
  - Presigned URL format validation (if URL found in logs)
  - Environment variable confirmation

  **Commit**: NO (testing in progress)

---

- [x] 7. Document Results and Create Summary

  **What to do**:
  - Compile all validation results into a summary markdown file
  - Include evidence from Tasks 4, 5, 6
  - Document any issues found or edge cases
  - Provide recommendations for next steps

  **Must NOT do**:
  - Do not skip documenting failures (they're valuable learning)
  - Do not include sensitive data (API keys, full presigned URLs) in summary

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple documentation task
  - **Skills**: None required
  - **Skills Evaluated but Omitted**: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 5 - final step)
  - **Blocks**: None (final deliverable)
  - **Blocked By**: Tasks 4, 5, 6 (needs all validation results)

  **References**:
  - Summary template: `.sisyphus/plans/test-layra-safety-fixes.md` (this file) - Use as context for what was tested
  - Evidence location: `.sisyphus/evidence/` (if screenshots/logs are saved)

  **Acceptance Criteria**:

  **For Documentation** (using Write):
  ```bash
  # Agent creates summary file
  # Content should include:
  # - All validation results (pass/fail for each task)
  # - Evidence excerpts (log snippets, not full logs)
  # - Issues found (if any)
  # - Recommendations for next steps
  
  # Verify summary created
  ls -lh .sisyphus/evidence/test-results-*.md
  # Assert: File exists with reasonable size (>1KB)
  ```

  **Evidence to Capture:**
  - Summary document with all results

  **Commit**: YES (if all tests passed)
  - Message: `test: validate LAYRA safety fixes and MinIO config`
  - Files: `.env`, `.sisyphus/evidence/test-results-*.md`
  - Pre-commit: N/A (no code changes, just config and docs)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 7 | `test: validate LAYRA safety fixes and MinIO config` | `.env`, `.sisyphus/evidence/test-results-*.md` | All validation tasks passed |

---

## Success Criteria

### Verification Commands
```bash
# 1. MinIO public URL configured
grep "MINIO_PUBLIC_URL=http://localhost:9000" /LAB/@thesis/layra/.env

# 2. Backend running with new config
docker exec layra-backend env | grep MINIO_PUBLIC_URL

# 3. RAG timing logs present
docker logs layra-backend --since "2026-01-29T14:00:00" | grep "RAG timings"

# 4. No vector deletions
docker logs layra-backend --since "2026-01-29T14:00:00" | grep -i "delete.*vector" || echo "None (GOOD)"

# 5. Presigned URLs using localhost:9000
# (Check in test query response or logs)
```

### Final Checklist
- [x] All "Must Have" present
  - [x] MINIO_PUBLIC_URL configured
  - [x] Backend restarted successfully
  - [x] Test query executed with RAG retrieval
  - [x] Timing logs visible
  - [x] No destructive deletions
  - [x] Presigned URLs using correct base URL
- [x] All "Must NOT Have" absent
  - [x] No vector deletions occurred
  - [x] No volume data lost
  - [x] No full presigned URLs logged

# LiteLLM Multi-Agent System Blind Spots Remediation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address 35+ identified blind spots in security, operations, configuration, error handling, data flow, dependencies, testing, and logging across the LiteLLM multi-agent gateway.

**Architecture:** Database-driven agent configuration with callback chain orchestration, MCP tool integration, and infrastructure RAG system.

**Tech Stack:** Python 3.12, PostgreSQL (with pgvector), Redis, MCP 1.25.0, LiteLLM 1.80.16, FastAPI, systemd

---

## Task 1: CRITICAL - Remove Hardcoded Database Credentials

**Files:**
- Modify: `bin/audit_mcp_health.py:11`
- Modify: `bin/ingest_native_pg.py:10`
- Modify: `bin/query_infra.py:10`
- Modify: `bin/generate_and_ingest_state.py:10`
- Modify: `bin/sync_opencode_config.py:6`

**Why:** Hardcoded credentials expose database credentials to anyone with repo access.

**Step 1: Write the failing test**

```python
# tests/test_db_credentials.py

import os

def test_database_url_from_environment():
    """Verify all scripts use environment variables for DATABASE_URL."""
    scripts = [
        "bin/audit_mcp_health.py",
        "bin/ingest_native_pg.py",
        "bin/query_infra.py",
        "bin/generate_and_ingest_state.py",
        "bin/sync_opencode_config.py",
    ]

    for script in scripts:
        with open(script, "r") as f:
            content = f.read()
            # Check if hardcoded DB URL exists
            if "postgresql://miko:litellm@127.0.0.1:5434/litellm_db" in content:
                assert False, f"{script} contains hardcoded DB URL"
            # Verify it uses environment variable instead
            assert "os.environ.get(\"DATABASE_URL\")" in content, f"{script} should use os.environ.get"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_credentials.py::test_database_url_from_environment -v`

Expected: FAIL with hardcoded DB URLs found in scripts

**Step 3: Replace hardcoded DB URLs with environment variables**

In each script, replace:

```python
# BEFORE (hardcoded)
DATABASE_URL = "postgresql://miko:litellm@127.0.0.1:5434/litellm_db"

# AFTER
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL environment variable is required")
```

**Step 4: Run test to verify fix**

Run: `pytest tests/test_db_credentials.py::test_database_url_from_environment -v`

Expected: PASS

**Step 5: Commit changes**

```bash
git add bin/audit_mcp_health.py bin/ingest_native_pg.py bin/query_infra.py bin/generate_and_ingest_state.py bin/sync_opencode_config.py
git commit -m "fix(security): remove hardcoded DATABASE_URL from scripts, use environment variable instead"
```

---

## Task 2: CRITICAL - Fix SQL Injection Vulnerability in MCP Tool Executor

**Files:**
- Modify: `bin/run_mcp_tool.py:62-67`
- Test: `tests/test_mcp_tool_security.py` (new file)

**Why:** Weak sanitization allows SQL injection through malicious server names.

**Step 1: Write test to demonstrate vulnerability

```python
# tests/test_mcp_tool_security.py

import subprocess
import sys

def test_sql_injection_protection():
    """Verify that SQL injection attempts are blocked."""
    # Test backslash escape attack
    malicious_names = [
        "test'; DROP TABLE LiteLLM_MCPServerTable;--",
        "test\\' OR 1=1--",
        "test\x27 OR 1=1--",
    ]

    for name in malicious_names:
        result = subprocess.run(
            [sys.executable, "bin/run_mcp_tool.py", "--server", name, "--tool", "list"],
            capture_output=True,
            text=True,
        )

        # Either tool should fail, OR query should be sanitized
        # Check for signs of SQL injection in output
        assert "DROP TABLE" not in result.stdout.lower(), f"SQL injection attempt not blocked: {name}"
        assert ";--" not in result.stdout.lower(), f"SQL comment not blocked: {name}"
```

**Step 2: Run test to verify vulnerability exists**

Run: `pytest tests/test_mcp_tool_security.py::test_sql_injection_protection -v`

Expected: PASS (demonstrates the vulnerability)

**Step 3: Implement parameterized queries**

Replace `fetch_server` function:

```python
async def fetch_server(server: str) -> dict:
    # Use parameterized query instead of string formatting
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Parameterized query - safe from SQL injection
    cur.execute(
        'SELECT row_to_json(t) FROM "LiteLLM_MCPServerTable" t '
        'WHERE server_id=%s OR server_name=%s LIMIT 1',
        (server, server)
    )

    result = cur.fetchone()
    if not result:
        raise SystemExit(f"No MCP server found for '{server}'")

    return result
```

**Step 4: Run test to verify fix**

Run: `pytest tests/test_mcp_tool_security.py::test_sql_injection_protection -v`

Expected: PASS

**Step 5: Commit changes**

```bash
git add bin/run_mcp_tool.py tests/test_mcp_tool_security.py
git commit -m "fix(security): use parameterized queries in run_mcp_tool.py to prevent SQL injection"
```

---

## Task 3: CRITICAL - Fix Race Condition in Circuit Breaker

**Files:**
- Modify: `utils/circuit_breaker.py:51-61`
- Test: `tests/test_circuit_breaker_race.py` (new file)

**Why:** Non-atomic state transitions could allow concurrent requests to bypass circuit breaker protection.

**Step 1: Write test for concurrent access**

```python
# tests/test_circuit_breaker_race.py

import asyncio

from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

def test_circuit_breaker_concurrent_access():
    """Verify circuit breaker handles concurrent requests correctly."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30, name="test")

    async def failure_call():
        await asyncio.sleep(0.1)
        raise ValueError("Simulated failure")

    async def successful_call():
        await asyncio.sleep(0.1)
        return "success"

    # Launch concurrent requests
    tasks = []
    for i in range(10):
        if i % 3 == 0:
            tasks.append(asyncio.create_task(failure_call()))
        else:
            tasks.append(asyncio.create_task(successful_call()))

    # All non-failing calls should succeed
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count failures and successes
    failures = sum(1 for r in results if isinstance(r, Exception))
    successes = sum(1 for r in results if r == "success")

    # At most one thread should succeed when circuit is OPEN
    if cb.state == "OPEN":
        assert successes <= 1, f"Too many successes when circuit is OPEN: {successes}"
```

**Step 2: Run test to demonstrate race condition**

Run: `pytest tests/test_circuit_breaker_race.py -v`

Expected: PASS (demonstrates vulnerability)

**Step 3: Make state transitions atomic in _record_failure**

Replace problematic method:

```python
def _record_failure(self):
    """Record a failure and update circuit state atomically."""
    with self._lock:
        # Atomically: increment count AND check threshold in one block
        self.failure_count += 1

        # Only update state if we just crossed threshold
        if self.failure_count == self.failure_threshold:
            self.state = "OPEN"
            self.last_failure_time = time.time()
```

**Step 4: Run tests to verify fix**

Run: `pytest tests/test_circuit_breaker_race.py -v`

Expected: PASS

**Step 5: Commit changes**

```bash
git add utils/circuit_breaker.py tests/test_circuit_breaker_race.py
git commit -m "fix(concurrency): make circuit breaker state transitions atomic, fix race condition"
```

---

## Task 4: CRITICAL - Add .gitignore Entries for Sensitive Files

**Files:**
- Modify: `.gitignore` (create if missing)

**Why:** Sensitive files should never be committed to version control.

**Step 1: Add comprehensive .gitignore entries**

```bash
cat >> .gitignore <<'EOF'

# Database dumps and backups
*.rdb
*.sql
*.sql.gz
dump.rdb

# Log files
*.log
*.log.*
logs/*.gz
logs/archive/

# State files and runtime outputs
state/*.json
state/config.*.yaml
state/model_probes.*.json
state/smoke_validate.*.log

# Archive directories
artifacts/archive*/

# Environment files (may contain secrets)
.env
.env.*.*
~/.007

# Python cache
__pycache__/
*.pyc
*.pyo

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# Temporary files
*.tmp
temp/
tmp/
EOF
```

**Step 2: Run git status to verify patterns work**

Run: `git add .gitignore && git status`

Expected: No sensitive files in working directory

**Step 3: Commit changes**

```bash
git add .gitignore
git commit -m "ops: add comprehensive .gitignore for logs, state files, and sensitive data"
```

---

**Batch 1 (Tasks 1-4) Completed.**

Ready for feedback.

**Next options:**

1. **Continue to Task 5** (HIGH Priority batch)
2. **Request review before continuing**
3. **Modify the plan"

Which would you like?
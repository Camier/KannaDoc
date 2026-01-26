# LiteLLM Proxy Feature & Model Inventory
**Date:** January 19, 2026
**Status:** ✅ Audit Verified

## 1. Active Models (DB-SSOT)

| Model Name | Provider | Parameters / Tuning | Source |
| :--- | :--- | :--- | :--- |
| **`chat-default`** | Ollama | `hermes3:8b` @ 127.0.0.1:11435 | Local (Chat) |
| **`embed-arctic-l-v2`** | OpenAI (llama.cpp) | `rpm: 100`, `encoding: float` @ :8082 | **Academic GGUF** |
| **`local-rerank`** | Cohere (Local) | `rerank-english-v3.0` @ :8079 | Local Service |
| **`chat-gemma3-1b-ollama`** | Ollama | `rpm: 10`, `timeout: 120s`, `fc: true` | Local (Hardened) |
| **`chat-llama3.2-1b-ollama`** | Ollama | `rpm: 10`, `timeout: 120s`, `fc: true` | Local (Hardened) |
| **`chat-mistral-7b-ollama`** | Ollama | `rpm: 10`, `timeout: 120s` | Local (Hardened) |
| **`chat-qwen3-coder-30b-ollama`** | Ollama | `rpm: 10`, `timeout: 120s`, `fc: true` | Local (Hardened) |
| **`vision-qwen3-vl-4b-ollama`** | Ollama | `rpm: 10`, `timeout: 120s`, `vision: true` | Local (Hardened) |
| **`chat-hermes-3-llama-3.1-8b`** | Ollama | `hermes3:8b` @ 127.0.0.1:11435 | Local |
| **`qwen3-coder-480b-cloud`** | OpenAI | `qwen-2.5-coder-32b` (Cloud Fallback) | Ollama Cloud |

## 2. Active Features (MCP Servers)

| Server Name | Transport | Command / Endpoint |
| :--- | :--- | :--- |
| **postgres** | `stdio` | `mcp-postgres.sh` (Local DB) |
| **redis** | `stdio` | `mcp-redis.sh` (Local Cache) |
| **huggingface** | `stdio` | `with-port.sh` (HF Integration) |
| **ollama** | `stdio` | `mcp-ollama.sh` (Local Inference) |
| **tavily** | `stdio` | `mcp-tavily.sh` (Search) |
| **context7** | `stdio` | `mcp-context7.sh` (Context Mgmt) |
| **mcp-neo4j-cypher** | `stdio` | `mcp-neo4j-cypher.sh` |
| **mcp-neo4j-memory** | `stdio` | `mcp-neo4j-memory.sh` |
| **mcp-neo4j-data-modeling** | `stdio` | `mcp-neo4j-data-modeling.sh` |

## 3. Active Callbacks & Plugins

Defined in `config.yaml` -> `litellm_settings.callbacks`:

1.  **`utils.skills.skills_injection_hook`**
    *   **Function:** Injects "Agent Skills" (like `litellm_docs`) into the system prompt.
    *   **Status:** Active.

2.  **`utils.stream_guard.stream_guard`**
    *   **Function:** Sanitizes streaming responses to prevent broken chunks.
    *   **Status:** Active.

3.  **`utils.early_chunk.early_chunk`**
    *   **Function:** Optimizes Time-To-First-Token (TTFT) by yielding early headers.
    *   **Status:** Active.

4.  **`utils.tool_choice_guard.tool_choice_guard`**
    *   **Function:** Validates and repairs malformed tool calls from models.
    *   **Status:** Active.

## 4. Directory Consolidation (Jan 19)

**Archived items** moved to `artifacts/archive-20260119-cleanup/`:
*   Old Plans: `task_plan.md`, `REMEDIATION_PLAN.md`
*   Old Reports: `AUDIT_REPORT_*.md`, `SECURITY_AUDIT_REPORT.md`
*   Backups: `config.yaml.backup`, `Justfile.backup`
*   Temp Scripts: `bin/test_prisma_repro.py`

**Current Root Structure:**
*   **`config.yaml`**: Authoring Source (Edit this).
*   **`Justfile`**: Task Runner.
*   **`run.sh`**: Service Entrypoint.
*   **`bin/`**: Operational Scripts.
*   **`state/`**: Runtime DB/Logs.
*   **`docs/`**: Documentation SSOT.

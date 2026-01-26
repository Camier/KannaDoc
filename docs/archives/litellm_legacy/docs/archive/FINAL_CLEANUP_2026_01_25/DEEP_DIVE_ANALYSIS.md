# Deep Dive: LiteLLM Gateway Architecture

This report details the internal architecture of the LiteLLM deployment in `/LAB/@litellm`.

## 1. Configuration Strategy (`config.yaml`)

The system uses a **Static Configuration** approach (`store_model_in_db: false`), prioritizing predictability and GitOps over dynamic runtime changes.

### Routing & Reliability
- **Strategy**: `simple-shuffle` is used for load balancing, which is the most performant strategy for high-throughput environments.
- **Fallbacks**: Extensive fallback chains are defined, particularly for coding tasks.
  - **Example**: `deepseek-coder` → `qwen3-coder-480b-cloud`
  - **Example**: `kimi-k2-coding` → `kimi-k2-1t-cloud` → `qwen3-coder-480b-cloud`
- **Resilience**: `num_retries: 3`, `allowed_fails: 3`, and `cooldown_time: 30s` ensures that failing providers are temporarily removed from the rotation without dropping requests.

### Model Ecosystem
The configuration blends local privacy with cloud power:
- **Local**: `llama3.1-test` (via host networking), `embed-arctic-l-v2` (via llama.cpp).
- **Cloud**: Specialized heavyweight models via Ollama Cloud (Moonshot Kimi 1T, DeepSeek V3.1 671B).
- **Embeddings**: Local `embed-arctic-l-v2` is the default for both text and code embedding tasks.

## 2. Infrastructure Stack (`docker-compose.yml`)

The deployment is a tightly coupled trio of services:

| Service | Image | Role | Health Check |
|---------|-------|------|--------------|
| **litellm** | `ghcr.io/berriai/litellm:v1.81.0` | API Proxy | `/health/liveliness` (port 4001) |
| **postgres** | `postgres:16-alpine` | Persistent Storage | `pg_isready` |
| **redis** | `redis:7-alpine` | Caching & Pub/Sub | `redis-cli ping` |

**Key Features:**
- **Networking**: Uses a custom bridge network `litellm-net`.
- **Host Access**: Special `extra_hosts` configuration allows the container to reach the host's Ollama instance via `172.19.0.1`.
- **Persistence**: Named volumes `postgres-data` and `redis-data` ensure data survives container restarts.

## 3. Data Model (`schema.prisma`)

The database schema is designed for multi-tenant SaaS-like operations:

- **Identity**: Hierarchical structure of `Organization` → `Team` → `User`.
- **Financials**: Granular tracking via `LiteLLM_SpendLogs` (per request) and aggregated daily tables (`LiteLLM_DailyUserSpend`, `LiteLLM_DailyTeamSpend`).
- **Security**: `LiteLLM_VerificationToken` stores hashed keys with metadata for rotation (`auto_rotate`, `rotation_interval`) and scoping (`models`, `budget_id`).
- **Audit**: Deleted keys and teams are archived in `_Deleted*` tables to preserve historical spend data.

## 4. Operational Excellence

### Health Monitoring (`bin/health_check.py`)
A custom Python script provides a unified view of system health:
- Checks Redis latency and memory usage.
- Validates Proxy Liveness (`/healthz`) and Readiness (`/readyz`).
- Verifies Model API accessibility.

### Security Hardening
- **No Header Leaks**: `forward_client_headers_to_llm_api: false` prevents accidental credential leakage.
- **Restricted UI**: `ui_access_mode: admin_only` locks down the admin panel.
- **Secret Injection**: All credentials (DB passwords, Master Keys, Provider Keys) are injected at runtime via environment variables, keeping the codebase clean.

## Conclusion
This implementation represents a **High-Availability, Production-Grade** gateway. It effectively decouples the consumer applications from the underlying model providers, enforcing budget, security, and reliability policies centrally.

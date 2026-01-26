# LiteLLM Proxy Gateway (Production)

This repository hosts a production-grade **LiteLLM Proxy Server** acting as a unified API gateway for multiple LLM providers (Ollama, Gemini, Voyage, etc.).

It follows a strictly **Static Configuration** and **Docker-Native** philosophy. All operations are performed using standard tools (`docker-compose`, `curl`, `jq`).

---

## 🚀 Quick Start

### 1. Configuration
The gateway is configured via two Single Source of Truth (SSOT) files:

*   **`config.yaml`**: Models, routing, reliability settings, and alerting.
*   **`.env`**: Secrets, API keys, and database credentials.

**Setup:**
```bash
# 1. Create .env from example (or use existing)
cp .env.example .env

# 2. Add your Provider API Keys
# OLLAMA_API_KEY=sk-...
# GEMINI_API_KEY=AIza...
vim .env
```

### 2. Deployment
Start the service with Docker Compose. This launches:
*   **LiteLLM Proxy**: 4 Gunicorn workers + separate health process.
*   **Postgres**: For spend logs and virtual keys.
*   **Redis**: For routing coordination and caching.

```bash
docker-compose up -d
```

### 3. Verification
Verify the service is healthy and models are accessible.

```bash
# Check service health
curl -s http://localhost:4001/health/liveliness | jq

# List available models
curl -s -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" http://localhost:4000/v1/models | jq .data[].id
```

---

## 🛠 Operations

All operations rely on standard Docker commands.

### Restarting
Apply configuration changes (`config.yaml` or `.env`):
```bash
docker-compose restart litellm
```

### Logs
Monitor live logs (JSON structured):
```bash
docker-compose logs -f litellm
```

### Database Migrations
Prisma migrations run automatically on startup (`USE_PRISMA_MIGRATE=true`).
To verify schema status:
```bash
docker-compose exec litellm prisma migrate status
```

---

## 🔐 Security & Hardening

This deployment enables several production hardening features by default in `config.yaml`:
*   **Alerting**: Thresholds set to 5 minutes (300s).
*   **Privacy**: PII/Prompts are redacted from exception logs.
*   **Governance**: Key generation restricted to Admins.
*   **Reliability**: Default fallbacks configured (`gpt-oss-120b-cloud`).
*   **Validation**: JSON Schema validation enabled for early request rejection.

---

## 📂 Architecture

*   **`config.yaml`**: Main configuration.
*   **`docker-compose.yml`**: Infrastructure definition.
*   **`schema.prisma`**: Database schema.
*   **`migrations/`**: SQL migrations.
*   **`docs/archive/`**: Legacy documentation and scripts (Reference only).
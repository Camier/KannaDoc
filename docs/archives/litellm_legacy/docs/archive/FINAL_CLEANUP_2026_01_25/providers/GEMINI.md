# LiteLLM Proxy Gateway

**Primary Documentation (SSOT):**
- `docs/OPERATIONAL_BASELINE.md`
- `docs/DOCKER_DEPLOYMENT.md`
- `docs/INDEX.md`

## Project Overview
This repo hosts a production-grade **LiteLLM Proxy Server** acting as a unified API gateway for multiple LLM providers (OpenAI, DeepSeek, Ollama, Hugging Face, etc.). **Models are defined in `config.yaml` (SSOT)**; Postgres stores keys/teams/spend.

**Key Technologies:**
- **Core**: LiteLLM (Python), PostgreSQL, Redis.
- **Orchestration**: Docker Compose (primary), `Justfile` (helpers).
- **Auxiliary Services**: Optional local rerank, optional TUI dashboard, Prometheus metrics.

## Quick Start (Docker)

```bash
# Full template (recommended)
cp .env.example .env

# Or minimal docker template
# cp .env.docker.example .env
vim .env
docker-compose up -d
docker-compose ps
curl http://localhost:4001/health/liveliness
```

## Configuration Workflow
1. **Edit**: Update `config.yaml` for routing/fallbacks/models.
2. **Secrets**: Update `.env` for credentials and ports.
3. **Restart**: `docker-compose restart litellm`.

## Common Operations
- **Logs**: `docker-compose logs -f litellm`
- **Restart all**: `docker-compose restart`
- **Health**: `curl http://localhost:4001/health/liveliness`

## Key Directories
- **`bin/`**: Operational scripts (seed, render, probe).
- **`docs/`**: Detailed runbooks and architecture docs.
- **`state/`**: Generated artifacts and runtime state.
- **`logs/`**: Runtime logs (if enabled).

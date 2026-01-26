# Operational Baseline (SSOT) - UPDATED 2026-01-22

This file keeps operational notes limited to **official LiteLLM documentation**. Local values are stored in repo files; see `config.yaml`, `.env`, and `docker-compose.yml`.

## Source of Truth (SSOT)
- **`config.yaml`** is the LiteLLM Proxy config file (models, routing, general settings). Official reference: https://docs.litellm.ai/docs/proxy/configs
- **Environment variables** supply secrets and connection details (e.g., `LITELLM_MASTER_KEY`, `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`). Official references:
  - Config reference: https://docs.litellm.ai/docs/proxy/configs
  - Caching reference: https://docs.litellm.ai/docs/proxy/prod#caching

## Health Endpoints (Official)
LiteLLM exposes health endpoints such as:
- `/health`
- `/health/liveliness`
- `/health/readiness`

Reference: https://docs.litellm.ai/docs/proxy/health

## Admin UI (Official)
- UI is served at `/ui` when a database is configured.
- Optional controls include `UI_USERNAME`, `UI_PASSWORD`, and `DISABLE_ADMIN_UI`.

Reference: https://docs.litellm.ai/docs/proxy/ui

## Virtual Keys (Official)
- Virtual keys require a database (`DATABASE_URL`) and a master key.
- The `/key/generate` route is protected by the master key.

Reference: https://docs.litellm.ai/docs/proxy/virtual_keys

## Caching (Official)
- Caching can be enabled in `config.yaml` via `litellm_settings.cache` with Redis-backed `cache_params`.

Reference: https://docs.litellm.ai/docs/proxy/prod#caching

## CLI (Official)
- The `litellm-proxy` CLI uses `LITELLM_PROXY_URL` and `LITELLM_PROXY_API_KEY`.

Reference: https://docs.litellm.ai/docs/proxy/management_cli

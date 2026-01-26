# LiteLLM Proxy Operations Guide

This guide keeps LiteLLM behavior statements limited to **official documentation**. Local values are defined in repo files (`config.yaml`, `.env`, `docker-compose.yml`).

## Official References
- Config reference: https://docs.litellm.ai/docs/proxy/configs
- OpenAI-compatible endpoints: https://docs.litellm.ai/docs/proxy/user_keys
- Health endpoints: https://docs.litellm.ai/docs/proxy/health
- Admin UI: https://docs.litellm.ai/docs/proxy/ui
- Virtual keys: https://docs.litellm.ai/docs/proxy/virtual_keys
- Caching: https://docs.litellm.ai/docs/proxy/prod#caching
- CLI: https://docs.litellm.ai/docs/proxy/management_cli

## OpenAI-Compatible Endpoints (Official)
Examples from official docs include:
- `/v1/chat/completions`
- `/v1/completions`
- `/v1/embeddings`
- `/v1/models`

Reference: https://docs.litellm.ai/docs/proxy/user_keys

## Health Endpoints (Official)
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
- `/key/generate` is protected by the master key.

Reference: https://docs.litellm.ai/docs/proxy/virtual_keys

## Caching (Official)
- Caching can be enabled in `config.yaml` via `litellm_settings.cache` with Redis-backed `cache_params`.

Reference: https://docs.litellm.ai/docs/proxy/prod#caching

## CLI (Official)
- The `litellm-proxy` CLI uses `LITELLM_PROXY_URL` and `LITELLM_PROXY_API_KEY`.

Reference: https://docs.litellm.ai/docs/proxy/management_cli

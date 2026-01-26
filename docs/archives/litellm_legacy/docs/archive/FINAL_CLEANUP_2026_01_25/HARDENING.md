# Hardening & Model Routing Notes

## Boundaries
- For local-only deployments, bind ports to `127.0.0.1` in `docker-compose.yml` (recommended). Otherwise, firewall exposed ports.
- Public routes: `/healthz`, `/readyz`, `/health/liveliness`, `/health/readiness`; `ui_access_mode=admin_only`.
- Secrets via `.env` + `~/.007`; `LITELLM_MODE=PRODUCTION` to disable load_dotenv.

## Logging/Privacy
- `disable_error_logs=true`, `disable_master_key_return=true`, `disable_adding_master_key_hash_to_db=true`.
- `health_check_details=false`, `json_logs=true`.

## DB / Config
- `DISABLE_SCHEMA_UPDATE=true` to avoid migration loops; SSOT details in `docs/OPERATIONAL_BASELINE.md`.
- Redis cache with password; TTL 600s for acompletion/aembedding.

## Routing & Availability
- Strategy `simple-shuffle`; `enable_pre_call_checks=true`, `allowed_fails=3`, `cooldown_time=30`.
- Fallbacks set for core groups (chat-default→qwen3-coder-480b-cloud, embeddings-default→local-embeddings, rerank-default→local-rerank, deepseek/llamacpp/vllm/tgi/gemma/qwen families).
- Context-window fallbacks for large models.
- Rerank served locally on 127.0.0.1:8079 (if enabled).
- Health app on 127.0.0.1:4001 when `SEPARATE_HEALTH_APP=1`.

## Tooling
- Callbacks: `ToolChoiceGuard` (coerce tool_choice=required→auto), `EarlyChunk` (first chunk for slow cloud models), `StreamGuard` (configurable, empty list), `dynamic_rate_limiter_v3` enabled.
- vLLM: tool_call_parser=hermes, auto tool choice on; max_model_len=4096; max_num_seqs=32; gpu util=0.2.

## Defaults for rate/budget (optional, applied via tooling)
- Keys: `rpm_limit=120`, `tpm_limit=60000` when generated programmatically.
- Teams: mirror key defaults; budgets optional.

## Per-model timeouts/retries (DB overrides)
- Local-ish (`vllm-qwen2.5-0.5b-instruct`, llamacpp-local, gemma3-1b-local, llama3.2-1b-local, local-embeddings, local-rerank): timeout=30, num_retries=1.
- Cloud/aliases (`%cloud%`, deepseek-*, chat-default, embeddings-default, rerank-default): timeout=90, num_retries=2.

## Operations
- Start/stop: `docker-compose up -d`, `docker-compose restart litellm`.
- Smoke: `bin/health_check.py` and `bin/probe_models.py`.

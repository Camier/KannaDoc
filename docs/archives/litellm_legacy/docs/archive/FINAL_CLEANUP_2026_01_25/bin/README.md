# `bin/` Scripts

This directory contains operational scripts for the local LiteLLM gateway, organized by function.

## `bin/db/` - Database Maintenance
Scripts for managing the Postgres DB-SSOT.
- `seed_db_config.py` – **Critical**: Pushes `config.yaml` changes to the DB.
- `backup_db.py` – Automated backups of DB + config files.
- `db_maintenance.py` – Core maintenance tasks (sanitization, cleanup).
- `ingest_native_pg.py` – Ingests local config files into the `pg-internal` vector store.
- `generate_and_ingest_state.py` – Snapshots DB state for RAG.

## `bin/monitor/` - Health & Compliance
Scripts for monitoring system health and configuration drift.
- `health_check.py` / `.sh` – Fast, blocking health probes (Redis + Proxy).
- `smoke_validate.py` – End-to-end validation (Auth, Chat, Embeddings, Tools).
- `audit_consistency.py` – Checks for drift between `config.yaml`, DB, and running processes.
- `compliance_check.py` – Enforces configuration policies (security, logging).
- `probe_capabilities.py` – Tests model capabilities (streaming, function calling) -> `docs/generated/MODEL_CAPABILITIES.md`.
- `metrics_exporter.py` – Prometheus metrics adapter.

## `bin/ops/` - Operations
Scripts for controlling services and runtime behavior.
- `start_vllm.sh` / `stop_vllm.sh` / `restart_vllm.sh` – Local inference control.
- `hot_reload.py` – Watches config for changes and triggers reload.
- `local_rerank_server.py` – Runs the FlashRank service.
- `maint.sh` – Wrapper for running maintenance tasks with the correct environment.
- `vllm_from_ai_hub.sh` – Adapter for shared vLLM installation.

## `bin/report/` - Reporting
Scripts for generating documentation and status reports.
- `render_config.py` – Generates `state/config.generated.yaml` from DB/Env.
- `model_inventory_report.py` – Generates `MODEL_INVENTORY_REPORT.md`.
- `hf_trending_inventory.py` / `hf_scout_models.py` – Hugging Face discovery tools.
# Repo Structure & Conventions

This repo runs a LiteLLM proxy. SSOT is defined in `docs/OPERATIONAL_BASELINE.md`.

## Architecture (high-level)
- **Proxy**: OpenAI-compatible gateway on `127.0.0.1:4000` (LiteLLM).
- **Health app**: separate health app on `127.0.0.1:4001` (when `SEPARATE_HEALTH_APP=1`).
- **Redis**: cache + router coordination (local).
- **Postgres**: keys/teams/spend and admin data (models live in `config.yaml`).

## Recommended Tree
```
/LAB/@litellm
  config.yaml                # Proxy config + model_list (SSOT)
  docker-compose.yml         # Primary deployment entrypoint
  .env.example               # Full env template
  .env.docker.example        # Minimal docker env template
  bin/
    ops/                     # Service control, hot reload
    tui/                     # Local dashboards / utilities
    health_check.py          # Health validation
    probe_models.py          # Model probes
    probe_capabilities.py    # Capability probes
    model_inventory_report.py
    backup_db_docker.py
  docs/                      # Runbooks and operational docs
    archive/                 # Historical reports
    generated/               # Generated docs (do not edit)
  state/                     # Runtime outputs + generated config
  logs/                      # Runtime logs
```

## Workflow
- **Edit**: `config.yaml` (router + general settings + models).
- **Restart**: proxy reloads config at startup.

## File Conventions
- **Python**: 4-space indent, `snake_case`.
- **Tests**: `tests/test_*.py` with fixtures under `tests/fixtures/`.
- **Generated**: `docs/generated/` and `state/` are generated; do not edit by hand.
  - `state/config.generated.yaml`: Runtime artifact. NOT source of truth.
  - `state/smoke_validate.latest.json`: Last smoke test result.
- **Secrets**: never commit to repo; use `~/.007`.

## Operational Commands
- Health check: `bin/health_check.py`
- Probe models: `bin/probe_models.py`
- Capability matrix: `bin/probe_capabilities.py --scope all --fetch-docs`

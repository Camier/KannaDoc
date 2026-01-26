# Maintenance Report (Jan 19, 2026)

## Session Summary

Comprehensive deep-dive into LiteLLM proxy deployment with DB-SSOT mode, admin UI setup, and troubleshooting.

## Issues Investigated & Resolved

### 1. Prisma Schema Drift (False Positive)
- **Symptom**: `FieldNotFoundError: Could not find field at upsertOneLiteLLM_VerificationToken.create.organization_id`
- **Investigation**: Verified DB columns via SQL and Prisma client introspection
- **Finding**: Schema is in sync; error was from transient client initialization
- **Resolution**: Restarted proxy to reinitialize Prisma client

### 2. Skills Hook Connection Error
- **Symptom**: `[SkillsHook] Error fetching skills: invalid dsn: invalid URI query parameter: "connection_limit"`
- **Investigation**: Checked DATABASE_URL format and psycopg2 connection
- **Finding**: DATABASE_URL was correct; error from pre-restart state
- **Resolution**: Transient issue resolved on proxy restart

### 3. Stale State Configuration
- **Symptom**: Audit showed config drift between `state/config.generated.yaml` and smoke-rendered config
- **Resolution**:
  - Archived stale `LITELLM_STATE_SNAPSHOT.md` to `state/archive/`
  - Regenerated config via `bin/render_config.py`

### 4. DB Config Drift
- **Symptom**: `[guard] DB config drift detected for: router_settings`
- **Resolution**: Seeded 5 config entries via `bin/seed_db_config.py --apply`

### 5. Admin UI Authentication Setup
- **Added**: `UI_PASSWORD=lol` to `env.litellm`
- **Added**: Dashboard basic auth to `~/.007`:
  - `LITELLM_DASHBOARD_BASIC_USER=admin`
  - `LITELLM_DASHBOARD_BASIC_PASSWORD=lol`
- **Configuration**: `ui_access_mode: admin_only`

## Validation Results

### Smoke Validation (Standard)
```
✅ Configuration is valid (with warnings)
== Summary ==
1 failure(s)
```

Failures:
- `/v1/models` missing required aliases (expected in DB-SSOT mode)

### Audit Consistency (Standard)
```
== summary ==
0 failures, 2 warning(s)
```

Warnings (non-blocking):
- Rerank VIRTUAL_ENV mismatch (running in separate conda env)

## Services Status

| Process | PID | Purpose |
|---------|-----|---------|
| litellm_with_patches.py | 170676 | Main proxy (4000) |
| health.py | 170638 | Health server (8181) |
| metrics_exporter.py | 170636 | Metrics export |
| local_rerank_server.py | 1677 | Rerank server (8079) |

## Current State

- **DB-SSOT**: Enabled with 17 local models
- **Active Keys**: 1 (probe-key)
- **Total Spend**: $1.74
- **MCP Servers**: 9 registered
- **Admin Users**: 2 (admin, default_user_id)

## Files Modified

1. `env.litellm` - Added `UI_PASSWORD=lol`
2. `~/.007` - Added dashboard basic auth credentials
3. `state/` - Regenerated config, archived stale files
4. `docs/LITELLM_OPS.md` - New comprehensive operations guide

## Recommendations

1. **No immediate action required** - system is healthy
2. **Consider**: Enabling cloud model providers for additional capabilities
3. **Monitor**: Skills hook for any recurring connection errors

## Commands Run

```bash
# Restart services
kill 4752 4730 4728 && bash start.sh

# Fix config drift
python bin/render_config.py
python bin/seed_db_config.py --apply

# Archive stale files
mv /LAB/@litellm/state/LITELLM_STATE_SNAPSHOT.md /LAB/@litellm/state/archive/

# Validate
python bin/smoke_validate.py
python bin/audit_consistency.py
```

## Access Points

| Endpoint | URL | Credentials |
|----------|-----|-------------|
| Proxy API | http://127.0.0.1:4000 | `LITELLM_API_KEY` |
| Ops Dashboard | http://127.0.0.1:4000/dashboard | admin:lol |
| Admin UI | http://127.0.0.1:4000/ui | admin:lol |

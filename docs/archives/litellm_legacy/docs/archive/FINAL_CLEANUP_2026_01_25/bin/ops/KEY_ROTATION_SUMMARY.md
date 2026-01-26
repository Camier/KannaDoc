# LiteLLM Master Key Rotation - Summary

## Deliverables

### 1. New Master Key (KEEP SECRET!)

```
MASTER KEY: <NEW_MASTER_KEY>
SALT KEY:   <NEW_SALT_KEY>
```

**Old key (to be replaced):** `<OLD_MASTER_KEY>`

### 2. Updated env.litellm

File: `/LAB/@litellm/env.litellm`

All hardcoded API keys have been removed and replaced with empty values that load from ~/.007:

```bash
DATABASE_URL=postgresql://miko:litellm@127.0.0.1:5434/litellm_db
# Master key - loaded from ~/.007 via systemd EnvironmentFile
LITELLM_MASTER_KEY=
LITELLM_SALT_KEY=
# Test keys - loaded from ~/.007
LITELLM_SMOKE_TEST_KEY=
LITELLM_HEALTH_API_KEY=
LITELLM_PROXY_API_KEY=
# Fallback keys - loaded from ~/.007
LLM_API_KEY=
EMBEDDING_API_KEY=
REDIS_PASSWORD=
```

### 3. Migration Scripts

#### Automated .007 Update
File: `/LAB/@litellm/bin/ops/update_007_keys.sh`

```bash
# Execute to update ~/.007
sudo /LAB/@litellm/bin/ops/update_007_keys.sh
```

#### Python Rotation Script
File: `/LAB/@litellm/bin/ops/rotate_master_key.py`

Full-featured rotation script with database updates.

### 4. Migration Steps

#### Step 1: Update ~/.007
```bash
/LAB/@litellm/bin/ops/update_007_keys.sh
```

Or manually:
```bash
export LITELLM_MASTER_KEY="<NEW_MASTER_KEY>"
export LITELLM_SALT_KEY="<NEW_SALT_KEY>"
export LITELLM_SMOKE_TEST_KEY="<NEW_MASTER_KEY>"
export LITELLM_HEALTH_API_KEY="<NEW_MASTER_KEY>"
export LITELLM_PROXY_API_KEY="<NEW_MASTER_KEY>"
```

#### Step 2: Update Database
```bash
psql postgresql://miko:litellm@127.0.0.1:5434/litellm_db << 'SQL'
UPDATE "LiteLLM_VerificationToken"
SET token = '<NEW_MASTER_KEY>',
    updated_at = NOW(),
    rotation_count = COALESCE(rotation_count, 0) + 1,
    last_rotation_at = NOW()
WHERE token = '<OLD_MASTER_KEY>';
SQL
```

#### Step 3: Restart Service
```bash
sudo systemctl restart litellm.service
sudo systemctl status litellm.service
```

#### Step 4: Verify
```bash
# Test health endpoint
curl -H 'Authorization: Bearer <NEW_MASTER_KEY>' \
     http://127.0.0.1:4000/healthz

# Test models endpoint
curl -H 'Authorization: Bearer <NEW_MASTER_KEY>' \
     http://127.0.0.1:4000/v1/models

# Check logs
sudo journalctl -u litellm.service -f
```

### 5. Service Restart Commands

```bash
# Standard restart
sudo systemctl restart litellm.service

# Check status
sudo systemctl status litellm.service

# View logs
sudo journalctl -u litellm.service -n 100 -f

# If issues occur, rollback
sudo systemctl stop litellm.service
# Restore old keys
sudo systemctl start litellm.service
```

### 6. Database Updates Required

Table: `LiteLLM_VerificationToken`

Current state:
```sql
token                     | key_name | key_alias | rotation_count
--------------------------+----------+-----------+---------------
<OLD_MASTER_KEY>...     |          |           |             0
```

After rotation:
```sql
token                     | key_name | key_alias | rotation_count | last_rotation_at
--------------------------+----------+-----------+----------------+------------------
<NEW_MASTER_KEY>...    |          |           |             1  | 2026-01-21...
```

### 7. Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `/LAB/@litellm/env.litellm` | Modified | Removed hardcoded keys |
| `/LAB/@litellm/bin/ops/rotate_master_key.py` | Created | Python rotation script |
| `/LAB/@litellm/bin/ops/update_007_keys.sh` | Created | Bash .007 update script |
| `/LAB/@litellm/bin/ops/KEY_ROTATION_RUNBOOK.md` | Created | Full runbook |
| `~/.007` | To Update | Add new master keys |

## Security Notes

1. The new master key is generated using Python's `secrets.token_urlsafe(32)`
2. Key format: `sk-` + 43 characters (256-bit entropy)
3. Keys are stored only in `~/.007` (user permissions: 600)
4. Database stores the token in `LiteLLM_VerificationToken.token`
5. No keys are committed to version control

## References

- LiteLLM Key Management: https://docs.litellm.ai/docs/proxy/auth
- Prisma Schema: `/LAB/@litellm/schema.prisma`
- Service Config: `/LAB/@litellm/systemd/litellm.service`

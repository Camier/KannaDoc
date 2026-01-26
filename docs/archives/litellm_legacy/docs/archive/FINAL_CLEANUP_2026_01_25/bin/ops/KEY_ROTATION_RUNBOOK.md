# LiteLLM Master Key Rotation Runbook

## Critical Information

**NEW MASTER KEY:** `sk-<NEW_MASTER_KEY>`
**NEW SALT KEY:** `sk-JZDc_5xh_0KM7EbN3OaD68KY82joaBMaiYYKHRbp2yI`
**OLD MASTER KEY:** `sk-4dYrydHnLdgy3zG5TuClyOUYKEmQTnTxT0t1dHfi0s`

> **SECURITY WARNING:** Keep the new keys secure! Do not commit to version control or share.

## Pre-Rotation Checklist

- [ ] Backup current database
- [ ] Verify service is healthy
- [ ] Schedule maintenance window (if applicable)
- [ ] Notify users of potential brief interruption

## Rotation Procedure

### Step 1: Update ~/.007 with New Keys

Run the automated script:

```bash
/LAB/@litellm/bin/ops/update_007_keys.sh
```

Or manually add to `~/.007`:

```bash
export LITELLM_MASTER_KEY="sk-<NEW_MASTER_KEY>"
export LITELLM_SALT_KEY="sk-JZDc_5xh_0KM7EbN3OaD68KY82joaBMaiYYKHRbp2yI"
export LITELLM_SMOKE_TEST_KEY="sk-<NEW_MASTER_KEY>"
export LITELLM_HEALTH_API_KEY="sk-<NEW_MASTER_KEY>"
export LITELLM_PROXY_API_KEY="sk-<NEW_MASTER_KEY>"
```

### Step 2: Update Database

Connect to PostgreSQL and update the verification token:

```bash
psql postgresql://miko:litellm@127.0.0.1:5434/litellm_db
```

Execute:

```sql
-- Verify old key exists
SELECT token, key_name, key_alias, created_at
FROM "LiteLLM_VerificationToken"
WHERE token = 'sk-4dYrydHnLdgy3zG5TuClyOUYKEmQTnTxT0t1dHfi0s';

-- Update the master key
UPDATE "LiteLLM_VerificationToken"
SET token = 'sk-<NEW_MASTER_KEY>',
    updated_at = NOW(),
    rotation_count = COALESCE(rotation_count, 0) + 1,
    last_rotation_at = NOW()
WHERE token = 'sk-4dYrydHnLdgy3zG5TuClyOUYKEmQTnTxT0t1dHfi0s';

-- Verify update
SELECT token, key_name, key_alias, rotation_count, last_rotation_at
FROM "LiteLLM_VerificationToken"
WHERE token = 'sk-<NEW_MASTER_KEY>';
```

### Step 3: Restart LiteLLM Service

```bash
# Stop the service
sudo systemctl stop litellm.service

# Wait for graceful shutdown (5 seconds)
sleep 5

# Start the service
sudo systemctl start litellm.service

# Verify it's running
sudo systemctl status litellm.service
```

### Step 4: Verify New Key

Test the new master key:

```bash
# Health check with new key
curl -H 'Authorization: Bearer sk-<NEW_MASTER_KEY>' \
     http://127.0.0.1:4000/healthz

# Model list with new key
curl -H 'Authorization: Bearer sk-<NEW_MASTER_KEY>' \
     http://127.0.0.1:4000/v1/models

# UI access
curl http://127.0.0.1:4000/ui/login
```

### Step 5: Check Logs

```bash
# Follow logs for errors
sudo journalctl -u litellm.service -f

# Check for startup issues
sudo journalctl -u litellm.service --since "5 minutes ago" | grep -i error
```

## Rollback Procedure

If rotation fails, restore the old key:

### 1. Restore ~/.007

```bash
cp ~/.007.backup.* ~/.007
```

### 2. Restore Database

```bash
psql postgresql://miko:litellm@127.0.0.1:5434/litellm_db
```

```sql
UPDATE "LiteLLM_VerificationToken"
SET token = 'sk-4dYrydHnLdgy3zG5TuClyOUYKEmQTnTxT0t1dHfi0s'
WHERE token = 'sk-<NEW_MASTER_KEY>';
```

### 3. Restart Service

```bash
sudo systemctl restart litellm.service
```

## Post-Rotation Tasks

- [ ] Update any external applications using the old key
- [ ] Update documentation with new key (if needed)
- [ ] Rotate any derived keys that used the old master
- [ ] Monitor service for 24 hours
- [ ] Document rotation in audit log

## Database Schema Reference

Key rotation affects the `LiteLLM_VerificationToken` table:

```sql
model LiteLLM_VerificationToken {
    token            String   @id
    key_name         String?
    key_alias        String?
    rotation_count   Int?     @default(0)
    last_rotation_at DateTime?
    created_at       DateTime? @default(now())
    updated_at       DateTime? @updatedAt
    ...
}
```

## Service Configuration Files

The following files reference the master key:

1. `/LAB/@litellm/env.litellm` - Environment configuration (now empty, loads from ~/.007)
2. `~/.007` - User secrets storage (updated with new keys)
3. `/LAB/@litellm/systemd/litellm.service` - systemd unit (loads from env.litellm)
4. PostgreSQL `LiteLLM_VerificationToken` table - Stores hashed tokens

## References

- [LiteLLM Key Management](https://docs.litellm.ai/docs/proxy/auth)
- [LiteLLM Proxy Configuration](https://docs.litellm.ai/docs/proxy/configs)
- Prisma Schema: `/LAB/@litellm/schema.prisma`

## Support

If issues occur during rotation:

1. Check logs: `sudo journalctl -u litellm.service -n 100`
2. Verify database: `psql postgresql://miko:litellm@127.0.0.1:5432/litellm_db -c "SELECT * FROM \"LiteLLM_VerificationToken\" LIMIT 5;"`
3. Verify environment: `systemctl show litellm.service | grep Environment`
4. Test connectivity: `curl -v http://127.0.0.1:4001/health/liveliness`

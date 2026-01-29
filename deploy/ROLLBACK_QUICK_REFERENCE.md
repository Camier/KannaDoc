# Rollback Quick Reference Guide

**Emergency Contact:** Use this guide when production issues require immediate action.

---

## EMERGENCY ROLLBACK (One Command)

```bash
cd /LAB/@thesis/layra && \
./deploy/rollback/emergency_rollback.sh <commit-hash>
```

Find commit hash: `git log --oneline -10`

---

## ROLLBACK DECISION MATRIX

### Rollback Immediately (RED ALERT)
- API Error Rate > 50% for 1 minute
- Health check fails for 2 consecutive checks
- Database connection pool exhausted
- Authentication failures > 90%
- Memory usage > 95%
- Any data corruption detected

### Investigate Within 5 Minutes (YELLOW ALERT)
- API Error Rate > 10% for 5 minutes
- Latency P95 > 5 seconds
- 3+ circuit breakers open
- User reports > 5 for same issue

### Monitor Only (GREEN)
- Latency increase < 3x baseline
- Queue lag < 1000 messages
- Single service restart needed

---

## ROLLBACK COMMANDS

### Full System Rollback
```bash
# Emergency full rollback
./deploy/rollback/emergency_rollback.sh abc1234

# Verify after rollback
./deploy/rollback/verify_rollback.sh
```

### Individual Service Rollback
```bash
# Rollback specific service
./deploy/rollback/service_rollback.sh backend v1.2.0

# Available services: backend, frontend, model-server, nginx
```

### Database Rollback
```bash
# MySQL
./deploy/rollback/db_rollback.sh mysql /tmp/mysql_backup.sql

# MongoDB
./deploy/rollback/db_rollback.sh mongodb /tmp/mongo_dump

# Redis
./deploy/rollback/db_rollback.sh redis /tmp/redis_dump.rdb
```

---

## PRE-MIGRATION CHECKLIST

Before any migration, ALWAYS:

```bash
# 1. Create backup
./deploy/scripts/backup.sh

# 2. Save commit hash
git rev-parse HEAD > /tmp/pre_migration_commit.txt

# 3. Start monitoring (in separate terminal)
./deploy/scripts/monitor_migration.sh

# 4. Then proceed with migration
```

---

## VERIFICATION AFTER ROLLBACK

```bash
# Run verification script
./deploy/rollback/verify_rollback.sh

# Manual checks
curl http://localhost:8090/api/v1/health/check
docker compose ps
docker compose logs backend --tail=50
```

---

## COMMON ROLLBACK SCENARIOS

### Scenario 1: Deployment Failed Mid-Deploy
```bash
# Stop deployment
docker compose down

# Restore previous state
git reset --hard $(cat /tmp/pre_migration_commit.txt)

# Restart
docker compose up -d

# Verify
./deploy/rollback/verify_rollback.sh
```

### Scenario 2: Database Migration Failed
```bash
# Stop backend
docker compose stop backend

# Restore database
./deploy/rollback/db_rollback.sh mysql /tmp/latest_mysql_backup.sql

# Revert code changes
git revert HEAD

# Restart
docker compose up -d backend
```

### Scenario 3: High Error Rate After Deploy
```bash
# Check logs first
docker compose logs backend --tail=100 | grep -i error

# If issues found, rollback
./deploy/rollback/service_rollback.sh backend

# Monitor
./deploy/scripts/monitor_migration.sh
```

### Scenario 4: Complete System Outage
```bash
# Use emergency rollback
./deploy/rollback/emergency_rollback.sh $(cat /tmp/pre_migration_commit.txt)

# If that fails, manual restore:
cd /LAB/@thesis/layra
git reset --hard <stable-commit>
docker compose down
docker compose up -d
```

---

## CRITICAL FILE LOCATIONS

```
/LAB/@thesis/layra/
├── deploy/
│   ├── ROLLBACK_STRATEGY.md          # Complete strategy document
│   ├── ROLLBACK_QUICK_REFERENCE.md   # This file
│   ├── rollback/
│   │   ├── emergency_rollback.sh     # Full system rollback
│   │   ├── service_rollback.sh       # Individual service
│   │   ├── db_rollback.sh            # Database restore
│   │   └── verify_rollback.sh        # Post-rollback checks
│   └── scripts/
│       ├── backup.sh                 # Pre-migration backup
│       └── monitor_migration.sh      # Real-time monitoring
```

---

## RECENT STABLE COMMITS

Check these for rollback targets:
```bash
git log --oneline -10
git tag -l "v*" | sort -V | tail -5
```

---

## CONTACT PROCEDURE

1. **Immediate (0-5 min):** Execute rollback, alert team
2. **Assessment (5-15 min):** Investigate root cause
3. **Resolution (15-60 min):** Fix and verify in staging
4. **Retest (60+ min):** Attempt migration again with fixes

---

## MONITORING DURING ROLLBACK

Open multiple terminals:

```bash
# Terminal 1: Logs
docker compose logs -f backend

# Terminal 2: Health
watch -n 2 'curl -s http://localhost:8090/api/v1/health/check | jq .'

# Terminal 3: Resources
watch -n 2 'docker stats --no-stream'

# Terminal 4: Errors
docker compose logs backend 2>&1 | grep -i error
```

---

## ESCALATION MATRIX

| Severity | Response Time | Action |
|----------|---------------|--------|
| SEV-0 (Complete outage) | Immediate | Emergency rollback |
| SEV-1 (Data corruption) | Immediate | Emergency rollback |
| SEV-2 (High error rate) | 5 min | Assess, likely rollback |
| SEV-3 (Performance) | 15 min | Investigate, monitor |
| SEV-4 (Minor issues) | 1 hour | Normal priority |

---

**Remember:** When in doubt, rollback first and investigate later. Data integrity > uptime.

**Documentation:** See `ROLLBACK_STRATEGY.md` for complete details.

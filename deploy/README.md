# Layra Deployment & Rollback Framework

Complete production-ready deployment and rollback strategy for the Layra repository migration.

---

## File Structure

```
/LAB/@thesis/layra/deploy/
├── README.md                       # This file - framework overview
├── ROLLBACK_STRATEGY.md            # Comprehensive rollback strategy (primary doc)
├── ROLLBACK_QUICK_REFERENCE.md     # Quick reference for emergencies
├── rollback/
│   ├── emergency_rollback.sh       # Full system rollback
│   ├── service_rollback.sh         # Individual service rollback
│   ├── db_rollback.sh              # Database restore
│   └── verify_rollback.sh          # Post-rollback verification
└── scripts/
    ├── backup.sh                   # Pre-migration backup
    └── monitor_migration.sh        # Real-time migration monitoring
```

---

## Quick Start

### Before Any Migration

```bash
# 1. Create backup
./deploy/scripts/backup.sh

# 2. Save current state
git rev-parse HEAD > /tmp/pre_migration_commit.txt

# 3. Start monitoring (in separate terminal)
./deploy/scripts/monitor_migration.sh
```

If your migration includes changing the Milvus topology (e.g., host/systemd Milvus -> docker-compose Milvus),
use the dedicated runbook to preserve collection schema/index parameters and aliases:
- `docs/operations/MILVUS_HOST_TO_DOCKER_MIGRATION.md`

### During Migration

Monitor the output from `monitor_migration.sh`. Watch for:
- Health check failures
- High latency (>2000ms)
- Error rates >10%
- Resource exhaustion

### If Issues Occur

```bash
# Immediate rollback
./deploy/rollback/emergency_rollback.sh $(cat /tmp/pre_migration_commit.txt)

# Verify rollback
./deploy/rollback/verify_rollback.sh
```

---

## Key Concepts

### Rollback Decision Matrix

| Condition | Threshold | Action |
|-----------|-----------|--------|
| API Error Rate | > 50% for 1 min | **IMMEDIATE ROLLBACK** |
| Health Check | Failed for 2 checks | **IMMEDIATE ROLLBACK** |
| Database Pool | > 95% used | **IMMEDIATE ROLLBACK** |
| Auth Failures | > 90% rate | **IMMEDIATE ROLLBACK** |
| Memory Usage | > 95% container | **IMMEDIATE ROLLBACK** |
| API Error Rate | > 10% for 5 min | **ASSESS** |
| Latency P95 | > 5 seconds | **ASSESS** |
| Circuit Breakers | > 3 open | **ASSESS** |

### Data Safety

- **MySQL:** Low risk with transactional backups
- **MongoDB:** Medium risk (no multi-document transactions)
- **Redis:** Zero risk (cache only, can be flushed)
- **Milvus:** High risk (requires volume snapshots)
- **Qdrant:** Medium risk (collection-level backups needed)

### Recovery Time Objectives

| Phase | Target | Actual |
|-------|--------|--------|
| Detection | < 1 min | |
| Decision | < 2 min | |
| Rollback Execution | < 5 min | |
| Verification | < 3 min | |
| **Total RTO** | **< 10 min** | |

---

## Workflow

### 1. Pre-Migration

```bash
# Checklist
- [ ] Create backup: ./deploy/scripts/backup.sh
- [ ] Save commit hash
- [ ] Start monitoring
- [ ] Inform team
- [ ] Schedule maintenance window (if needed)
```

### 2. Migration

```bash
# Execute migration
git pull
docker compose build
docker compose up -d

# Monitor continuously
# (monitor_migration.sh running in separate terminal)
```

### 3. Post-Migration Verification

```bash
# Run verification
./deploy/rollback/verify_rollback.sh

# Check application functionality
curl http://localhost:8090/api/v1/health/check
```

### 4. If Rollback Needed

```bash
# Emergency rollback
./deploy/rollback/emergency_rollback.sh <commit-hash>

# Or specific service
./deploy/rollback/service_rollback.sh backend

# Or specific database
./deploy/rollback/db_rollback.sh mysql /path/to/backup.sql
```

### 5. Post-Rollback

```bash
# Verification
./deploy/rollback/verify_rollback.sh

# Post-mortem
- Document root cause
- Update tests
- Improve monitoring
- Plan re-migration
```

---

## Rollback Methods

### Git Revert (Recommended)

```bash
# Safe - creates new commit
git revert <commit-hash> --no-commit
git commit -m "rollback: revert due to production issues"
docker compose up -d --build
```

### Git Reset (Emergency Only)

```bash
# WARNING: DANGEROUS
git reset --hard <stable-commit>
git push --force origin main
docker compose down && docker compose up -d
```

### Service Rollback (Zero-Downtime)

```bash
# Rollback specific service
./deploy/rollback/service_rollback.sh backend v1.2.0
```

### Database Rollback

```bash
# Restore from backup
./deploy/rollback/db_rollback.sh mysql /tmp/mysql_backup.sql
./deploy/rollback/db_rollback.sh mongodb /tmp/mongo_dump
```

---

## Monitoring

### Metrics to Watch

- **Health Check:** `http://localhost:8090/api/v1/health/check`
- **Prometheus:** `http://localhost:9090`
- **Grafana:** `http://localhost:3001`
- **Logs:** `docker compose logs -f backend`

### Alert Thresholds

See `/LAB/@thesis/layra/monitoring/alerts.yml` for complete alerting configuration.

---

## Testing

### Pre-Migration Testing

```bash
# In staging environment
./deploy/scripts/backup.sh
git checkout <migration-branch>
docker compose build
docker compose up -d
./deploy/rollback/verify_rollback.sh

# Test rollback
./deploy/rollback/emergency_rollback.sh <previous-commit>
./deploy/rollback/verify_rollback.sh
```

### Rollback Drills

Schedule quarterly rollback drills to:
- Verify rollback procedures work
- Train team on emergency procedures
- Measure actual RTO vs targets
- Identify process improvements

---

## Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| `ROLLBACK_STRATEGY.md` | Complete strategy reference | All engineers |
| `ROLLBACK_QUICK_REFERENCE.md` | Emergency quick reference | On-call engineers |
| `README.md` (this file) | Framework overview | All engineers |
| `monitoring/alerts.yml` | Alert definitions | DevOps/SRE |

---

## Support

### Emergency Contacts

| Role | Responsibility |
|------|----------------|
| On-Call Engineer | Execute rollback |
| Tech Lead | Approve rollback |
| DBA | Database rollback |
| DevOps | Infrastructure rollback |

### Escalation

1. **SEV-0** (Complete outage): Immediate rollback
2. **SEV-1** (Data corruption): Immediate rollback
3. **SEV-2** (High error rate): Assess, likely rollback
4. **SEV-3** (Performance): Investigate, monitor
5. **SEV-4** (Minor): Normal priority

---

## Best Practices

1. **Always create backup before migration**
2. **Test rollback procedures in staging**
3. **Monitor continuously during migration**
4. **When in doubt, rollback first**
5. **Document all incidents and post-mortems**
6. **Update this framework based on lessons learned**

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-27 | Initial rollback strategy |

---

**Remember:** Data integrity > uptime. When in doubt, rollback.

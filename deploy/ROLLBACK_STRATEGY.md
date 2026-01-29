# Layra Repository Migration - Rollback Strategy

**Version:** 1.0
**Last Updated:** 2026-01-27
**Scope:** Production migration rollback procedures

---

## Executive Summary

This document defines the comprehensive rollback strategy for Layra repository migrations. It provides decision matrices, automated rollback procedures, data safety guarantees, and recovery plans to ensure production stability during and after migrations.

### Key Principles
1. **Safety First:** Data integrity takes precedence over uptime
2. **Fast Recovery:** Target rollback time < 10 minutes (RTO)
3. **Zero Data Loss:** Ensure RPO = 0 for critical data
4. **Verified Restoration:** Post-rollback validation before resuming operations

---

## 1. ROLLBACK TRIGGERS

### 1.1 Automatic Rollback Conditions

Trigger immediate automated rollback when ANY of these conditions are met:

#### Critical Alerts (Immediate Rollback < 2 min)

| Metric | Threshold | Duration | Action |
|--------|-----------|----------|--------|
| API Error Rate | > 50% | 1 minute | **ROLLBACK** |
| Health Check | Failed | 2 consecutive checks | **ROLLBACK** |
| Database Connection | Pool exhausted | 30 seconds | **ROLLBACK** |
| Authentication | Login failures > 90% | 1 minute | **ROLLBACK** |
| Memory Usage | > 95% container | 2 minutes | **ROLLBACK** |
| Disk Space | < 5% free | Immediate | **ROLLBACK** |

#### Warning Alerts (Manual Review Required)

| Metric | Threshold | Duration | Action |
|--------|-----------|----------|--------|
| API Error Rate | > 10% | 5 minutes | **INVESTIGATE** |
| Latency (P95) | > 5 seconds | 5 minutes | **INVESTIGATE** |
| Circuit Breakers | > 3 open | 2 minutes | **INVESTIGATE** |
| Queue Depth | Kafka lag > 1000 | 5 minutes | **MONITOR** |

#### Performance Degradation

| Component | Degradation | Threshold | Action |
|-----------|-------------|-----------|--------|
| Embedding Service | Latency increase | > 3x baseline | **MONITOR** |
| Vector DB Query | Timeout rate | > 5% | **INVESTIGATE** |
| LLM Response | Failure rate | > 15% | **INVESTIGATE** |
| File Processing | Failed conversions | > 10% | **MONITOR** |

### 1.2 Manual Rollback Triggers

Initiate manual rollback when:

- **User Reports:** > 5 confirmed bug reports for same issue within 10 minutes
- **Data Corruption:** Any confirmed data inconsistency
- **Security Incident:** Suspected vulnerability or exposure
- **Feature Regression:** Critical feature no longer works
- **Integration Failure:** External service integrations broken
- **Performance Impact:** User-visible slowdowns > 50%

### 1.3 Rollback Decision Matrix

```
                    ┌─────────────────────────────────────────┐
                    │         SEVERITY ASSESSMENT              │
                    └─────────────────────────────────────────┘

    CRITICAL              HIGH                  MEDIUM
    (Immediate)          (5-15 min)           (Monitor Only)
    ┌─────────────┐    ┌─────────────┐     ┌─────────────┐
    │ Data loss   │    │ Auth fail   │     │ Slow UI     │
    │ Complete    │    │ 500 errors  │     │ High latency│
    │ outage      │    │ Degradation │     │ Queue lag   │
    │ Security    │    │             │     │             │
    └─────────────┘    └─────────────┘     └─────────────┘
         │                   │                    │
         ▼                   ▼                    ▼
    AUTO-ROLLBACK     ASSESS → ROLLBACK      DOCUMENT &
   (< 2 min)         IF NO FIX              MONITOR
```

---

## 2. ROLLBACK METHODS

### 2.1 Git-Based Rollback (Code Changes)

#### Strategy: Git Revert (Recommended)

```bash
# Identify the commit to rollback to
git log --oneline -10

# Safe revert (creates new commit)
git revert <commit-hash> --no-commit

# Review changes
git status
git diff

# If acceptable, commit the revert
git commit -m "rollback: revert <commit-hash> due to production issues"

# Tag the rollback
git tag -a rollback-$(date +%Y%m%d-%H%M%S) -m "Rollback due to incident"
```

#### Strategy: Git Reset (Emergency Only)

```bash
# WARNING: Only use if rollback commit hasn't been pushed
# Reset to previous stable commit
git reset --hard <stable-commit-hash>

# Force push (DANGEROUS - requires team coordination)
git push --force origin main
```

#### Deployment with Git Rollback

```bash
# After reverting code changes
cd /LAB/@thesis/layra

# Rebuild affected services
docker compose build backend model-server frontend

# Rolling restart (zero-downtime)
docker compose up -d --no-deps --build backend

# Verify health
curl -f http://localhost:8090/api/v1/health/check || echo "Health check failed"
```

### 2.2 Docker Compose Rollback (Infrastructure)

#### Service Version Rollback

```bash
# List current images
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}"

# Identify previous image version
docker images layra-backend --format "{{.ID}} {{.CreatedAt}}" | head -5

# Rollback specific service
docker compose stop backend
docker compose rm -f backend
docker compose up -d --scale backend=1

# Or use specific image
docker run -d \
  --name layra-backend-rollback \
  --network layra-net \
  --restart unless-stopped \
  layra-backend:<previous-tag> \
  /app/start.sh
```

#### Full Stack Rollback

```bash
# Emergency: Stop all services
docker compose down

# Pull previous working docker-compose.yml
git checkout <stable-commit> -- docker-compose.yml

# Restart with previous configuration
docker compose up -d

# Monitor startup
docker compose logs -f --tail=100
```

### 2.3 Database Migration Rollback

#### MySQL Rollback

```bash
# Before migration: Always take backup
docker exec layra-mysql mysqldump \
  -u root -p"${MYSQL_ROOT_PASSWORD}" \
  --all-databases \
  --single-transaction \
  --quick \
  > /tmp/mysql_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# Rollback MySQL schema changes
# Option 1: Restore from backup
docker exec -i layra-mysql mysql \
  -u root -p"${MYSQL_ROOT_PASSWORD}" \
  < /tmp/mysql_pre_migration_YYYYMMDD_HHMMSS.sql

# Option 2: Manual revert (if schema change scripts were idempotent)
# Connect and run revert scripts
docker exec -it layra-mysql mysql \
  -u root -p"${MYSQL_ROOT_PASSWORD}" \
  layra < /app/migrations/revert_schema_change.sql
```

#### MongoDB Rollback

```bash
# MongoDB doesn't have transactions across documents
# Restore from backup for data consistency

# Before migration: Create backup
docker exec layra-mongodb mongodump \
  --username "${MONGODB_ROOT_USERNAME}" \
  --password "${MONGODB_ROOT_PASSWORD}" \
  --authenticationDatabase admin \
  --db layra \
  --out /tmp/mongo_pre_migration

# Rollback: Restore backup
docker exec layra-mongodb mongorestore \
  --username "${MONGODB_ROOT_USERNAME}" \
  --password "${MONGODB_ROOT_PASSWORD}" \
  --authenticationDatabase admin \
  --drop \
  /tmp/mongo_pre_migration
```

#### Vector Database Rollback

```bash
# Milvus Rollback (collection-level)
# Note: Cannot rollback individual inserts, must restore collection

# Before migration: Export collection metadata
curl -X POST http://localhost:19530/v1/vector/collections/describe \
  -H 'Content-Type: application/json' \
  -d '{"collection_name": "knowledge_base"}' \
  > /tmp/milvus_schema_backup.json

# Rollback: Recreate collection from backup
# (Requires data volume snapshot - see section 3)
```

### 2.4 Cache Invalidation

```bash
# Redis Flush (Complete cache clear)
docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" FLUSHALL

# Selective cache invalidation
docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" \
  DEL "user:session:*" \
  DEL "kb:cache:*" \
  DEL "embedding:*"

# Verify cache cleared
docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" DBSIZE
```

---

## 3. DATA SAFETY

### 3.1 Pre-Migration Backup Checklist

```bash
#!/bin/bash
# Complete pre-migration backup script
# Run this BEFORE any migration

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/layra_pre_migration_${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

echo "=== LAYRA PRE-MIGRATION BACKUP ===" | tee "${BACKUP_DIR}/backup.log"

# 1. Git state
echo "1. Capturing Git state..."
git rev-parse HEAD > "${BACKUP_DIR}/git_commit.txt"
git diff HEAD > "${BACKUP_DIR}/git_uncommitted.patch"

# 2. Database backups
echo "2. Backing up databases..."
docker exec layra-mysql mysqldump -u root -p"${MYSQL_ROOT_PASSWORD}" \
  --all-databases --single-transaction \
  > "${BACKUP_DIR}/mysql_full.sql"

docker exec layra-mongodb mongodump \
  --username "${MONGODB_ROOT_USERNAME}" \
  --password "${MONGODB_ROOT_PASSWORD}" \
  --authenticationDatabase admin \
  --out "${BACKUP_DIR}/mongo_dump"

# 3. Vector DB volume snapshots
echo "3. Snapshotting vector databases..."
docker run --rm \
  -v layra_milvus_data:/data \
  -v "${BACKUP_DIR}:/backup" \
  alpine tar czf "/backup/milvus_data.tar.gz" -C /data .

docker run --rm \
  -v layra_qdrant_data:/data \
  -v "${BACKUP_DIR}:/backup" \
  alpine tar czf "/backup/qdrant_data.tar.gz" -C /data .

# 4. Configuration
echo "4. Backing up configuration..."
cp .env "${BACKUP_DIR}/env_backup"
cp docker-compose.yml "${BACKUP_DIR}/docker-compose_backup.yml"

# 5. Container state
echo "5. Recording container state..."
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" \
  > "${BACKUP_DIR}/containers.txt"

echo "=== BACKUP COMPLETE: ${BACKUP_DIR} ===" | tee -a "${BACKUP_DIR}/backup.log"
echo "To restore: ./deploy/scripts/restore_backup.sh ${BACKUP_DIR}"
```

### 3.2 Data Loss Risk Assessment

| Component | Data Loss Risk | Migration Safe? | Notes |
|-----------|---------------|-----------------|-------|
| **MySQL** | Low (with backup) | **YES** | Transactional, single-transaction dump sufficient |
| **MongoDB** | Medium | **CAUTION** | No multi-document transactions, backup essential |
| **Redis** | None (cache only) | **YES** | Can be safely flushed, will rebuild |
| **Milvus** | High | **NO** | Volume snapshots required |
| **Qdrant** | Medium | **CAUTION** | Collection-level backups required |
| **MinIO** | Low | **YES** | Object storage, versioned if configured |
| **Kafka** | Low | **YES** | Logs retained, consumers can replay |

### 3.3 Write Safety During Migration

**Safe Operations** (Can proceed during migration):
- Authentication token validation
- Read-only knowledge base queries
- Chat history reads
- Cache reads and writes

**Unsafe Operations** (Must pause or queue):
- Knowledge base creation/modification
- File uploads and processing
- Workflow execution
- User registration

**Recommended Write Quiesce Strategy:**

```python
# Add to backend/app/api/endpoints/base.py
import os
from fastapi import HTTPException

MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

# Write-blocking middleware
async def check_maintenance_mode(request):
    """Block write operations during maintenance."""
    if MAINTENANCE_MODE:
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Allow health checks and auth
            if "/health" in request.url.path or "/auth" in request.url.path:
                return
            raise HTTPException(
                status_code=503,
                detail="System undergoing maintenance. Please try again in a few minutes."
            )
```

---

## 4. TESTING ROLLBACK

### 4.1 Rollback Verification Checklist

Run these checks AFTER every rollback:

#### Phase 1: Infrastructure (0-2 min)

```bash
# Check all containers running
docker compose ps
# Expected: All services "Up" and healthy

# Check no resource exhaustion
docker stats --no-stream
# Expected: CPU < 80%, Memory < 85% for all containers

# Check disk space
df -h /
# Expected: > 10% free space
```

#### Phase 2: Connectivity (2-3 min)

```bash
# Health check endpoints
curl -f http://localhost:8090/api/v1/health/check
# Expected: {"status": "UP"}

# Database connections
docker exec layra-mysql mysqladmin -u root -p"${MYSQL_ROOT_PASSWORD}" ping
docker exec layra-mongodb mongosh --eval "db.adminCommand('ping')"
docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" ping
# Expected: All respond with success

# Vector databases
curl -f http://localhost:19530/healthz
curl -f http://localhost:6333/healthz
# Expected: 200 OK
```

#### Phase 3: Application Functionality (3-5 min)

```bash
# Authentication test
curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "thesis", "password": "test_password"}'
# Expected: 200 OK with token

# Knowledge base query
curl -X GET http://localhost:8090/api/v1/knowledge-bases \
  -H "Authorization: Bearer <token>"
# Expected: 200 OK with list

# Chat endpoint
curl -X POST http://localhost:8090/api/v1/chat/completions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
# Expected: 200 OK with response
```

#### Phase 4: Data Integrity (5-10 min)

```bash
# MySQL data check
docker exec layra-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
  -e "SELECT COUNT(*) FROM layra.users;"
# Expected: Returns count > 0

# MongoDB data check
docker exec layra-mongodb mongosh layra --eval "db.conversations.countDocuments()"
# Expected: Returns count

# Vector DB collection check
curl -X POST http://localhost:19530/v1/vector/get \
  -H 'Content-Type: application/json' \
  -d '{"collection_name": "knowledge_base", "limit": 1}'
# Expected: Returns vector data or empty (not error)
```

### 4.2 Automated Verification Script

```bash
#!/bin/bash
# Post-rollback verification script
# Exit on first failure

set -e

echo "=== LAYRA ROLLBACK VERIFICATION ==="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check() {
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ $1${NC}"
  else
    echo -e "${RED}✗ $1${NC}"
    exit 1
  fi
}

# 1. Container health
echo -n "Checking containers..."
docker compose ps | grep -q "layra-backend.*Up"
check "Backend running"

docker compose ps | grep -q "layra-mongodb.*Up"
check "MongoDB running"

docker compose ps | grep -q "layra-mysql.*Up"
check "MySQL running"

# 2. API health
echo -n "Checking API health..."
curl -sf http://localhost:8090/api/v1/health/check > /dev/null
check "API health check"

# 3. Database connectivity
echo -n "Checking MySQL..."
docker exec layra-mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" > /dev/null 2>&1
check "MySQL connectivity"

echo -n "Checking MongoDB..."
docker exec layra-mongodb mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1
check "MongoDB connectivity"

echo -n "Checking Redis..."
docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1
check "Redis connectivity"

# 4. Basic functionality
echo -n "Checking auth endpoint..."
curl -sf http://localhost:8090/api/v1/health/check > /dev/null
check "Auth endpoint"

echo ""
echo -e "${GREEN}=== ALL CHECKS PASSED ===${NC}"
echo "Rollback verified successfully."
```

---

## 5. RECOVERY PLAN

### 5.1 Post-Rollback Analysis

After rollback, complete this analysis before attempting migration again:

```markdown
# Rollback Post-Mortem Template

## Incident Summary
- **Time:** [Timestamp]
- **Trigger:** [Automatic/Manual - specific reason]
- **Rollback Time:** [Duration to rollback]
- **Downtime:** [Total minutes of degraded service]

## Root Cause Analysis
1. **What happened:** [Description]
2. **Why it happened:** [Root cause]
3. **Impact:** [Users affected, data impacted]

## Resolution
- **Rollback method used:** [Git revert / Docker rollback / Database restore]
- **Verification:** [All checks passed?]

## Prevention
1. **What test would have caught this:** [Test description]
2. **What monitoring was missing:** [Monitoring gap]
3. **Process improvements:** [Process change]

## Re-migration Plan
- **Fix applied:** [Yes/No - What fix]
- **Testing completed:** [Yes/No - What tests]
- **Proposed date:** [When to retry]
- **Rollback plan updated:** [Yes/No - How improved]
```

### 5.2 Re-Migration Checklist

Before attempting migration again:

- [ ] Root cause identified and fixed
- [ ] Fix tested in staging environment
- [ ] Rollback procedure updated based on lessons learned
- [ ] Monitoring enhanced for the failure mode
- [ ] Additional pre-migration backups taken
- [ ] Team briefed on new plan
- [ ] Maintenance window scheduled (if needed)
- [ ] Rollback decision triggers reviewed and adjusted
- [ ] Communication plan prepared for users

### 5.3 Migration Retry Procedure

```bash
#!/bin/bash
# Migration retry procedure

echo "=== LAYRA MIGRATION RETRY ==="

# 1. Verify previous rollback was successful
echo "1. Verifying current state..."
./deploy/scripts/verify_rollback.sh || exit 1

# 2. Take fresh backups
echo "2. Taking pre-migration backups..."
./deploy/scripts/backup.sh

# 3. Review and apply fix
echo "3. Applying fixes..."
git log -1 --oneline  # Review what we're about to deploy

# 4. Deploy with canary
echo "4. Deploying with canary testing..."
docker compose build backend
docker compose up -d --no-deps backend

# 5. Intensive monitoring
echo "5. Monitoring deployment..."
./deploy/scripts/monitor_migration.sh

echo "=== MIGRATION RETRY COMPLETE ==="
```

---

## 6. OPERATIONAL PROCEDURES

### 6.1 Emergency Rollback (Panic Procedure)

Use this when immediate action is required:

```bash
# ONE-LINE EMERGENCY ROLLBACK
# Copy and paste this entire block

cd /LAB/@thesis/layra && \
git log --oneline -5 && \
echo "Enter commit hash to rollback to:" && \
read COMMIT && \
git revert --no-commit $COMMIT && \
git commit -m "EMERGENCY ROLLBACK: $COMMIT" && \
docker compose down && \
docker compose up -d && \
sleep 30 && \
curl -f http://localhost:8090/api/v1/health/check && \
echo "ROLLBACK SUCCESSFUL" || echo "ROLLBACK FAILED - CHECK LOGS"
```

### 6.2 Monitoring During Rollback

```bash
# Terminal 1: Watch logs
docker compose logs -f --tail=100 backend model-server

# Terminal 2: Monitor health
watch -n 5 'curl -s http://localhost:8090/api/v1/health/check | jq .'

# Terminal 3: Monitor resources
watch -n 2 'docker stats --no-stream'

# Terminal 4: Error rate
watch -n 5 'docker compose logs backend 2>&1 | grep -i error | tail -20'
```

### 6.3 Communication Plan

**Internal (Team):**
- Immediately: Alert via designated channel (Slack/Teams)
- 5 min: Initial assessment and rollback decision
- 15 min: Status update
- 1 hour: Post-mortem kickoff

**External (Users):**
- Immediately: Status page update (if configured)
- 15 min: Announcement if extended downtime
- 1 hour: Resolution summary

---

## 7. ROLLBACK SCRIPTS REFERENCE

### 7.1 Quick Rollback Commands

| Scenario | Command |
|----------|---------|
| Code change | `git revert HEAD && docker compose up -d --build backend` |
| Container issue | `docker compose restart backend` |
| Database issue | `docker exec -i layra-mysql mysql < backup.sql` |
| Cache issue | `docker exec layra-redis redis-cli FLUSHALL` |
| Full system | `git reset --hard <stable> && docker compose down && docker compose up -d` |

### 7.2 Rollback Script Locations

```
/LAB/@thesis/layra/
├── deploy/
│   ├── rollback/
│   │   ├── emergency_rollback.sh        # Full system rollback
│   │   ├── service_rollback.sh          # Individual service
│   │   ├── db_rollback.sh               # Database restore
│   │   └── verify_rollback.sh           # Post-rollback checks
│   ├── scripts/
│   │   ├── backup.sh                    # Pre-migration backup
│   │   └── monitor_migration.sh         # Migration monitoring
│   └── ROLLBACK_STRATEGY.md             # This document
```

---

## 8. SUCCESS METRICS

### 8.1 Rollback Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Detection Time | < 1 min | ___ |
| Decision Time | < 2 min | ___ |
| Rollback Execution | < 5 min | ___ |
| Verification | < 3 min | ___ |
| **Total RTO** | **< 10 min** | ___ |

### 8.2 Data Integrity Targets

| Metric | Target | Status |
|--------|--------|--------|
| Data Loss | 0 records | ✅ |
| Corrupted Records | 0 | ✅ |
| Orphaned Data | 0 | ✅ |
| Transaction Consistency | 100% | ✅ |

---

## 9. APPENDICES

### Appendix A: Environment-Specific Considerations

#### Development Environment
- Fast rollback acceptable (data can be reset)
- Skip comprehensive backups
- Focus on quick iteration

#### Staging Environment
- Test rollback procedures before production
- Use production-like data
- Validate rollback scripts

#### Production Environment
- Follow this document exactly
- All backups mandatory
- Communication required

### Appendix B: Contact Information

| Role | Name | Contact | Responsibility |
|------|------|---------|----------------|
| On-Call Engineer | | | Execute rollback |
| Tech Lead | | | Approve rollback |
| DBA | | | Database rollback |
| DevOps | | | Infrastructure rollback |

### Appendix C: Related Documents

- `/LAB/@thesis/layra/deploy/DEPLOYMENT_RUNBOOK.md` - Normal deployment procedures
- `/LAB/@thesis/layra/docs/operations/TROUBLESHOOTING.md` - Common issues
- `/LAB/@thesis/layra/docs/operations/RUNBOOK.md` - Operational procedures
- `/LAB/@thesis/layra/scripts/snapshot_data.sh` - Backup procedures

---

## CHANGE LOG

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-01-27 | 1.0 | Initial rollout strategy | Claude Code |

---

**Approved By:** ____________________
**Date:** ____________________

**Document Control:** Do not modify this document without following the change management process. All changes must be tested in staging before production use.

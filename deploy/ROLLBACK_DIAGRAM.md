# Rollback Strategy Visual Guide

## Emergency Rollback Flow

```
                    ┌─────────────────────────────────────┐
                    │     PRODUCTION INCIDENT DETECTED     │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │      ASSESS SEVERITY (30 seconds)    │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐                  ┌───────▼────────┐
            │ CRITICAL       │                  │ NON-CRITICAL   │
            │ (Immediate)    │                  │ (Investigate)  │
            │                │                  │                │
            │ • 50% errors   │                  │ • 10% errors   │
            │ • Health down  │                  │ • High latency │
            │ • Data loss    │                  │ • Slow UI      │
            └───────┬────────┘                  └───────┬────────┘
                    │                                   │
                    ▼                                   ▼
            ┌───────────────┐                 ┌───────────────┐
            │ DECISION:     │                 │ INVESTIGATE   │
            │ ROLLBACK?     │                 │ 5 MINUTES     │
            │               │                 └───────┬───────┘
            │ [YES] ────────┼───────►                 │
            │                       │                   ▼
            │ [NO] ─────────►       │         ┌───────────────┐
            │                       │         │ STILL BAD?    │
            └───────┬───────────────┘         └───────┬───────┘
                    │                               │
            ┌───────▼────────┶───────────────┐     │
            │                                   │     │
        YES │                               NO │     │
            │                                   │     │
            ▼                                   ▼     │
    ┌───────────────┐                   ┌───────────────┐
    │ EXECUTE       │                   │ CONTINUE      │
    │ ROLLBACK      │                   │ MONITORING    │
    │ (< 5 min)     │                   └───────────────┘
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ VERIFY        │
    │ ROLLBACK      │
    │ (< 3 min)     │
    └───────┬───────┘
            │
    ┌───────┴────────┶───────────────┐
    │                               │
SUCCESS │                       FAILURE │
    │                               │
    ▼                               ▼
┌───────────────┐           ┌───────────────┐
│ RESUME        │           │ MANUAL        │
│ OPERATIONS    │           │ INTERVENTION  │
└───────────────┘           └───────────────┘
```

---

## Component Rollback Decision Tree

```
                    ┌─────────────────────────────────┐
                    │  ISSUE DETECTED IN PRODUCTION  │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼────────┐           ┌──────────▼──────────┐
            │ SINGLE SERVICE │           │ MULTIPLE SERVICES   │
            │ ISSUE?         │           │ OR FULL SYSTEM?     │
            └───────┬────────┘           └──────────┬──────────┘
                    │                               │
            ┌───────┴────────┐           ┌──────────┴──────────┐
            │                │           │                     │
      YES  │            NO  │      YES  │                 NO  │
            │                │           │                     │
            ▼                ▼           ▼                     ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │ SERVICE       │ │ DATABASE      │ │ FULL SYSTEM   │ │ DATA CORRUPTION│
    │ ROLLBACK      │ │ ROLLBACK      │ │ ROLLBACK      │ │ EMERGENCY     │
    │               │ │               │ │               │ │               │
    │ ./rollback/   │ │ ./rollback/   │ │ ./rollback/   │ │ ./rollback/   │
    │ service_*.sh  │ │ db_*.sh       │ │ emergency*.sh │ │ emergency*.sh │
    └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
```

---

## Pre-Migration Checklist Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PRE-MIGRATION CHECKLIST                             │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ 1. BACKUP
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ [ ] Create full system backup                                               │
│     Command: ./deploy/scripts/backup.sh                                     │
│     Verify: Check backup directory created and has size                     │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ 2. SAVE STATE
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ [ ] Save current commit hash                                                 │
│     Command: git rev-parse HEAD > /tmp/pre_migration_commit.txt             │
│     Verify: File contains commit hash                                       │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ 3. START MONITORING
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ [ ] Start monitoring in separate terminal                                   │
│     Command: ./deploy/scripts/monitor_migration.sh                          │
│     Verify: Seeing health checks every 5 seconds                           │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ 4. NOTIFY TEAM
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ [ ] Alert team of upcoming migration                                        │
│ [ ] Confirm on-call engineer available                                      │
│ [ ] Document expected changes and potential impact                         │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ 5. STAGING TEST
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ [ ] Test migration in staging environment                                   │
│ [ ] Verify all health checks pass                                          │
│ [ ] Test rollback procedure in staging                                     │
└─────────────────────────────────────────────────────────────────────────────┘
      │
      │ ALL CHECKED?
      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PROCEED WITH MIGRATION                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Rollback Verification Flow

```
                    ┌─────────────────────────────────────┐
                    │      ROLLBACK COMPLETED             │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │   PHASE 1: INFRASTRUCTURE (0-2 min) │
                    ├─────────────────────────────────────┤
                    │ [ ] All containers running           │
                    │ [ ] No resource exhaustion           │
                    │ [ ] Disk space > 10%                 │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │   PHASE 2: CONNECTIVITY (2-3 min)   │
                    ├─────────────────────────────────────┤
                    │ [ ] Health check endpoint            │
                    │ [ ] Database connections             │
                    │ [ ] Vector databases                 │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │   PHASE 3: FUNCTIONALITY (3-5 min)  │
                    ├─────────────────────────────────────┤
                    │ [ ] Authentication working           │
                    │ [ ] Knowledge base queries           │
                    │ [ ] Chat endpoint responding         │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │   PHASE 4: DATA INTEGRITY (5-10 min)│
                    ├─────────────────────────────────────┤
                    │ [ ] MySQL data count matches         │
                    │ [ ] MongoDB data count matches       │
                    │ [ ] Vector DB collections intact     │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              PASS │                               FAIL │
                    │                                   │
                    ▼                                   ▼
          ┌───────────────┐                   ┌───────────────┐
          │ VERIFICATION  │                   │ INVESTIGATE   │
          │ SUCCESSFUL    │                   │ FAILURE       │
          │               │                   │               │
          │ Resume normal │                   │ Check logs    │
          │ operations    │                   │ Manual fix    │
          │ Document      │                   │ Consider      │
          │ post-mortem   │                   │ re-rollback   │
          └───────────────┘                   └───────────────┘
```

---

## Data Safety Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LOSS RISK ASSESSMENT                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOW RISK (Safe to migrate)                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ • MySQL (with single-transaction backup)                            │  │
│  │ • Redis (can be flushed, cache rebuilds)                            │  │
│  │ • MinIO (object storage, versioned if configured)                   │  │
│  │ • Kafka (logs retained, consumers can replay)                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  MEDIUM RISK (Backup required)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ • MongoDB (no multi-document transactions)                          │  │
│  │ • Qdrant (collection-level backups needed)                          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  HIGH RISK (Volume snapshot required)                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ • Milvus (requires volume snapshots)                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Timeline: Typical Migration with Rollback

```
T = -30 min    PREPARATION
               ├─ Create backup
               ├─ Save state
               └─ Start monitoring

T = 0 min      MIGRATION START
               ├─ Deploy new code
               └─ Monitor closely

T = +5 min     EARLY CHECKS
               ├─ Health checks
               ├─ Error rates
               └─ Resource usage

T = +10 min    ISSUE DETECTED!
               ├─ Error rate > 50%
               └─ Trigger rollback decision

T = +12 min    ROLLBACK DECISION
               ├─ Assess severity
               └─ Initiate rollback

T = +17 min    ROLLBACK COMPLETE
               ├─ Services restored
               └─ Health checks passing

T = +20 min    VERIFICATION COMPLETE
               ├─ All checks pass
               └─ Resume operations

T = +60 min    POST-MORTEM
               ├─ Root cause analysis
               ├─ Documentation
               └─ Re-migration plan

TOTAL DOWNTIME: ~10 minutes (within RTO target)
```

---

## Command Reference Card

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EMERGENCY COMMANDS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  One-Line Emergency Rollback:                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ ./deploy/rollback/emergency_rollback.sh <commit-hash>               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  Quick Health Check:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ curl http://localhost:8090/api/v1/health/check                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  Check Recent Commits:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ git log --oneline -10                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  Monitor Logs:                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ docker compose logs -f backend                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Contact Flow for Incidents

```
                    ┌─────────────────────────────────────┐
                    │     INCIDENT DETECTED                │
                    └─────────────────┬───────────────────┘
                                      │
                    T = 0 min         ▼
                    ┌─────────────────────────────────────┐
                    │  ALERT: On-Call Engineer             │
                    │  • Immediate assessment             │
                    │  • Check monitoring dashboards       │
                    │  • Verify issue severity            │
                    └─────────────────┬───────────────────┘
                                      │
                    T = 2 min         ▼
                    ┌─────────────────────────────────────┐
                    │  CRITICAL?                           │
                    │  • YES → Execute rollback            │
                    │  • NO → Continue investigation        │
                    └─────────────────┬───────────────────┘
                                      │
                    T = 5 min         ▼
                    ┌─────────────────────────────────────┐
                    │  ALERT: Tech Lead                    │
                    │  • Status update                    │
                    │  • Escalation if needed             │
                    └─────────────────┬───────────────────┘
                                      │
                    T = 15 min        ▼
                    ┌─────────────────────────────────────┐
                    │  ASSESSMENT COMPLETE                 │
                    │  • Root cause identified?           │
                    │  • Fix developed?                   │
                    │  • Rollback successful?             │
                    └─────────────────┬───────────────────┘
                                      │
                    T = 60 min        ▼
                    ┌─────────────────────────────────────┐
                    │  POST-MORTEM                         │
                    │  • Document incident                │
                    │  • Update procedures                │
                    │  • Plan re-migration                │
                    └─────────────────────────────────────┘
```

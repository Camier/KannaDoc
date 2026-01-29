# LAYRA Documentation Consolidation Plan

> **Date:** 2026-01-29
> **Goal:** Reduce 207 docs to ~30 essential files

## Consolidation Strategy

### 1. Archive Old Reports (122 → ~20)
**Move to:** `docs/archives/reports/2026-01/`

| File | Action | Destination |
|------|--------|-------------|
| CODEBASE_AUDIT_REPORT.md | Archive | archives/reports/2026-01/ |
| COMPLETION_SUMMARY.md | Archive | archives/reports/2026-01/ |
| COMPLEXITY_ANALYSIS_* | Merge & Archive | archives/reports/2026-01/ |
| COMPREHENSIVE_TECHNICAL_DEBT_REPORT.md | Archive | archives/reports/2026-01/ |
| MCP_CONFIG_* | Merge & Archive | archives/reports/2026-01/ |
| PHASE_0_1_* | Merge & Archive | archives/reports/2026-01/ |
| PHASE_1_* | Merge & Archive | archives/reports/2026-01/ |

### 2. Consolidate Duplicate Topics (34 → ~5)

| Topic | Files | Keep | Merge To |
|-------|-------|------|---------|
| Database | DATABASE_*.md | DATABASE_QUICK_REFERENCE.md | core/DATABASE.md |
| Data Flow | DATA_FLOW_*.md | DATA_FLOW_QUICK_REFERENCE.md | core/ |
| Remediation | FINAL_REMEDIATION_*, REMEDIATION_COMPLETE_* | REMEDIATION_SESSION_2026-01-29.md | archives/ |

### 3. Keep Essential Docs (15 files)

**Root Level:**
- `INDEX.md` - Main documentation index
- `README.md` - Project README (in root, not docs/)
- `SSOT_CLEAN.md` - Keep for reference

**SSOT** (Single Source of Truth):
- `ssot/stack.md` - ⭐ Primary reference
- `ssot/QUICK_REF.md` - Quick reference card
- `ssot/CREDENTIALS.md` - Credentials management
- `ssot/README.md` - SSOT index

**Core** (Essential docs):
- `core/CONFIGURATION.md` - Configuration guide
- `core/API.md` - API documentation
- `core/DATABASE.md` - Database schema
- `core/EMBEDDINGS.md` - Embedding models
- `core/WORKFLOW_ENGINE.md` - Workflow guide

**Guides:**
- `guides/COLQWEN_SETUP.md`
- `guides/MILVUS_INGESTION.md`
- `guides/GPU_OPTIMIZATION.md`

**Operations:**
- `operations/RUNBOOK.md`
- `operations/DEPLOYMENT_DIAGRAM.md`
- `operations/TROUBLESHOOTING.md`

**Getting Started:**
- `getting-started/START_HERE.md`
- `getting-started/QUICKSTART.md`

## Commands to Execute

```bash
# 1. Create archive directories
mkdir -p docs/archives/reports/2026-01

# 2. Move old reports to archives
mv docs/CODEBASE_AUDIT_REPORT.md docs/archives/reports/2026-01/
mv docs/COMPLETION_SUMMARY.md docs/archives/reports/2026-01/
mv docs/COMPLEXITY_ANALYSIS_DETAILED.md docs/archives/reports/2026-01/
mv docs/COMPLEXITY_ANALYSIS_SUMMARY.md docs/archives/reports/2026-01/
mv docs/COMPREHENSIVE_TECHNICAL_DEBT_REPORT.md docs/archives/reports/2026-01/

# 3. Consolidate MCP config docs
mv docs/MCP_CONFIG_ANALYSIS_SUMMARY.md docs/archives/reports/2026-01/
mv docs/MCP_CONFIG_COMMIT_MESSAGE.md docs/archives/reports/2026-01/
mv docs/MCP_CONFIG_DUPLICATION_ANALYSIS.md docs/archives/reports/2026-01/
mv docs/MCP_CONFIG_FINAL_REPORT.md docs/archives/reports/2026-01/
mv docs/MCP_CONFIG_README.md docs/archives/reports/2026-01/

# 4. Consolidate PHASE docs
mv docs/PHASE_0_1_FINAL_STATUS.md docs/archives/reports/2026-01/
mv docs/PHASE_0_1_IMPLEMENTATION_SUMMARY.md docs/archives/reports/2026-01/
mv docs/PHASE_0_1_PROGRESS_UPDATE.md docs/archives/reports/2026-01/
mv docs/PHASE_0_1_SUCCESS_SUMMARY.md docs/archives/reports/2026-01/
mv docs/PHASE_1_MIGRATION_GUIDE.md docs/archives/reports/2026-01/
mv docs/PHASE_1_MIGRATION_ROADMAP.md docs/archives/reports/2026-01/
mv docs/PHASE_1_STATUS_CLARIFICATION.md docs/archives/reports/2026-01/

# 5. Consolidate remediation docs
mv docs/FINAL_REMEDIATION_SUMMARY.md docs/archives/reports/2026-01/
mv docs/REMEDIATION_COMPLETE_SUMMARY.md docs/archives/reports/2026-01/
mv docs/CONSOLIDATION_COMPLETE.md docs/archives/reports/2026-01/

# 6. Move detailed analysis to archives (keep quick refs)
mv docs/DATA_FLOW_ANALYSIS.md docs/archives/reports/2026-01/
mv docs/DATA_FLOW_DIAGRAMS.md docs/archives/reports/2026-01/
mv docs/DATABASE_SCHEMA_ANALYSIS.md docs/archives/reports/2026-01/
mv docs/DATABASE_INDEX_OPTIMIZATION.md docs/archives/reports/2026-01/

# 7. Move other archived content
mv docs/IMPLEMENTATION_PLAN.md docs/archives/reports/2026-01/
mv docs/LLM_PROVIDER_CONFIGURATION_SUMMARY.md docs/archives/reports/2026-01/
mv docs/REFACTORING_MASTER_PLAN.md docs/archives/reports/2026-01/
mv docs/CONDITIONAL_GATE_PATTERNS.md docs/archives/guides/

# 8. Keep REMEDIATION_SESSION_2026-01-29.md in root (latest)
```

## Result: ~30 Essential Files

- Root: 3 files (INDEX, SSOT_CLEAN, latest session)
- SSOT: 4 files
- Core: 5 files
- Guides: 4 files
- Operations: 3 files
- Getting Started: 2 files
- Archives: ~122 files (preserved)

## Next Steps

1. Execute consolidation commands
2. Update INDEX.md with new structure
3. Create docs/archives/README.md as archive index

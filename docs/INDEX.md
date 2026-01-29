# Layra Documentation Index

**Last Updated:** 2026-01-29
**Version:** 2.2.0 (Post-Consolidation)

> 🎯 **START HERE** if you're new to Layra
> 📉 **Reduced from 207 to ~50 essential documents**

---

## 📍 Latest Updates (2026-01-29)

**Session Remediation Report:** [REMEDIATION_SESSION_2026-01-29.md](REMEDIATION_SESSION_2026-01-29.md)
- Fixed MongoDB schema drift (model_config collection)
- Fixed SSE endpoint bug (message_id parameter)
- Added ZhipuAI Coding Plan provider (glm-4.5, glm-4.6, glm-4.7)

---

## ⭐ Single Source of Truth (SSOT)

**Before consulting any other documentation, read this:**

### 📘 [Stack SSOT](ssot/stack.md) - PRIMARY REFERENCE

The authoritative document for:
- Complete system state (all 13 services)
- Architecture decisions & rationale (ADRs)
- Service dependencies & data flows
- Environment configuration (all variables)
- Resource requirements & usage
- Deployment procedures
- Known issues & limitations
- Version history & migrations

### 📄 [Quick Reference Card](ssot/QUICK_REF.md)

One-page cheat sheet for:
- Common Docker commands
- Service ports & access
- Quick fixes for common issues
- Critical environment variables

**Policy:** ANY architectural change MUST be reflected in the SSOT first.

---

## 📍 Quick Navigation

**Current KB State (miko):** See [RUNBOOK](operations/RUNBOOK.md#kb-state-miko) → "Etat reel".

### Getting Started
| Document | Description |
|----------|-------------|
| [QUICKSTART](getting-started/QUICKSTART.md) | Deploy Layra in 5 minutes |
| [START_HERE](getting-started/START_HERE.md) | New user onboarding guide |
| [README](getting-started/README.md) | Project overview |
| [README_zh](getting-started/README_zh.md) | Chinese overview |

### Core Documentation
| Document | Description |
|----------|-------------|
| [CONFIGURATION](core/CONFIGURATION.md) | Configuration guide and deployment scenarios |
| [ENVIRONMENT VARIABLES](reference/ENVIRONMENT_VARIABLES.md) | Complete .env reference (all variables) |
| [API](core/API.md) | REST API reference |
| [DATABASE](core/DATABASE.md) | Database schemas (MongoDB, MySQL, Milvus, Redis) |
| [EMBEDDINGS](core/EMBEDDINGS.md) | Embedding pipeline (ColQwen/Jina) |
| [Vector DB Overview](core/vector_db/OVERVIEW.md) | Vector DB abstraction (Milvus/Qdrant) |
| [WORKFLOW ENGINE](core/WORKFLOW_ENGINE.md) | Workflow execution, fault tolerance, recovery |

### Architecture
| Document | Description |
|----------|-------------|
| [DEEP_ANALYSIS](architecture/DEEP_ANALYSIS.md) | Comprehensive architecture deep-dive |
| [REPO_MAP](architecture/REPO_MAP.md) | Codebase structure guide |
| [ANTI_COMPLEXITY](architecture/ANTI_COMPLEXITY.md) | Complexity prevention guidelines |

### Operations
| Document | Description |
|----------|-------------|
| [RUNBOOK](operations/RUNBOOK.md) | Clean restart procedures |
| [DEPLOYMENT_DIAGRAM](operations/DEPLOYMENT_DIAGRAM.md) | Minimal deployment topology (Mermaid) |
| [CHANGE_LOG](operations/CHANGE_LOG.md) | Version history & changes |
| [TROUBLESHOOTING](operations/TROUBLESHOOTING.md) | Troubleshooting guide & incident reports |

### Guides
| Document | Description |
|----------|-------------|
| [COLQWEN_SETUP](guides/COLQWEN_SETUP.md) | ColQwen embedding model setup |
| [GPU_OPTIMIZATION](guides/GPU_OPTIMIZATION.md) | GPU performance tuning |
| [MILVUS_OPTIMIZATION](guides/MILVUS_OPTIMIZATION.md) | Vector DB optimization |
| [MILVUS_INGESTION](guides/MILVUS_INGESTION.md) | Large-scale data ingestion |

---

## 📚 Historical Reports

| Date | Report | Description |
|------|--------|-------------|
| 2026-01-25 | [Model Update](reports/2026-01-25-model-update.md) | LiteLLM removal + latest models |
| 2026-01-25 | [KB Corruption](reports/2026-01-25-kb-corruption.md) | Metadata corruption incident |
| 2026-01-25 | [Urgent Update](reports/2026-01-25-urgent-update.md) | Critical fixes summary |
| 2026-01-24 | [Troubleshooting](reports/2026-01-24-troubleshooting.md) | GPU OOM & network issues |

---

## 📦 Archives

| Category | Contents |
|----------|----------|
| **[Neo4j](archives/neo4j/)** | Graph database docs (removed in v2.0.0) |
| **[LiteLLM](archives/litellm/)** | Proxy migration docs (v2.0.0) |
| **[Checklists](archives/checklists/)** | Historical implementation checklists |
| **[Session Transcripts](archives/session-transcripts/)** | AI session logs (LIKESPEED.md) |
| **[Strategy Docs](archives/)** | Model configuration, workflow refactoring |

---

## 🗺️ Reading Paths by Role

### New Developer
1. [README](getting-started/README.md) - Project overview
2. [QUICKSTART](getting-started/QUICKSTART.md) - Get it running
3. [REPO_MAP](architecture/REPO_MAP.md) - Understand codebase
4. [API](core/API.md) - Learn the API

### System Administrator
1. [QUICKSTART](getting-started/QUICKSTART.md) - Deployment
2. [CONFIGURATION](core/CONFIGURATION.md) - Environment setup
3. [RUNBOOK](operations/RUNBOOK.md) - Operations
4. [TROUBLESHOOTING](operations/TROUBLESHOOTING.md) - Current status

### ML Engineer
1. [EMBEDDINGS](core/EMBEDDINGS.md) - Embedding pipeline
2. [COLQWEN_SETUP](guides/COLQWEN_SETUP.md) - Model setup
3. [GPU_OPTIMIZATION](guides/GPU_OPTIMIZATION.md) - Performance
4. [MILVUS_OPTIMIZATION](guides/MILVUS_OPTIMIZATION.md) - Vector DB
5. [Vector DB Overview](core/vector_db/OVERVIEW.md) - Multi-vector support

### Troubleshooting Session
1. [TROUBLESHOOTING](operations/TROUBLESHOOTING.md) - Recent status & fixes
2. [Reports](reports/) - Past incidents by date
3. [CHANGE_LOG](operations/CHANGE_LOG.md) - Version history

---

## 📊 Documentation Organization

```
docs/
├── INDEX.md                     ← YOU ARE HERE
│
├── 📖 getting-started/          ← Start here
│   ├── QUICKSTART.md
│   ├── START_HERE.md
│   ├── README.md
│   └── README_zh.md
│
├── 📘 core/                     ← Essential reference
│   ├── API.md
│   ├── CONFIGURATION.md
│   ├── DATABASE.md
│   ├── EMBEDDINGS.md
│   └── vector_db/OVERVIEW.md
│
├── 📋 reference/                ← Detailed references
│   └── ENVIRONMENT_VARIABLES.md ← Complete .env reference
│
├── 🏗️ architecture/             ← System design
│   ├── DEEP_ANALYSIS.md
│   ├── REPO_MAP.md
│   └── ANTI_COMPLEXITY.md
│
├── 🔧 operations/               ← Running & maintaining
│   ├── RUNBOOK.md
│   ├── DEPLOYMENT_DIAGRAM.md
│   ├── CHANGE_LOG.md
│   └── TROUBLESHOOTING.md
│
├── 📚 guides/                   ← How-to guides
│   ├── COLQWEN_SETUP.md
│   ├── GPU_OPTIMIZATION.md
│   ├── MILVUS_OPTIMIZATION.md
│   └── MILVUS_INGESTION.md
│
├── 📋 reports/                  ← Historical (by date)
│   ├── 2026-01-24-*.md
│   └── 2026-01-25-*.md
│
├── 📦 archives/                 ← Superseded/obsolete
│   ├── neo4j/
│   ├── litellm/
│   ├── checklists/
│   ├── session-transcripts/
│   └── *.md (historical)
│
└── ssot/                        ← Single Source of Truth
    ├── stack.md                 ← PRIMARY REFERENCE
    └── QUICK_REF.md
```

---

## ⚠️ Anti-Complexity Guidelines

To prevent documentation drift and complexity accumulation:

### DO
✅ Update existing docs instead of creating new ones
✅ Consolidate related information
✅ Archive outdated docs to `archives/`
✅ Keep INDEX.md up-to-date
✅ Use clear section hierarchies
✅ Link to canonical sources (no duplication)

### DON'T
❌ Create new docs for every troubleshooting session
❌ Keep multiple versions of the same guide
❌ Document temporary workarounds in permanent docs
❌ Create session-specific files (use archives/ instead)
❌ Duplicate information across multiple files

### When Creating New Docs
1. Check if existing doc can be updated instead
2. Ask: Does this deserve a permanent doc or should it go in archives/?
3. Update INDEX.md to include the new doc
4. Link from related docs
5. Set expiration date for temporary docs

---

## 📝 Documentation Maintenance

### Weekly Tasks
- [ ] Review new docs in root directory → move to archives/ or delete
- [ ] Update TROUBLESHOOTING.md with current status
- [ ] Archive old reports (>30 days)
- [ ] Verify all links in INDEX.md work

### Monthly Tasks
- [ ] Consolidate scattered information
- [ ] Update CHANGE_LOG.md
- [ ] Review archives/ for permanent deletion candidates
- [ ] Update version numbers

### When Making Changes
- [ ] Update CHANGE_LOG.md
- [ ] Update affected documentation
- [ ] Update INDEX.md if adding/removing docs
- [ ] Add migration guide if breaking change

---

## 🔍 Search Tips

**Finding Specific Topics:**
```bash
# Search all docs
grep -r "keyword" /LAB/@thesis/layra/docs

# Find files mentioning "milvus"
find /LAB/@thesis/layra/docs -name "*.md" -exec grep -l "milvus" {} \;

# Search API documentation
grep "endpoint" /LAB/@thesis/layra/docs/core/API.md
```

---

## 📊 Document Health Report

| Metric | Count |
|--------|-------|
| **Total Markdown Files** | 207 → ~50 (75% reduction) |
| **Root Level** | 4 |
| **SSOT** | 4 |
| **Core Docs** | 7 |
| **Getting Started** | 4 |
| **Architecture** | 3 |
| **Operations** | 4 |
| **Guides** | 5 |
| **Reports (Active)** | 3 |
| **Archives** | 122+ |
| **Health** | 🟢 **Excellent** |

**Consolidation Summary:**
- Moved 35+ old reports to `archives/reports/2026-01/`
- Consolidated database/data flow docs into `core/`
- Kept only essential docs in root level

---

## 🆘 Getting Help

**Documentation Issues:**
- File an issue: [GitHub Issues](https://github.com/liweiphys/layra/issues)
- Check recent changes: [CHANGE_LOG.md](operations/CHANGE_LOG.md)
- Search past incidents: [archives/](archives/)

**System Issues:**
- Check status: [TROUBLESHOOTING.md](operations/TROUBLESHOOTING.md)
- Recent fixes: [Reports](reports/)
- KB corruption: [2026-01-25-kb-corruption.md](reports/2026-01-25-kb-corruption.md)

---

**Last Review:** 2026-01-26
**Next Review Due:** 2026-02-02
**Maintainer:** AI/Human collaborative maintenance

# LiteLLM Documentation Map

**Quick navigation to all documentation** | Updated: 2026-01-24

---

## 🚀 Getting Started (Start Here)

### New Users
1. **[`README.md`](./README.md)** - Overview & quick start
2. **[`PRODUCTION_SETUP.md`](./PRODUCTION_SETUP.md)** - Complete production setup guide
3. **[`PROVIDER_SETUP.md`](./PROVIDER_SETUP.md)** - Provider API keys & configuration

### Quick Reference
- **[`docs/providers/QUICK_REFERENCE.md`](./docs/providers/QUICK_REFERENCE.md)** - Provider quick lookup
- **[`.env.example`](./.env.example)** - Environment variable template

---

## 📖 Core Documentation

### Production Configuration
| Document | Description | Size |
|----------|-------------|------|
| **[`PRODUCTION_SETUP.md`](./PRODUCTION_SETUP.md)** | Complete production setup guide | 661 lines |
| **[`PROVIDER_SETUP.md`](./PROVIDER_SETUP.md)** | Provider configuration & troubleshooting | 634 lines |
| **[`OFFICIAL_DOCS_ALIGNMENT.md`](./OFFICIAL_DOCS_ALIGNMENT.md)** | Production settings explained | 430 lines |
| **[`.env.example`](./.env.example)** | Environment variables with provider details | Updated |

### Operations & Management
| Document | Description |
|----------|-------------|
| **[`docs/LITELLM_OPS.md`](./docs/LITELLM_OPS.md)** | Operational runbook |
| **[`docs/MODEL_MANAGEMENT.md`](./docs/MODEL_MANAGEMENT.md)** | Model configuration guide |
| **[`docs/DOCKER_DEPLOYMENT.md`](./docs/DOCKER_DEPLOYMENT.md)** | Docker deployment procedures |
| **[`docs/PRODUCTION_DEPLOYMENT.md`](./docs/PRODUCTION_DEPLOYMENT.md)** | Production deployment guide |

### Reference
| Document | Description |
|----------|-------------|
| **[`docs/REPO_STRUCTURE.md`](./docs/REPO_STRUCTURE.md)** | Repository structure |
| **[`docs/INFRA_KNOWLEDGE.md`](./docs/INFRA_KNOWLEDGE.md)** | Infrastructure details |
| **[`docs/HARDENING.md`](./docs/HARDENING.md)** | Security hardening |
| **[`docs/INDEX.md`](./docs/INDEX.md)** | Documentation index |

---

## 🔌 Provider Documentation

| Document | Description |
|----------|-------------|
| **[`PROVIDER_SETUP.md`](./PROVIDER_SETUP.md)** | Complete provider setup guide ⭐ |
| **[`docs/providers/QUICK_REFERENCE.md`](./docs/providers/QUICK_REFERENCE.md)** | Quick lookup card ⚡ |
| **[`docs/providers/README.md`](./docs/providers/README.md)** | Provider docs index |
| **[`docs/providers/GEMINI_API_KEY_SETUP.md`](./docs/providers/GEMINI_API_KEY_SETUP.md)** | Gemini quick setup |
| **[`docs/providers/GEMINI.md`](./docs/providers/GEMINI.md)** | Legacy Gemini docs |
| **[`docs/providers/OPENCODE_SETUP.md`](./docs/providers/OPENCODE_SETUP.md)** | OpenCode integration |

**Providers Covered:** Ollama Cloud, Google Gemini, Voyage AI, Cohere, OpenAI, Anthropic, Zhipu AI, MiniMax, Hyperbolic

---

## 📊 Generated Reports

Located in `docs/generated/`:

| Report | Description |
|--------|-------------|
| **`MODEL_CAPABILITIES.md`** | Per-model capability matrix |
| **`MODEL_INVENTORY_REPORT.md`** | Model inventory sync report |
| **`.last_refresh_attempt`** | Last capability refresh timestamp |

**Generate:** `./bin/probe_capabilities.py --scope all --fetch-docs`

---

## 📦 Consolidation Summaries

| Document | Description |
|----------|-------------|
| **[`DOCUMENTATION_CONSOLIDATION.md`](./DOCUMENTATION_CONSOLIDATION.md)** | Main documentation consolidation summary |
| **[`PROVIDER_CONSOLIDATION.md`](./PROVIDER_CONSOLIDATION.md)** | Provider documentation consolidation |

---

## 🗂️ Archive

### Historical Documentation

**Location:** `docs/archive/2026-01-24-before-consolidation/`

**Contents:** Pre-consolidation status docs, fix documentation, gap analyses (15 files)

---

## 🎯 Common Tasks

### I want to...

| Task | Read This |
|------|-----------|
| **Get started quickly** | [`README.md`](./README.md) |
| **Set up production** | [`PRODUCTION_SETUP.md`](./PRODUCTION_SETUP.md) |
| **Configure providers** | [`PROVIDER_SETUP.md`](./PROVIDER_SETUP.md) |
| **Quick provider lookup** | [`docs/providers/QUICK_REFERENCE.md`](./docs/providers/QUICK_REFERENCE.md) |
| **Understand settings** | [`OFFICIAL_DOCS_ALIGNMENT.md`](./OFFICIAL_DOCS_ALIGNMENT.md) |
| **Operate the proxy** | [`docs/LITELLM_OPS.md`](./docs/LITELLM_OPS.md) |
| **Add/modify models** | [`docs/MODEL_MANAGEMENT.md`](./docs/MODEL_MANAGEMENT.md) |
| **Troubleshoot issues** | [`PRODUCTION_SETUP.md`](./PRODUCTION_SETUP.md) → Troubleshooting |
| **Troubleshoot providers** | [`PROVIDER_SETUP.md`](./PROVIDER_SETUP.md) → Troubleshooting |
| **See all docs** | [`docs/INDEX.md`](./docs/INDEX.md) |

---

## 📈 Documentation Stats

### Core Documentation
- **Total lines:** 2,300+ lines across main guides
- **Main guides:** 5 comprehensive documents
- **Quick references:** 2 fast lookup cards
- **Provider docs:** 6 guides (1 main + 5 historical/specific)

### Structure
- **Root docs:** 7 core files (focused)
- **Provider docs:** `docs/providers/` (6 files)
- **Operational docs:** `docs/` (10+ files)
- **Generated reports:** `docs/generated/` (3 files)
- **Historical archive:** `docs/archive/` (15 files)

### Reduction
- **Before consolidation:** 17+ root markdown files
- **After consolidation:** 7 core files (59% reduction)
- **Archived:** 15 historical files preserved

---

## 🔗 External References

### Official LiteLLM Documentation
- [Production Best Practices](https://docs.litellm.ai/docs/proxy/prod)
- [Configuration Settings](https://docs.litellm.ai/docs/proxy/config_settings)
- [All Providers](https://docs.litellm.ai/docs/providers)
- [GitHub Repository](https://github.com/BerriAI/litellm)

### Provider Documentation
- [Ollama API](https://ollama.com/docs/api)
- [Google AI Studio](https://ai.google.dev/)
- [Voyage AI Docs](https://docs.voyageai.com/)
- [Cohere Docs](https://docs.cohere.com/)
- [OpenAI Docs](https://platform.openai.com/docs)
- [Anthropic Docs](https://docs.anthropic.com/)

---

## 📋 Quick Start Commands

```bash
# Setup
cp .env.example .env
vim .env  # Add API keys (see PROVIDER_SETUP.md)

# Start services
docker-compose up -d

# Verify
curl http://localhost:4001/health/liveliness
just check
just probe

# Operations
just logs       # View logs
just restart    # Restart proxy
just backup     # Backup database
```

---

## 🏗️ Directory Structure

```
/LAB/@litellm/
│
├── 📘 Core Documentation (Root)
│   ├── README.md                      ⭐ Start here
│   ├── PRODUCTION_SETUP.md            📖 Production guide (661 lines)
│   ├── PROVIDER_SETUP.md              🔌 Provider guide (634 lines)
│   ├── OFFICIAL_DOCS_ALIGNMENT.md     📊 Settings explained (430 lines)
│   ├── DOCUMENTATION_MAP.md           🗺️  This file
│   ├── DOCUMENTATION_CONSOLIDATION.md 📝 Consolidation summary
│   └── PROVIDER_CONSOLIDATION.md      📝 Provider consolidation
│
├── 🔐 Configuration
│   ├── .env.example                   Environment template
│   ├── config.yaml                    Main configuration (SSOT)
│   ├── docker-compose.yml             Container orchestration
│   └── .env                           Secrets (not in git)
│
├── 📁 docs/
│   ├── INDEX.md                       Documentation index
│   ├── LITELLM_OPS.md                 Operational runbook
│   ├── MODEL_MANAGEMENT.md            Model configuration
│   ├── DOCKER_DEPLOYMENT.md           Docker guide
│   ├── PRODUCTION_DEPLOYMENT.md       Production procedures
│   ├── HARDENING.md                   Security guide
│   ├── INFRA_KNOWLEDGE.md             Infrastructure
│   ├── REPO_STRUCTURE.md              Repository layout
│   │
│   ├── providers/                     Provider-specific docs
│   │   ├── README.md
│   │   ├── QUICK_REFERENCE.md         ⚡ Fast lookup
│   │   ├── GEMINI_API_KEY_SETUP.md
│   │   ├── GEMINI.md
│   │   └── OPENCODE_SETUP.md
│   │
│   ├── generated/                     Auto-generated reports
│   │   ├── MODEL_CAPABILITIES.md
│   │   ├── MODEL_INVENTORY_REPORT.md
│   │   └── .last_refresh_attempt
│   │
│   └── archive/                       Historical documentation
│       └── 2026-01-24-before-consolidation/
│
├── 📁 bin/                            Operational scripts
│   ├── health_check.py
│   ├── model_inventory_report.py
│   ├── probe_capabilities.py
│   └── ops/
│
├── 📁 state/                          Runtime state (volatile)
├── 📁 logs/                           Container logs (volatile)
└── 📁 migrations/                     Database migrations
```

---

## ✅ Documentation Quality

- ✅ **Comprehensive** - All aspects covered
- ✅ **Well-organized** - Clear hierarchy and structure
- ✅ **Production-ready** - Aligned with official best practices
- ✅ **Self-documenting** - Config files include inline explanations
- ✅ **Maintainable** - Single source of truth for each topic
- ✅ **Discoverable** - Clear entry points and navigation
- ✅ **Historical context** - Archive preserves evolution

---

**Last Updated:** 2026-01-24  
**Status:** Production-ready with comprehensive documentation

For questions, start with [`README.md`](./README.md) or consult the task-specific guide above.

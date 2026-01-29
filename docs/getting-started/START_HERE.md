# 🚀 START HERE

**New to Layra?** Follow this path:

## 1. Quick Setup (5 minutes)

```bash
cd /LAB/@thesis/layra

# 1. Configure API keys
nano .env
# Add: OPENAI_API_KEY=sk-proj-...
#      DEEPSEEK_API_KEY=sk-...

# 2. Deploy
./scripts/start_layra.sh

# 3. Access
# http://localhost:8090
# Create a user in the UI (or use an existing demo user if preseeded)
```

**Full Guide:** [QUICKSTART.md](QUICKSTART.md)

---

## 2. What Changed Recently? (2026-01-25)

✅ **LiteLLM Removed** - Now using direct OpenAI/DeepSeek APIs  
✅ **Neo4j Removed** (default stack) - Saves 500MB RAM  
✅ **KB Corruption Fixed** - 0 duplicates, validated  
✅ **Documentation Reorganized** - See INDEX.md  

**Details:** [CHANGES_20260125.md](CHANGES_20260125.md)

---

## 3. Documentation Map

- **[INDEX.md](INDEX.md)** - Complete documentation navigation
- **[ANTI_COMPLEXITY.md](ANTI_COMPLEXITY.md)** - Prevent complexity creep
- **[API.md](API.md)** - REST API reference
- **[DATABASE.md](DATABASE.md)** - Database schemas

---

## 4. Troubleshooting

**System won't start?**
- Check API keys in `.env`
- See [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md)

**KB issues?**
- See [DRIFT_FORENSICS_20260125.md](DRIFT_FORENSICS_20260125.md)

**Migration from v1.x?**
- See [LITELLM_REMOVAL_GUIDE.md](LITELLM_REMOVAL_GUIDE.md)

---

**Ready?** Start with [QUICKSTART.md](QUICKSTART.md)

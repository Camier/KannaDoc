# Anti-Complexity Guidelines

**Purpose:** Prevent complexity accumulation and drift in the Layra project  
**Last Updated:** 2026-01-25  
**Status:** 🟢 Active Policy

---

## 🎯 Core Principles

### **1. Minimalism Over Future-Proofing**

**DO:**
- ✅ Build what you need TODAY
- ✅ Add features when there's proven demand
- ✅ Remove unused infrastructure immediately
- ✅ Question "what if" scenarios critically

**DON'T:**
- ❌ Add services "for future use"
- ❌ Deploy infrastructure without application code
- ❌ Keep features because "we might need them"
- ❌ Build for hypothetical scale

**Example - Neo4j Removal:**
```yaml
# BAD: Deployed Neo4j with 0 lines of application code
# Impact: 500MB RAM, monitoring overhead, no value
# Action: REMOVED (can re-add when actually needed)

# GOOD: Deploy when there's code that uses it
# Trigger: "We have graph queries ready to test"
```

---

### **2. Idempotency is Non-Negotiable**

**Every Data-Modifying Operation Must Be Idempotent**

**DO:**
- ✅ Check if operation already done before executing
- ✅ Use Redis keys with TTL for duplicate detection
- ✅ Implement atomic transactions (all-or-nothing)
- ✅ Add unique constraints at database level

**DON'T:**
- ❌ Assume retry won't happen
- ❌ Append to arrays without deduplication
- ❌ Create resources without existence checks
- ❌ Trust "it only runs once"

**Example - KB Ingestion:**
```python
# BAD: Appends without checking
kb_files.append(new_file)  # Retry creates duplicates!

# GOOD: Check first
if file_id not in existing_file_ids:
    kb_files.append(new_file)

# BETTER: Redis idempotency
duplicate_key = f"ingestion:{file_id}"
if await redis.exists(duplicate_key):
    return {"status": "already_processing"}
await redis.setex(duplicate_key, 86400, "processing")
```

---

### **3. Documentation Hygiene**

**DO:**
- ✅ Update existing docs instead of creating new ones
- ✅ Archive session-specific files after 30 days
- ✅ Consolidate scattered information
- ✅ Maintain `docs/INDEX.md` as single source of navigation
- ✅ Delete outdated docs immediately

**DON'T:**
- ❌ Create new doc for every troubleshooting session
- ❌ Keep multiple versions of same guide
- ❌ Document temporary workarounds permanently
- ❌ Let docs/ exceed 20 active files

**Current Status:**
- ✅ `docs/INDEX.md` created (navigation hub)
- ⚠️ 30 markdown files (target: ≤20)
- 📋 Action: Consolidate troubleshooting reports

**Archive Criteria:**
- Session transcripts (e.g., `LIKESPEED.md`) → `archives/` immediately
- Troubleshooting reports > 30 days → `archives/`
- Deprecated guides → Delete if superseded
- Planning docs (completed) → `archives/` or delete

---

### **4. One Source of Truth (SSOT)**

**For Every Piece of Information, There Should Be ONE Canonical Source**

**DO:**
- ✅ Link to canonical source, don't duplicate
- ✅ Update SSOT when changes happen
- ✅ Use references for derived information
- ✅ Maintain `docs/ssot/` for critical configs

**DON'T:**
- ❌ Copy-paste information across multiple docs
- ❌ Maintain parallel documentation trees
- ❌ Update one place and forget others
- ❌ Have "old" and "new" versions coexisting

**SSOT Locations:**
- **Tech Stack:** `docs/ssot/stack.md`
- **Environment Config:** `.env` + `docs/CONFIGURATION.md`
- **API Reference:** `docs/API.md` (generated from OpenAPI)
- **Database Schemas:** `docs/DATABASE.md`
- **Architecture:** `docs/LAYRA_DEEP_ANALYSIS.md`

---

### **5. Explicit Over Implicit**

**DO:**
- ✅ Validate all assumptions with assertions
- ✅ Fail fast with clear error messages
- ✅ Log important decisions
- ✅ Make required fields explicit in schemas

**DON'T:**
- ❌ Assume fields exist without validation
- ❌ Silently fail or return empty results
- ❌ Use magic numbers or unexplained defaults
- ❌ Skip error handling "because it won't happen"

**Example - Metadata Validation:**
```python
# BAD: Assumes field exists
last_modified = kb_record["last_modify_at"]  # KeyError!

# GOOD: Validates first
if "last_modify_at" not in kb_record:
    raise ValueError("Missing required field: last_modify_at")
last_modified = kb_record["last_modify_at"]

# BETTER: Schema validation
from pydantic import BaseModel, Field
class KBRecord(BaseModel):
    knowledge_base_id: str
    last_modify_at: datetime  # Required by type system
```

---

### **6. Measure Complexity**

**Track Complexity Metrics and Set Limits**

| Metric | Current | Target | Action Threshold |
|--------|---------|--------|------------------|
| **Active Containers** | 13 | ≤15 | Review if >15 |
| **Docker Networks** | 1 | 1 | Investigate if >1 |
| **Active Docs** | 30 | ≤20 | Consolidate if >25 |
| **Docker Compose Files** | 3 | 1-2 | Merge if >3 |
| **Python Scripts (root)** | 15 | ≤10 | Move to subdirs |
| **Env Vars (.env)** | 130 | ≤150 | Review if >150 |

**Review Triggers:**
- New service added → Justify necessity
- New doc created → Check for duplicate
- New script created → Check for existing solution
- Network issues → Review topology

---

### **7. Delete Aggressively**

**Deleting Code/Docs/Services is Progress, Not Regression**

**DO:**
- ✅ Remove unused code immediately
- ✅ Archive instead of delete if uncertain
- ✅ Set expiration dates for temporary workarounds
- ✅ Celebrate deletions in changelogs

**DON'T:**
- ❌ Keep code "just in case"
- ❌ Comment out large blocks instead of deleting
- ❌ Maintain deprecated features indefinitely
- ❌ Fear breaking things (that's what git is for)

**Deletion Checklist:**
- [ ] Feature not used in 90 days?
- [ ] No references in codebase? (grep check)
- [ ] No external dependencies? (API callers)
- [ ] Documented in CHANGE_LOG.md?
- [ ] Git history preserved? (recovery possible)

**Recent Deletions (2026-01-25):**
- ✅ LiteLLM proxy (3 containers, 395-line config, unused features)
- ✅ Neo4j service (thesis mode, 0 application code)
- ✅ `litellm_net` network (isolation issue)

---

## 📊 Complexity Audit Process

### **Weekly Review (Every Friday)**

```bash
# 1. Count active containers
docker ps --format '{{.Names}}' | wc -l

# 2. Count active docs
find docs/ -name "*.md" -type f | wc -l

# 3. Find large files (>100KB)
find docs/ -name "*.md" -size +100k

# 4. Find old troubleshooting reports
find docs/ -name "TROUBLESHOOTING*.md" -mtime +30

# 5. Check for unused scripts
find scripts/ -name "*.py" -type f | xargs grep -l "if __name__"
```

### **Monthly Cleanup (First Monday)**

1. **Archive old docs:**
   ```bash
   mv docs/TROUBLESHOOTING_REPORT_*.md docs/archives/
   ```

2. **Consolidate scattered info:**
   - Merge similar troubleshooting reports
   - Update INDEX.md

3. **Remove deprecated features:**
   - Check DEPRECATION.md for expired items
   - Delete code + update docs

4. **Update metrics dashboard:**
   - Container count
   - Memory usage
   - Doc count
   - Service count

---

## 🚨 Warning Signs of Complexity Creep

### **Red Flags:**

🔴 **"We might need this later"** → Remove until actually needed  
🔴 **Service running with 0 code using it** → Delete service  
🔴 **>3 troubleshooting docs in 1 week** → Systemic issue, not doc issue  
🔴 **Network isolation issues** → Topology too complex  
🔴 **"Just add a workaround"** → Fix root cause instead  
🔴 **>5 docker-compose files** → Consolidate with profiles  
🔴 **Duplicate detection failing** → Idempotency missing  
🔴 **Manual intervention required** → Automation gap  

### **Yellow Flags:**

🟡 New service added without documentation  
🟡 Script created without tests  
🟡 Config option added without validation  
🟡 Temporary fix not removed after 30 days  
🟡 Exception handler that silences errors  
🟡 Assumption without validation  

---

## 📋 Decision Framework

### **Before Adding Anything (Service/Feature/Doc):**

**Ask These Questions:**

1. **Do we need this TODAY?**
   - If no → DON'T ADD IT

2. **Can we use existing infrastructure?**
   - If yes → USE EXISTING

3. **What's the maintenance cost?**
   - High cost + low usage = NO

4. **Can we delete it easily later?**
   - If no → Rethink design

5. **Is there a simpler alternative?**
   - If yes → USE SIMPLER

6. **Does this solve a real problem?**
   - "Nice to have" = NO
   - "Blocks user" = YES

**Example - LiteLLM Decision:**
```
Q: Do we need this TODAY?
A: No - thesis mode has 1 user, not managing multiple providers

Q: Can we use existing?
A: Yes - OpenAI SDK directly

Q: Maintenance cost?
A: High - 3 extra containers, 395-line config, network complexity

Q: Delete easily?
A: No - requires migration script

Q: Simpler alternative?
A: Yes - direct provider calls

Decision: REMOVE LiteLLM
```

---

## 🛡️ Safeguards

### **Code Review Checklist:**

**For Every PR, Check:**
- [ ] Does this add a new dependency? Justify it
- [ ] Does this add a new service? Justify it
- [ ] Does this create new documentation? Update INDEX.md
- [ ] Does this add configuration? Document in CONFIGURATION.md
- [ ] Is idempotency preserved? (for data operations)
- [ ] Are required fields validated?
- [ ] Are errors logged explicitly?
- [ ] Is there a simpler way?

### **AI Agent Guidelines:**

**When AI agents create code/scripts:**
- [ ] Implement idempotency checks (Redis keys)
- [ ] Validate all required metadata fields
- [ ] Add comprehensive error logging
- [ ] Don't create new docs without updating INDEX.md
- [ ] Don't add services without application code
- [ ] Prefer updating existing code over new files

**Lessons from Jan 2026 Incident:**
- AI agent created retry script without idempotency → 114 duplicates
- Manual sync script omitted required field → frontend crash
- **Prevention:** Review agent output against this checklist

---

## 📈 Success Metrics

**Good Indicators:**
- ✅ Container count decreasing or stable
- ✅ Memory usage optimized
- ✅ Fewer manual interventions needed
- ✅ Documentation easy to navigate
- ✅ Onboarding time decreasing
- ✅ Fewer "how do I..." questions

**Bad Indicators:**
- ❌ Container count creeping up
- ❌ New network isolation issues
- ❌ Troubleshooting docs multiplying
- ❌ Manual scripts accumulating
- ❌ "We need to refactor this" conversations
- ❌ Nobody understands the full system

---

## 🎓 Case Studies

### **Case Study 1: LiteLLM Removal (2026-01-25)**

**Problem:**
- 3 extra containers (litellm, postgres, redis)
- 395-line config.yaml defining 40+ models
- Network isolation causing workflow failures
- 95% of features unused (thesis mode = 1 user)

**Analysis:**
- Added for multi-provider routing (not needed for 1 user)
- Cost tracking unused (no budget management)
- Rate limiting pointless (1 user)
- Future-proofing that never happened

**Solution:**
- Removed LiteLLM completely
- Direct OpenAI/DeepSeek API calls
- −3 containers, simpler architecture
- Network isolation issues gone

**Lesson:** Don't add infrastructure for hypothetical future needs.

---

### **Case Study 2: Neo4j Deployment (2026-01-23)**

**Problem:**
- Neo4j service running (500MB RAM)
- 0 lines of application code using it
- Ports exposed, monitoring added
- "Future roadmap" justification

**Analysis:**
- Deployed because "graph DB sounds useful"
- No concrete use case defined
- No implementation timeline
- Immediate cost, hypothetical value

**Solution:**
- Commented out service in thesis mode
- Can re-enable when:
  - Use case defined
  - Code written
  - Testing ready

**Lesson:** Deploy services when code exists, not before.

---

### **Case Study 3: KB Corruption (2026-01-21)**

**Problem:**
- 114 duplicate KB entries
- Failed ingestion retries without idempotency
- Manual sync script missing required fields

**Analysis:**
- No duplicate detection in retry logic
- Assumed retries wouldn't happen (they did)
- Field validation not enforced
- AI agent amplified existing code weaknesses

**Solution:**
- Added Redis-based idempotency (24h TTL)
- Metadata validation enforced
- Full atomic re-ingestion
- Schema validation via Pydantic

**Lesson:** Idempotency is not optional for data operations.

---

## 🔧 Tools & Automation

### **Complexity Monitoring Script**

```bash
#!/bin/bash
# scripts/check_complexity.sh

echo "=== Layra Complexity Check ==="
echo

echo "📦 Containers:"
docker ps --format '{{.Names}}' | wc -l
echo "Target: ≤15"
echo

echo "📝 Active Docs:"
find docs/ -name "*.md" -type f | wc -l
echo "Target: ≤20"
echo

echo "📊 Large Docs (>100KB):"
find docs/ -name "*.md" -size +100k -exec ls -lh {} \; | awk '{print $9, $5}'
echo

echo "🗂️ Docker Compose Files:"
find . -name "docker-compose*.yml" -type f | wc -l
echo "Target: ≤2"
echo

echo "🌐 Networks:"
docker network ls --format '{{.Name}}' | grep -v "bridge\|host\|none" | wc -l
echo "Target: 1"
```

### **Documentation Cleanup Script**

```bash
#!/bin/bash
# scripts/cleanup_docs.sh

# Archive old troubleshooting reports
find docs/ -name "TROUBLESHOOTING_*.md" -mtime +30 -exec mv {} docs/archives/ \;

# Archive session transcripts
find docs/ -name "*session*.md" -exec mv {} docs/archives/ \;

# Find orphaned images
find docs/ -name "*.png" -o -name "*.jpg" | while read img; do
  if ! grep -r "$(basename $img)" docs/*.md; then
    echo "Orphaned: $img"
  fi
done
```

---

## 📚 Further Reading

- [INDEX.md](INDEX.md) - Documentation navigation
- [LITELLM_ANALYSIS.md](LITELLM_ANALYSIS.md) - Overengineering case study
- [DRIFT_FORENSICS_20260125.md](DRIFT_FORENSICS_20260125.md) - KB corruption analysis
- [CHANGE_LOG.md](CHANGE_LOG.md) - Version history

---

**Last Review:** 2026-01-25  
**Next Review:** 2026-02-01  
**Maintainer:** Project-wide responsibility

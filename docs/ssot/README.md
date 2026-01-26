# SSOT - Single Source of Truth

This directory contains the **authoritative reference documentation** for the LAYRA stack.

## 📘 Primary Documents

### [stack.md](stack.md) ⭐ **MAIN REFERENCE**

**The definitive source for:**
- Complete system architecture
- All services, versions, and configurations
- Network topology and data flows
- Environment variables
- Deployment procedures
- Known issues and limitations
- Architecture Decision Records (ADRs)
- Version history

**Size:** 887 lines  
**Last Updated:** 2026-01-25  
**Version:** 2.0.0

### [QUICK_REF.md](QUICK_REF.md)

**One-page cheat sheet for:**
- Common Docker commands
- Service access credentials
- Quick troubleshooting
- Critical environment variables

**Size:** 217 lines  
**Purpose:** Fast reference during operations

---

## 📜 SSOT Policy

**BEFORE making ANY architectural change:**
1. ✅ Consult `stack.md` for current state
2. ✅ Document the decision (ADR if significant)
3. ✅ Update `stack.md` with the change
4. ✅ Verify no conflicts with documented principles

**AFTER implementing a change:**
1. ✅ Update service tables with new versions/configs
2. ✅ Update data flow diagrams if topology changed
3. ✅ Add entry to Update Log
4. ✅ Update version number if major change

---

## 🎯 What Requires SSOT Update?

**MUST update:**
- ✅ Adding/removing services
- ✅ Changing service versions
- ✅ Modifying ports or networks
- ✅ Adding/removing environment variables
- ✅ Changing data flows
- ✅ Architectural decisions

**OPTIONAL update:**
- Configuration tweaks (same version)
- Documentation improvements (non-architectural)
- Code refactoring (no service changes)

---

## 🔍 Quick Links

**For New Users:**
- Start with [../START_HERE.md](../START_HERE.md)
- Then read [stack.md](stack.md) sections 1-3
- Keep [QUICK_REF.md](QUICK_REF.md) open for commands

**For Operators:**
- Keep [QUICK_REF.md](QUICK_REF.md) bookmarked
- Consult [stack.md](stack.md) section 10 for procedures
- Check [stack.md](stack.md) section 8 for known issues

**For Developers:**
- Read [stack.md](stack.md) sections 4-7 (tech stack)
- Check [stack.md](stack.md) section 11 for code locations
- Follow ADRs in [stack.md](stack.md) section 13

---

## 📊 Document Status

| Document | Status | Last Update | Lines |
|----------|--------|-------------|-------|
| `stack.md` | ✅ Current | 2026-01-25 | 887 |
| `QUICK_REF.md` | ✅ Current | 2026-01-25 | 217 |
| `README.md` | ✅ Current | 2026-01-25 | (this file) |

---

## 🛡️ Drift Prevention

**To prevent documentation drift:**

1. **Weekly Check** (Every Friday):
   - Compare `stack.md` with `docker ps` output
   - Verify environment variables match `.env`
   - Check for orphaned volume references

2. **Post-Deployment Verification**:
   - After any deployment, verify container count
   - Confirm service versions match documented
   - Update resource usage if significant change

3. **Code Review Requirement**:
   - PRs that modify docker-compose MUST update SSOT
   - PRs that add/remove services MUST document ADR

---

**Maintained by:** System  
**Contact:** See [../ANTI_COMPLEXITY.md](../ANTI_COMPLEXITY.md) for complexity guidelines

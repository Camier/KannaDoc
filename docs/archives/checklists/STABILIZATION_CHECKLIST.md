# Stabilization Checklist (Post-v2.0.0 Troubleshooting)

**Start Date:** 2026-01-24
**Objective:** Resolve infrastructure failures preventing "Thesis Blueprint" workflow execution.

---

## 🔴 Critical Fixes (Blocking Workflow)

### 1. Fix Model Server Crash (OOM)
- [x] **Diagnose**: Identify OOM cause (ColQwen2.5 default resolution too high for 16GB VRAM).
- [x] **Fix**: Reduce `shortest_edge` to 768px in `model-server/colbert_service.py`.
- [x] **Verify**: Service starts, passes warmup, memory stable at ~3GB.
- [x] **Document**: Update `docs/CONFIGURATION.md` with new GPU settings.

### 2. Fix LiteLLM Network Isolation
- [ ] **Diagnose**: `layra-backend` cannot resolve `litellm-proxy` due to separate Docker networks. Manual link breaks on container restart.
- [ ] **Fix**:
    - Update `/LAB/@litellm/docker-compose.yml` to attach to `layra_layra-net`.
    - OR Update `layra/docker-compose.thesis.yml` to treat `litellm` as external service with shared network.
- [ ] **Verify**: `curl http://litellm-proxy:4000/health` from `layra-backend` persists after restarts.

### 3. Verify Authentication
- [ ] **Diagnose**: Workflow execution returns `401 Invalid proxy server token` despite using Master Key.
- [ ] **Audit**: Check `LITELLM_MASTER_KEY` in `/LAB/@litellm/.env` vs `scripts/deploy_thesis_workflow_full.py`.
- [ ] **Test**: `curl` with key from host machine to verify validity.
- [ ] **Fix**: Update workflow/deployment script with verified key.

### 4. Workflow Execution
- [ ] **Execute**: Run `workflow_v5` (or newer).
- [ ] **Verify**: Node `n1` completes successfully.
- [ ] **Monitor**: Check for further OOM or timeouts in `model-server` during actual RAG workload.

---

## 🟡 Reliability Improvements

### 5. Network Hardening
- [ ] **DNS**: Configure explicit DNS names or aliases for cross-stack communication.
- [ ] **Health Checks**: Ensure dependent services wait for `litellm-proxy`.

### 6. Documentation
- [x] **Report**: Create `docs/TROUBLESHOOTING_REPORT_20260124.md`.
- [x] **Status**: Update `PROJECT_STATE.md`.
- [x] **Cleanup**: Archive old v2.0.0 plans.

---

## 🟢 Monitoring

- [ ] **Check**: Prometheus metrics for `gpu_memory_usage`.
- [ ] **Check**: Kafka consumer lag during workflow execution.

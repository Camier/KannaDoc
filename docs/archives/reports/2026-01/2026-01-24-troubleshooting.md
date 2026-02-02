# Troubleshooting Report: Infrastructure & Connectivity (2026-01-24)

## 1. Executive Summary
**Status:** Partial Resolution.
**Critical Fix:** Resolved `layra-model-server` crash loop caused by GPU OOM.
**Pending:** Intermittent connectivity between `layra-backend` and `litellm-proxy` due to container restarts and isolated Docker networks.

## 2. Issue: Workflow Execution Failure (DNS/Network)
**Symptom:**
Workflow tasks failed immediately at Node `n1` (Requirements) with:
```
ValueError: n1:节点Requirements: [Errno -3] Temporary failure in name resolution
```
This indicated `layra-backend` could not resolve hostnames (`model-server` or `litellm-proxy`).

### 2.1 Root Cause Analysis: Model Server OOM
**Observation:**
- `docker ps` showed `layra-model-server` in `Exited (0)` state.
- Logs revealed repeated **CUDA Out Of Memory** errors during startup warmup.
- **Cause:** The default `ColQwen2.5` processor configuration set `shortest_edge` to `56*56` (3136 pixels), requiring >15GB VRAM. The RTX 5000 (16GB) was insufficient once overhead was included.

**Resolution:**
- **Action:** Patched `model-server/colbert_service.py` to reduce image resolution.
- **Change:**
  ```python
  # Old
  size={"shortest_edge": 56 * 56, "longest_edge": 28 * 28 * 768}
  # New (Conservative)
  size={"shortest_edge": 768, "longest_edge": 1536}
  ```
- **Result:** Service successfully started and passed warmup with ~3GB GPU memory usage.

### 2.2 Root Cause Analysis: LiteLLM Network Isolation
**Observation:**
- `layra-backend` runs in `layra_layra-net`.
- `litellm-proxy` runs in `litellm_litellm-net`.
- They cannot resolve each other by container name default.

**Attempted Fix (Transient):**
- Ran `docker network connect layra_layra-net litellm-proxy`.
- **Failure:** `litellm-proxy` container restarted (likely due to internal health checks or config updates), causing it to lose the manually attached network interface.
- **Impact:** Workflow `v5` failed with `401` (Auth) and then `Could not resolve host` as the link broke.

### 2.3 Root Cause Analysis: Authentication
**Observation:**
- Workflow `v5` failed with `Authentication Error ... Received API Key = sk-...1234`.
- **Cause:** The deployment script was updated with the Master Key, but the error log suggests an old or incorrect key was still received by LiteLLM, OR the key format was rejected.
- **Action:** Confirmed `workflow_v5.json` contains the correct Master Key. The error might be a red herring caused by the network drop or specific proxy behavior.

## 3. Current System State

| Service | Status | Notes |
| :--- | :--- | :--- |
| **layra-backend** | 🟢 Healthy | Connectivity to `model-server` restored. |
| **layra-model-server** | 🟢 Healthy | **OOM Fixed**. Optimized for 16GB VRAM. |
| **litellm-proxy** | 🟡 Unstable | Restarting periodically. Network link to `layra` drops on restart. |
| **Workflow** | 🔴 Failing | Blocked by LiteLLM connectivity/auth. |

## 4. Recommendations & Next Steps

1.  **Network Persistence:**
    - Modify `/LAB/@litellm/docker-compose.yml` to explicitly join `layra_layra-net` OR use a shared external network for all AI services.
2.  **Auth Verification:**
    - Verify `LITELLM_MASTER_KEY` directly against the proxy using `curl` from the host before testing inside the container.
3.  **Workflow Retry:**
    - Once network is stable, re-run `workflow_v5` to confirm end-to-end execution.

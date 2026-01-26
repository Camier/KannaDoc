# Compliance Evaluation: Runtime Patching via sitecustomize.py

**Date:** January 19, 2026
**Subject:** Usage of `sitecustomize.py` to inject `utils/litellm_patches.py`.

## 1. Executive Summary
The use of `sitecustomize.py` to monkeypatch `litellm` internals is **NON-COMPLIANT** with official LiteLLM documentation, which recommends using standard configuration (`config.yaml`), callbacks, or plugin systems for extensibility.

However, within the context of the `/LAB/@litellm` project, this practice is a **Documented Technical Debt** (see `docs/RESOLVE_TECHNICAL_DEBT.md`) used to resolve critical blocking bugs in the pinned version (v1.81.0).

## 2. Findings

### 2.1 Official Documentation vs. Implementation
| Feature | Implementation | Official Recommendation | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Auth Bypass** | Monkeypatch `auth_checks.get_actual_routes` | Use `pass_through_endpoints` config | 🔴 **Non-Compliant** (Fixes upstream bug) |
| **Embedding Format** | Monkeypatch `HuggingfaceEmbeddingHandler` | Use provider-specific config | 🔴 **Non-Compliant** |
| **Admin Security** | Monkeypatch `_can_user_query_key_info` | Use RBAC / Teams features | 🔴 **Non-Compliant** |
| **Patch Injection** | `sitecustomize.py` | N/A (Python feature, not LiteLLM feature) | 🟡 **Unofficial** |

### 2.2 Justification for Deviation
The patches are retained because they address issues where the "Official Recommendation" failed during testing on v1.81.0:
1.  **Auth Bug:** `include_subpath: true` failed to honor `auth: false` in this version.
2.  **Output Format:** Hugging Face embeddings returned raw lists instead of the OpenAI-compatible structure required by downstream clients.
3.  **Security:** Stricter key isolation was required than what the default RBAC provided.

## 3. Risk Assessment
*   **High Risk:** Upgrade Friction. Future LiteLLM versions may rename internal functions (`auth_checks.get_actual_routes`), causing patches to silently fail or crash the application.
*   **Medium Risk:** Behavior Divergence. The system behaves differently than a standard LiteLLM instance, potentially confusing operators relying solely on public docs.

## 4. Recommendations
1.  **Freeze Version:** Continue pinning `litellm==1.81.0` to ensure patch stability.
2.  **Upstream Reporting:** Verify if these bugs are fixed in the latest release (v1.80.8-stable mentioned in docs seems older, but v1.81.0 is installed?). *Note: Version numbering seems inconsistent in local docs; verify actual latest upstream.*
3.  **Retire Patches:** Periodically attempt to disable `sitecustomize.py` and run `bin/run_e2e_test.sh` to see if native configuration can now handle the requirements.

## 5. Conclusion
The patching mechanism is a **necessary violation** of standard practices to maintain operational stability. It is correctly identified and managed as Technical Debt.

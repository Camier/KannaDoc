# Resolving Technical Debt: Runtime Patches

This document outlines the plan to retire the custom runtime patches in `utils/litellm_patches.py` by adopting official LiteLLM features and best practices.

**Current Status:** ✅ **0 Patches Active** (All Retired).
**Target:** 0 Patches (Native Configuration).

---

## 1. `apply_passthrough_auth_patch`
**Status:** ✅ **RETIRED** (Jan 19, 2026)
**Resolution:** Replaced by explicit subpath listing in `config.yaml` under `pass_through_endpoints`. This avoids the `include_subpath: true` bug by defining each required endpoint individually with `auth: false`.

## 2. `apply_hf_embedding_vector_patch`
**Status:** ✅ **RETIRED** (Jan 19, 2026)
**Resolution:** Migrated embedding model to `ollama/snowflake-arctic-embed2`. Verified that LiteLLM natively returns OpenAI-compatible response structures when using the `ollama/` provider.

## 3. `apply_db_model_env_ref_patch`
**Status:** ✅ **RETIRED** (Jan 19, 2026)
**Resolution:** Dead code removed.

## 4. `apply_route_checks_http_exception_patch`
**Status:** ✅ **RETIRED** (Jan 19, 2026)
**Resolution:** Reverted to default LiteLLM error handling.

## 5. `apply_key_info_admin_only_patch`
**Status:** ✅ **RETIRED** (Jan 19, 2026)
**Resolution:** Native LiteLLM access control (using `LITELLM_MASTER_KEY` and `ui_access_mode: admin_only`) provides sufficient security. Special "check own key" behavior is supported natively or via official CLI tools.

---

## Execution Log

- **Jan 19, 2026:**
  - Audit reveals `apply_db_model_env_ref_patch` is dead code. Removed.
  - Removed `apply_route_checks_http_exception_patch`.
  - Replaced `apply_passthrough_auth_patch` with explicit `config.yaml` routes.
  - Replaced `apply_hf_embedding_vector_patch` with native `ollama/` provider configuration.
  - Removed `apply_key_info_admin_only_patch` in favor of native LiteLLM security.
  - **Result:** Monkeypatching mechanism (`sitecustomize.py`) disabled. System now compliant with strict official documentation.
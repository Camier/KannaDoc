# Drift Resolution Report: "Hidden" Configuration Corruption

**Date:** January 17, 2026
**Investigator:** Gemini Agent
**Status:** ✅ **RESOLVED**

## 1. Executive Summary
A deep investigation into "considered working" settings revealed a critical corruption in the LiteLLM database. Several local models, including the primary embedding service (`embeddings-default`), had their `custom_llm_provider` field stored as **encrypted ciphertext** instead of plain text. This caused LiteLLM to fail silently or generate malformed requests (e.g., `input: null`) to backend services like `llama.cpp`.

## 2. Findings

### A. The "Blind Spot"
- **Symptom:** `bin/probe_capabilities.py` failed for `embeddings-default` with `500 Internal Server Error`.
- **Log Evidence:** `logs/llama_arctic_embed.log` showed `[json.exception.type_error.302] type must be string, but is null`.
- **Root Cause:** The database contained corrupted values:
    ```json
    "custom_llm_provider": "BapxNgp_vs_WqcjFswh-NjbHM2Ki1AtC7qgOp06zD2YhASy_sP4wbf6Z1uH0Nw=="
    ```
    This prevented LiteLLM from correctly identifying the provider as `openai` and formatting the request body.

### B. Patch Status
- **Verification:** Confirmed active via `litellm_with_patches.py` logic and `logs/litellm.service.log` (implicit via successful startup).
- **Technical Debt:** Patches are version-locked to `1.80.16`. Upgrading LiteLLM requires manual verification of `utils/litellm_patches.py`.

### C. Missing Inventory
- **Issue:** `model_inventory_report.py` initially failed to list `arctic` models because the capability probe inferred the wrong mode (`chat` instead of `embedding`) due to the corrupted provider metadata preventing correct classification.

## 3. Resolution Actions

1.  **Created Remediation Tool:** Developed `bin/fix_encrypted_providers.py` to decrypt `custom_llm_provider` and `encoding_format` fields using `LITELLM_SALT_KEY`.
2.  **Executed Fix:**
    - Decrypted `embeddings-default` -> `openai`
    - Decrypted `llamacpp-local` -> `openai`
    - Decrypted `ollama-embed-text` -> `openai`
    - Decrypted `rerank-default` -> `cohere`
3.  **Verified:**
    - Re-ran `bin/probe_capabilities.py`.
    - Result: `embeddings-default` now returns **200 OK** with 1024-dim embeddings.

## 4. Recommendations

- **Monitoring:** Add a check to `bin/audit_consistency.py` to alert if `custom_llm_provider` contains characters typical of ciphertext (`==`, `_`).
- **Maintenance:** When upgrading LiteLLM, check `utils/litellm_patches.py` immediately.
- **Backup:** The database is now clean; consider a fresh snapshot.
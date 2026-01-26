# Session Summary: System Hardening, Audit & Cleanup

**Date:** January 17, 2026
**Agent:** Gemini
**Status:** ✅ **SUCCESS**

This document summarizes the actions taken to audit, repair, harden, and optimize the LiteLLM Proxy infrastructure.

## 1. Critical Repairs

### A. The "Encrypted Provider" Bug
- **Issue:** Several local models (including `embeddings-default`) had their `custom_llm_provider` field stored as encrypted ciphertext in the DB, causing `500` errors.
- **Fix:** Decrypted and normalized fields to `openai` directly in the database.
- **Result:** `embeddings-default` is now **200 OK**.

### B. UI Authentication (500 Error)
- **Issue:** Login failed with `500` because `store_model_in_db: true` required the `admin` user to exist in the DB (foreign key check), but it was only in env vars.
- **Fix:** Bootstrapped the `admin` user into the `LiteLLM_UserTable`.
- **Result:** Login with `admin` / `lol` is functional.

## 2. Infrastructure Optimization (VRAM)

### A. "Just-in-Time" Loading
- **Issue:** Multiple systemd services (`litellm-embed-arctic`, `llama-embed`, `ollama`) were auto-starting, saturating VRAM at boot.
- **Fix:**
    - Disabled **ALL** heavy GPU services at boot.
    - Configured Ollama models with `keep_alive: 5m` to auto-unload.
    - Renamed/Consolidated duplicate services (`llama-embed.service` replaced by optimized `litellm-embed-arctic.service`).
- **Result:** Boot consumes ~0GB VRAM. You launch models only when needed.

## 3. Model Inventory Overhaul

### A. Nomenclature Standardization
- **Action:** Renamed all local models to `[type]-[name]-[engine]` for clarity.
    - `llamacpp-local` -> `chat-hermes-3-llama-3.1-8b`
    - `vllm-qwen2.5-0.5b-instruct` -> `chat-qwen2.5-0.5b-vllm`
    - `ollama-mistral` -> `chat-mistral-7b-ollama`
    - etc.
- **Config:** Updated `config.yaml` fallbacks to match new names.

### B. Resilience & Safety
- **Fallbacks:** `chat-default` points to local Hermes 3, but falls back to **Ollama Cloud** (`qwen3-coder-480b-cloud`) if local is off. This works seamlessly.
- **Safety:** All local models patched with `timeout: 120s` and `rpm: 10-60` to prevent hangs.
- **Vision:** `vision-qwen3-vl-4b-ollama` patched with `max_tokens: 4096`.

## 4. Post-Reboot Verification Guide

1.  **Start Proxy:** `systemctl --user start litellm`
2.  **Verify:** `python3 /LAB/@litellm/bin/smoke_validate.py`
3.  **Use Cloud:** `chat-default` works immediately (via fallback).
4.  **Use Local:**
    *   **Embed:** `systemctl --user start litellm-embed-arctic`
    *   **Chat:** `bash bin/start_llamacpp.sh`

---
**Handover:** The system is clean, documented, VRAM-optimized, and resilient.
# LiteLLM Model Endpoint Test Report

**Generated:** 2026-01-21 08:50 CET  
**Proxy URL:** http://127.0.0.1:4000  
**Total Models Configured:** 11

## Executive Summary

**CRITICAL:** ALL 11 models FAILED.

### Root Cause Analysis

| Issue Type | Affected Models | Details |
|------------|----------------|---------|
| **Port Mismatch** | 5 ollama models | Ollama running on 11434, config has 11435 |
| **Missing API Keys** | 3 models | OPENAI_API_KEY not set for TGI/Arctic |
| **Backend Not Running** | 2 models | vLLM (11436), Rerank (8079) down |
| **Cloud API Error** | 1 model | qwen3-coder-480b-cloud connection failed |

---

## Detailed Test Results

| Model Name | Status | Time (s) | Error |
|------------|--------|----------|-------|
| chat-default | ERROR | 0.41 | `AuthenticationError: OpenAIException - api_key client option must be set` |
| chat-gemma3-1b-ollama | ERROR | 9.64 | `APIConnectionError: OllamaException - Cannot connect to Ollama` |
| chat-hermes-3-llama-3.1-8b | ERROR | 35.67 | `AuthenticationError: OpenAIException - api_key client option must be set` |
| chat-llama3.2-1b-ollama | ERROR | 9.55 | `APIConnectionError: OllamaException - Cannot connect to Ollama` |
| chat-mistral-7b-ollama | ERROR | 9.66 | `APIConnectionError: OllamaException - Cannot connect to Ollama` |
| chat-qwen2.5-0.5b-vllm | ERROR | 46.74 | `InternalServerError: Hosted_vllm error` |
| chat-qwen3-coder-30b-ollama | ERROR | 46.90 | `APIConnectionError: OllamaException - Cannot connect to Ollama` |
| embed-arctic-l-v2 | ERROR | 0.21 | `AuthenticationError: OpenAIException - api_key client option must be set` |
| local-rerank | ERROR | 8.47 | `InternalServerError: CohereException - Cannot connect to rerank service` |
| qwen3-coder-480b-cloud | ERROR | 37.52 | `APIConnectionError: OllamaException - {"error":"model not found"}` |
| vision-qwen3-vl-4b-ollama | ERROR | 8.60 | `APIConnectionError: OllamaException - Cannot connect to Ollama` |

---

## Backend Service Status

| Service | Expected Port | Actual Status | Notes |
|---------|---------------|---------------|-------|
| Ollama | 11435 | 11434 (RUNNING) | **Port mismatch** - Ollama on default 11434 |
| vLLM | 11436 | DOWN | Service not running |
| TGI (Hermes) | 8002 | DOWN | Missing OPENAI_API_KEY |
| Arctic Embeddings | 8082 | DOWN | Missing OPENAI_API_KEY |
| Rerank | 8079 | DOWN | `rerank.service` inactive |
| LiteLLM Proxy | 4000 | RUNNING | Proxy healthy |

---

## Working Models List

**NONE** - All 11 models failed testing.

---

## Failed Models with Errors

### By Error Type

#### 1. Port Configuration Errors (Ollama)
Models affected:
- chat-gemma3-1b-ollama
- chat-llama3.2-1b-ollama
- chat-mistral-7b-ollama
- chat-qwen3-coder-30b-ollama
- vision-qwen3-vl-4b-ollama

**Fix:** Update `api_base` from `http://127.0.0.1:11435` to `http://127.0.0.1:11434`

#### 2. Missing API Keys
Models affected:
- chat-default (TGI backend on port 8002)
- chat-hermes-3-llama-3.1-8b (TGI backend on port 8002)
- embed-arctic-l-v2 (Arctic on port 8082)

**Fix:** Set `OPENAI_API_KEY` environment variable or configure in model params

#### 3. Backend Services Not Running
Models affected:
- chat-qwen2.5-0.5b-vllm (vLLM on port 11436)
- local-rerank (Rerank on port 8079)

**Fix:** Start respective backend services

#### 4. Cloud API Error
Models affected:
- qwen3-coder-480b-cloud

**Fix:** Verify Ollama Cloud credentials and model availability

---

## Recommendations

### Immediate Actions

1. **Fix Ollama Port Configuration**
   ```sql
   UPDATE "LiteLLM_ProxyModelTable" 
   SET litellm_params = jsonb_set(
     litellm_params, 
     '{api_base}', 
     '"http://127.0.0.1:11434"'
   )
   WHERE litellm_params->>'api_base' = 'http://127.0.0.1:11435';
   ```

2. **Set OPENAI_API_KEY** for TGI/Arctic backends
   ```bash
   # Add to env.litellm or systemd EnvironmentFile
   OPENAI_API_KEY=sk-your-key-here
   ```

3. **Start vLLM Service**
   ```bash
   systemctl start vllm@qwen2.5-0.5b
   ```

4. **Start Rerank Service**
   ```bash
   systemctl start litellm-rerank
   ```

### Configuration Issues to Address

| Issue | File | Line | Fix |
|-------|------|------|-----|
| Ollama port mismatch | Database | `litellm_params` | Update api_base to 11434 |
| Missing master key | env.litellm | LITELLM_MASTER_KEY | Set valid key |
| TGI/Arctic auth | env.litellm | OPENAI_API_KEY | Set valid key |
| vLLM not running | systemd | vllm service | Enable and start |
| Rerank not running | systemd | litellm-rerank | Enable and start |

---

## Test Methodology

For each model:
1. Sent request to `http://127.0.0.1:4000/v1/chat/completions` (or `/v1/embeddings` for embeddings)
2. Used valid API key from environment
3. Payload: `{"model": "<name>", "messages": [{"role": "user", "content": "Say OK in 3 words or less."}], "max_tokens": 10}`
4. Measured response time
5. Categorized results as WORKING, ERROR, or UNKNOWN

---

## API Key Used for Testing

**Key:** `sk-rox0Kj3q4YmDFNx-ZfoNtA` (alias: `opencode-client`)  
**Source:** ~/.007 (LITELLM_OPENCODE_KEY)  
**Status:** Valid - authenticates successfully with proxy

---

*Report generated by automated LiteLLM model testing suite*

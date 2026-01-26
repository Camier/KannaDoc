# Fixing 4 Failing Models - Action Plan

**Diagnosis Date:** 2026-01-23  
**Current Status:** 14/18 models working (78%)  
**Goal:** 18/18 models working (100%)

---

## Current State Analysis

### ✅ What's Working
- Ollama is running on localhost:11434 with 31 models
- Including: `llama3.1:latest`, `llama3.2:latest`, and many others
- Docker networking to host working (host.docker.internal)

### ❌ What's Failing (4 Models)

| Model | Issue | Solution |
|-------|-------|----------|
| `llama3.1-test` | Config mismatch | Fix model reference in config.yaml |
| `gemini-1.5-flash` | No API key | Add GEMINI_API_KEY to .env |
| `gemini-1.5-pro` | No API key | Add GEMINI_API_KEY to .env |
| `embed-arctic-l-v2` | llama.cpp not running | Start llama.cpp server on port 8082 |

---

## SOLUTION 1: Fix llama3.1-test

### Problem
Config says `ollama_chat/llama3.1:latest` but network connectivity is fine.
The auth error suggests it's trying but the model reference might be wrong.

### Solution A: Update config.yaml to match actual model name

**Current:**
```yaml
- model_name: llama3.1-test
  litellm_params:
    model: ollama_chat/llama3.1:latest
    api_base: http://host.docker.internal:11434
```

**Change to:**
```yaml
- model_name: llama3.1-test
  litellm_params:
    model: ollama/llama3.1:latest
    api_base: http://host.docker.internal:11434
```

Or use the verified model that exists:
```yaml
- model_name: llama3.1-test
  litellm_params:
    model: ollama/llama3.1
    api_base: http://host.docker.internal:11434
```

---

## SOLUTION 2 & 3: Fix Gemini Models

### Problem
No GEMINI_API_KEY set in .env

### Solution
Get Gemini API key and add to .env:

```bash
# 1. Go to https://aistudio.google.com/
# 2. Create an API key (free tier available)
# 3. Add to .env:
GEMINI_API_KEY=your_key_here

# 4. Restart:
docker compose restart
```

---

## SOLUTION 4: Fix embed-arctic-l-v2 (Embeddings)

### Problem
llama.cpp server not running on port 8082

### Solution: Start llama.cpp server

#### Option A: Docker Container (Recommended)
```bash
docker run -d \
  --name llama-cpp-server \
  -p 8082:8000 \
  --restart unless-stopped \
  ghcr.io/abetlen/llama-cpp-python:latest \
  --model-url https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B-GGUF/resolve/main/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8000
```

#### Option B: Manual (if binary available)
```bash
./server -m arctic-l-v2.gguf -p 8082
```

#### Option C: Use Ollama's embedding (simpler)
Change config.yaml to use Ollama's built-in embeddings:

**Current:**
```yaml
- model_name: embed-arctic-l-v2
  litellm_params:
    model: openai/embed-arctic-l-v2
    api_base: http://host.docker.internal:8082
```

**Change to (use Ollama):**
```yaml
- model_name: embed-arctic-l-v2
  litellm_params:
    model: ollama/nomic-embed-text:latest
    api_base: http://host.docker.internal:11434
```

---

## Implementation Steps

### Step 1: Fix llama3.1-test (2 minutes)
```bash
# Edit config.yaml
# Change: model: ollama_chat/llama3.1:latest
# To: model: ollama/llama3.1

docker compose restart
sleep 30
python3 bin/probe_models.py | grep llama3.1-test
```

### Step 2: Add Gemini API Key (5 minutes)
```bash
# 1. Get key from https://aistudio.google.com/
# 2. Edit .env and add: GEMINI_API_KEY=your_key_here
# 3. Restart:
docker compose restart
sleep 30
python3 bin/probe_models.py | grep gemini
```

### Step 3: Fix Embeddings (10 minutes - Option C is simplest)
```bash
# Option C: Use Ollama embeddings (already running)
# Edit config.yaml:
# Change embed-arctic-l-v2 to point to: ollama/nomic-embed-text:latest

docker compose restart
sleep 30
python3 bin/probe_models.py | grep embed-arctic
```

---

## Testing After Each Fix

```bash
# After each change:
docker compose restart litellm
sleep 30

# Test specific model:
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -X POST http://localhost:4000/chat/completions \
  -d '{"model":"llama3.1-test","messages":[{"role":"user","content":"test"}],"max_tokens":1}'

# Or run full probe:
python3 bin/probe_models.py
```

---

## Expected Results After All Fixes

```
✅ llama3.1-test           ✅ (Ollama local)
✅ gemini-1.5-flash        ✅ (API key set)
✅ gemini-1.5-pro          ✅ (API key set)
✅ embed-arctic-l-v2       ✅ (Ollama embeddings)

TOTAL: 18/18 models working (100%)
```

---

## Rollback Plan

If anything breaks:
```bash
# Restore config.yaml from backup
cp config.yaml.backup.1769184210 config.yaml

# Restore .env from backup
cp .env.backup.1769184210 .env

# Restart
docker compose restart
```

---

## Priority & Effort Estimate

| Model | Effort | Priority | Impact |
|-------|--------|----------|--------|
| llama3.1-test | 2 min | HIGH | Local model testing |
| gemini-1.5-flash | 5 min | MEDIUM | Alternative provider |
| gemini-1.5-pro | 5 min | MEDIUM | Alternative provider |
| embed-arctic-l-v2 | 10 min | LOW | Fallback embeddings |

**Total effort:** ~20 minutes  
**Result:** 100% model availability

---

## Quick Reference: What to Change

### config.yaml Changes
```diff
- model: ollama_chat/llama3.1:latest
+ model: ollama/llama3.1

- model: openai/embed-arctic-l-v2
- api_base: http://host.docker.internal:8082
+ model: ollama/nomic-embed-text:latest
+ api_base: http://host.docker.internal:11434
```

### .env Changes
```diff
+ GEMINI_API_KEY=your_actual_key_here
```

---

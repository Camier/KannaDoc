# Model Management Guide

This guide explains how to manage models in the LiteLLM Proxy. SSOT details are in `docs/OPERATIONAL_BASELINE.md`.

## 1. Overview
Models are managed in `config.yaml`. This allows for:
- Transparent, versionable model definitions.
- Consistent routing and fallbacks in a single file.
- Explicit review of provider credentials references (`os.environ/VAR`).

---

## 2. Editing `config.yaml`
Add, edit, or remove models in the `model_list` section.

---

### Example: Add a Model
```yaml
  - model_name: deepseek-v3
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
    model_info:
      mode: chat
```

Restart the proxy after changes.

---

## 5. Provider Specifics

### 5.1 Zai / ZhipuAI (Coding Plan)
To use the GLM Coding Plan quota, models must be configured with the dedicated coding endpoint.

**Models:** `GLM-4.7`, `GLM-4.6`, `GLM-4.5`, `GLM-4.5-Air`

**Configuration:**
```bash
curl -X POST "http://127.0.0.1:4000/model/new" \
     -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model_name": "zai-glm-4.7",
       "litellm_params": {
         "model": "openai/GLM-4.7",
         "api_key": "os.environ/ZHIPUAI_API_KEY",
         "api_base": "os.environ/ZHIPUAI_CODING_BASE"
       },
       "model_info": { "mode": "chat", "provider": "zhipu" }
     }'
```
**Env Vars:**
- `ZHIPUAI_API_KEY`: Your Zai API Key.
- `ZHIPUAI_CODING_BASE`: `https://api.z.ai/api/coding/paas/v4`

---

## 4. Operational Maintenance

### 4.1 Handling Environment Variables
Use the `os.environ/VARIABLE_NAME` syntax for API keys in `config.yaml`. Store actual values in `.env` or `~/.007`.

### 4.2 Admin UI
The Admin UI is still used for keys/teams/spend and diagnostics:
- URL: `http://127.0.0.1:4000/ui`
- Login: `LITELLM_MASTER_KEY`

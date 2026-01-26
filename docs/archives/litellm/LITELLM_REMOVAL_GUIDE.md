# LiteLLM Removal Migration Guide

**Date:** 2026-01-25  
**Status:** ✅ Complete - Ready to Deploy

---

## What Changed?

Layra no longer depends on the LiteLLM proxy service. All LLM API calls now go **directly to providers** (OpenAI, DeepSeek, Anthropic, etc.).

### Before (with LiteLLM)
```
[Layra Backend] → [LiteLLM Proxy :4000] → [Provider APIs]
                   (3 extra containers)
                   (separate network)
```

### After (Direct)
```
[Layra Backend] → [Provider APIs]
                  (no middleware)
```

---

## Benefits

✅ **3 fewer containers** (litellm-proxy, postgres, redis)  
✅ **No network isolation issues** (was causing workflow failures)  
✅ **Simpler debugging** (direct error messages from providers)  
✅ **Fewer secrets to manage** (no master keys)  
✅ **Easier deployment** (one docker-compose command)

---

## Migration Steps

### 1. Add Provider API Keys to .env

Edit `/LAB/@thesis/layra/.env` and add your provider keys:

```bash
# LLM PROVIDER CONFIGURATION
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...  # Optional
# GEMINI_API_KEY=AIza...         # Optional

# Default provider for new users
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini
```

**Where to get keys:**
- OpenAI: https://platform.openai.com/api-keys
- DeepSeek: https://platform.deepseek.com/api_keys
- Anthropic: https://console.anthropic.com/settings/keys
- Gemini: https://aistudio.google.com/app/apikey

### 2. Run Migration Script (If System Was Running)

If you have existing users in MongoDB with LiteLLM configs:

```bash
cd /LAB/@thesis/layra
docker-compose up -d mongodb mysql
sleep 5  # Wait for DB to start

# Run migration
docker exec layra-backend python backend/scripts/migrate_from_litellm.py
```

This will:
- Find all `model_config` documents with `litellm-proxy` URLs
- Update them to use direct provider APIs
- Set appropriate API keys from environment

### 3. Restart Layra

```bash
cd /LAB/@thesis/layra
docker-compose down
docker-compose up -d
```

Or if using thesis deployment:
```bash
cd /LAB/@thesis/layra/deploy
docker-compose -f docker-compose.thesis.yml down
docker-compose -f docker-compose.thesis.yml up -d
```

### 4. Verify

Test chat functionality:
```bash
# Check logs
docker logs layra-backend -f

# Test API
curl -X POST http://localhost:8090/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "conversation_id": "test"}'
```

---

## New User Creation

When creating new users, the script now uses direct provider APIs:

```bash
cd /LAB/@thesis/layra
docker exec layra-backend python backend/scripts/change_credentials.py USERNAME PASSWORD
```

The user will get:
- `model_name`: Value from `DEFAULT_LLM_MODEL` (default: gpt-4o-mini)
- `model_url`: Empty string (auto-detects provider)
- `api_key`: Value from provider-specific env var

---

## Code Changes Summary

### 1. New Provider Client (`backend/app/rag/provider_client.py`)

Auto-detects provider from model name and creates appropriate API client:

```python
from app.rag.provider_client import get_llm_client

# Auto-detect provider from model name
client = get_llm_client("gpt-4o")  # → OpenAI client
client = get_llm_client("deepseek-reasoner")  # → DeepSeek client
```

### 2. Updated LLM Services

Both `app/rag/llm_service.py` and `app/workflow/llm_service.py` now:
- Check if `model_url` is provided (legacy support)
- If empty/not HTTP, auto-detect provider from `model_name`
- Use direct provider client

### 3. Updated Scripts

`backend/scripts/change_credentials.py`:
- Reads `DEFAULT_LLM_PROVIDER` and `DEFAULT_LLM_MODEL` from env
- Sets provider-specific API keys
- No longer references `litellm-proxy`

### 4. Docker Compose

`deploy/docker-compose.thesis.yml`:
- Removed `litellm_net` network
- Removed `litellm_net` from backend service

---

## Troubleshooting

### API Key Not Found

**Error:**
```
ValueError: API key for openai not found. Set OPENAI_API_KEY environment variable.
```

**Fix:**
1. Add key to `.env`:
   ```bash
   OPENAI_API_KEY=sk-proj-...
   ```
2. Restart backend:
   ```bash
   docker-compose restart backend
   ```

### Model Not Recognized

**Error:**
```
Unknown model provider for 'custom-model', defaulting to OpenAI
```

**Fix:**
Add model pattern to `provider_client.py`:
```python
PROVIDERS = {
    "custom": {
        "base_url": "https://api.custom.com/v1",
        "env_key": "CUSTOM_API_KEY",
        "models": ["custom-model", "custom-*"]
    }
}
```

### Legacy LiteLLM URL Still in DB

**Error:**
```
Connection refused to litellm-proxy:4000
```

**Fix:**
Re-run migration script:
```bash
docker exec layra-backend python backend/scripts/migrate_from_litellm.py
```

---

## Rollback (If Needed)

If you need to rollback to LiteLLM:

1. Revert code changes:
   ```bash
   cd /LAB/@thesis/layra
   git checkout HEAD~1 backend/app/rag/llm_service.py
   git checkout HEAD~1 backend/app/workflow/llm_service.py
   git checkout HEAD~1 backend/scripts/change_credentials.py
   ```

2. Restore network in docker-compose:
   ```bash
   git checkout HEAD~1 deploy/docker-compose.thesis.yml
   ```

3. Start LiteLLM:
   ```bash
   cd /LAB/@litellm
   docker-compose up -d
   ```

4. Restart Layra:
   ```bash
   cd /LAB/@thesis/layra
   docker-compose restart
   ```

---

## FAQ

### Q: Do I need to keep `/LAB/@litellm/` directory?

A: You can keep it if you use LiteLLM for other projects. Layra no longer needs it.

### Q: Can I use multiple providers?

A: Yes! Set multiple API keys in `.env`. The provider is auto-detected from model name.

### Q: What if I want to use a custom provider?

A: Edit `backend/app/rag/provider_client.py` and add your provider config.

### Q: Do workflows still work?

A: Yes! Workflows use the same LLM service, so they automatically use direct providers.

---

## Next Steps

1. ✅ Migration complete
2. 📝 Update workflow JSONs if they reference specific models
3. 🧪 Test chat + workflows thoroughly
4. 📊 Monitor logs for any provider errors
5. 🗑️ Optional: Clean up `/LAB/@litellm/` if not used elsewhere

---

**Questions?** Check `docs/LITELLM_ANALYSIS.md` for full technical details.

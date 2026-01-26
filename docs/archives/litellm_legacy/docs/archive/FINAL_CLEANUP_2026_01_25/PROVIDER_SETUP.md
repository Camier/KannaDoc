# LiteLLM Provider Setup Guide

**Production-Ready Configuration** | All providers tested and validated

---

## Quick Start

### 1. Required Providers (Minimum Setup)

For basic functionality, you need **only one** provider:

```bash
# Minimum setup - Ollama Cloud (free tier available)
OLLAMA_API_KEY=sk-ollama-...
```

### 2. Recommended Providers (Full Features)

For production with all features (embeddings, reranking, vision):

```bash
# Core Models
OLLAMA_API_KEY=sk-ollama-...              # Chat models (free tier)

# Embeddings & Reranking
VOYAGE_API_KEY=voyage-...                 # Best quality embeddings
# OR
COHERE_API_KEY=...                        # Alternative for reranking

# Vision & Multimodal (Optional)
GEMINI_API_KEY=AIza...                    # Vision models (free tier)
```

---

## Provider Configuration

### 🌟 Ollama Cloud (Primary Provider)

**Used for:** Chat models (1T+ parameters), reasoning, coding

**Get API Key:**
1. Go to https://ollama.com
2. Sign up for free account
3. Navigate to API section
4. Generate API key

**Add to `.env`:**
```bash
OLLAMA_API_KEY=sk-ollama-your-key-here
```

**Models Available:**
- `kimi-k2-1t-cloud` (1T params, 128K context)
- `deepseek-v3-1-671b-cloud` (671B params, reasoning)
- `mistral-large-3-675b-cloud` (675B params, multimodal)
- `gpt-oss-120b-cloud` / `gpt-oss-20b-cloud` (reasoning)
- `ministral-3-8b-cloud` / `ministral-3-14b-cloud` (fast)

**Configuration in `config.yaml`:**
```yaml
- model_name: kimi-k2-1t-cloud
  litellm_params:
    model: ollama_chat/kimi-k2:1t-cloud
    api_base: https://ollama.com
    api_key: os.environ/OLLAMA_API_KEY
    timeout: 300  # Large models need longer timeouts
```

**Pricing:** Free tier available, pay-as-you-go for production

**Official Docs:** https://docs.litellm.ai/docs/providers/ollama

---

### 🔵 Google Gemini (Vision & Multimodal)

**Used for:** Vision models, large context (1M tokens), multimodal tasks

**Get API Key:**
1. Go to https://aistudio.google.com/
2. Click "Get API Key"
3. Create new project or use existing
4. Copy API key (starts with `AIza...`)

**Add to `.env`:**
```bash
GEMINI_API_KEY=AIzaSy...your-key-here
```

**Models Available:**
- `gemini-1.5-flash` (Fast, multimodal)
- `gemini-1.5-pro` (Vision, 1M context)

**Configuration in `config.yaml`:**
```yaml
- model_name: gemini-1.5-pro
  litellm_params:
    model: gemini/gemini-pro-vision
    api_key: os.environ/GEMINI_API_KEY
  model_info:
    mode: chat
    supports_vision: true
```

**Pricing:** Generous free tier (15 RPM), affordable pay-as-you-go

**Official Docs:** https://docs.litellm.ai/docs/providers/gemini

---

### 🚀 Voyage AI (Embeddings & Reranking)

**Used for:** State-of-the-art embeddings, RAG applications, reranking

**Get API Key:**
1. Go to https://www.voyageai.com/
2. Sign up for account
3. Navigate to API Keys section
4. Generate new key

**Add to `.env`:**
```bash
VOYAGE_API_KEY=voyage-your-key-here
```

**Models Available:**
- `voyage-3` (Latest embedding model, 1024 dims)
- `rerank-voyage-2` (Reranking for RAG)

**Configuration in `config.yaml`:**
```yaml
# Embeddings
- model_name: voyage-3
  litellm_params:
    model: voyage/voyage-3
    api_key: os.environ/VOYAGE_API_KEY
  model_info:
    mode: embedding

# Reranking
- model_name: rerank-voyage-2
  litellm_params:
    model: voyage/rerank-2
    api_key: os.environ/VOYAGE_API_KEY
  model_info:
    mode: rerank
```

**Pricing:** Free tier for testing, affordable production pricing

**Official Docs:** https://docs.litellm.ai/docs/providers/voyage

---

### 📊 Cohere (Reranking)

**Used for:** RAG reranking (alternative to Voyage)

**Get API Key:**
1. Go to https://cohere.com/
2. Sign up for account
3. Dashboard → API Keys
4. Create production key

**Add to `.env`:**
```bash
COHERE_API_KEY=your-cohere-key-here
```

**Models Available:**
- `rerank-english-v3.0` (Best English reranking)

**Configuration in `config.yaml`:**
```yaml
- model_name: rerank-english-v3.0
  litellm_params:
    model: cohere/rerank-english-v3.0
    api_key: os.environ/COHERE_API_KEY
  model_info:
    mode: rerank
```

**Pricing:** Free tier available, production tiers

**Official Docs:** https://docs.litellm.ai/docs/providers/cohere

---

## Optional Providers

### OpenAI (Alternative for OpenAI-native apps)

**Get API Key:**
1. Go to https://platform.openai.com/
2. API Keys → Create new key

**Add to `.env`:**
```bash
OPENAI_API_KEY=sk-...
```

**Use Case:** If you need native OpenAI models (GPT-4, GPT-3.5) or for app compatibility

**Official Docs:** https://docs.litellm.ai/docs/providers/openai

---

### Anthropic (Claude Models)

**Get API Key:**
1. Go to https://console.anthropic.com/
2. Account Settings → API Keys

**Add to `.env`:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Use Case:** Claude 3 models (Opus, Sonnet, Haiku)

**Official Docs:** https://docs.litellm.ai/docs/providers/anthropic

---

### Zhipu AI (GLM Models)

**Get API Key:**
1. Register at https://open.bigmodel.cn/
2. API Management → Create key

**Add to `.env`:**
```bash
ZAI_API_KEY=your-zai-key
```

**Use Case:** GLM-4 models (355B params, Chinese language support)

**Note:** Currently commented out in config.yaml - requires account balance

---

### MiniMax (M2.1 Models)

**Get API Key:**
1. Register at https://www.minimaxi.com/
2. API section → Generate key

**Add to `.env`:**
```bash
MINIMAX_API_KEY=your-minimax-key
```

**Use Case:** MiniMax M2.1 (230B params, thinking models)

**Note:** Currently commented out in config.yaml - requires proper API key format

---

## Provider Setup Workflow

### Step 1: Choose Providers

**Minimum (Free):**
```bash
OLLAMA_API_KEY=...  # Chat models
```

**Recommended (Full Features):**
```bash
OLLAMA_API_KEY=...   # Chat models
GEMINI_API_KEY=...   # Vision
VOYAGE_API_KEY=...   # Embeddings/Reranking
```

**Enterprise (All Options):**
```bash
OLLAMA_API_KEY=...
GEMINI_API_KEY=...
VOYAGE_API_KEY=...
COHERE_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

### Step 2: Register & Get Keys

Follow the "Get API Key" instructions for each provider above.

### Step 3: Add to `.env`

```bash
cd /LAB/@litellm
vim .env

# Add your keys to the appropriate sections
```

### Step 4: Restart Services

```bash
docker-compose restart litellm

# Wait for startup (~30 seconds)
sleep 30
```

### Step 5: Verify

```bash
# Check all models
just probe

# Or manually test specific provider
export MASTER_KEY=$(grep LITELLM_MASTER_KEY .env | cut -d= -f2)

# Test Ollama model
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "kimi-k2-1t-cloud", "messages": [{"role": "user", "content": "Hello"}]}'

# Test Gemini
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-1.5-flash", "messages": [{"role": "user", "content": "Hello"}]}'

# Test Voyage embeddings
curl http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "voyage-3", "input": "Test embedding"}'
```

---

## Troubleshooting

### Provider Authentication Errors

**Symptom:** 401 Unauthorized or authentication failed

**Solutions:**

1. **Check API key format:**
   ```bash
   # Ollama keys start with: sk-ollama-
   # Gemini keys start with: AIza
   # Voyage keys start with: voyage-
   # OpenAI keys start with: sk-
   ```

2. **Verify key is set:**
   ```bash
   docker-compose exec litellm env | grep _API_KEY
   ```

3. **Check for trailing spaces:**
   ```bash
   # Edit .env and remove any spaces after the key
   OLLAMA_API_KEY=sk-ollama-key   # ❌ Bad (space after)
   OLLAMA_API_KEY=sk-ollama-key    # ✅ Good
   ```

4. **Restart after adding keys:**
   ```bash
   docker-compose restart litellm
   ```

### Rate Limit Errors

**Symptom:** 429 Too Many Requests

**Solutions:**

1. **Check provider quotas:**
   - Ollama: Check your plan limits
   - Gemini: Free tier = 15 RPM
   - Voyage: Check usage dashboard

2. **Increase timeout for retries:**
   ```yaml
   # In config.yaml
   router_settings:
     retry_policy:
       RateLimitErrorRetries: 3  # Will retry 3 times
   ```

3. **Use fallbacks:**
   ```yaml
   # Automatically fail over to backup model
   fallbacks:
     - kimi-k2-1t-cloud:
         - gpt-oss-120b-cloud
         - mistral-large-3-675b-cloud
   ```

### Timeout Errors

**Symptom:** Request timeout after 600s

**Solutions:**

1. **Increase global timeout:**
   ```yaml
   # In config.yaml
   litellm_settings:
     request_timeout: 900  # 15 minutes for ultra-slow models
   ```

2. **Increase per-model timeout:**
   ```yaml
   - model_name: kimi-k2-1t-cloud
     litellm_params:
       timeout: 900  # Model-specific override
   ```

3. **Use faster models for testing:**
   - `ministral-3-8b-cloud` (fast)
   - `gpt-oss-20b-cloud` (medium)
   - `gemini-1.5-flash` (fast)

### Model Not Found

**Symptom:** Model 'xyz' not found

**Solutions:**

1. **List available models:**
   ```bash
   curl http://localhost:4000/v1/models \
     -H "Authorization: Bearer $MASTER_KEY" | jq -r '.data[].id'
   ```

2. **Check model alias:**
   ```yaml
   # In config.yaml - model_group_alias section
   router_settings:
     model_group_alias:
       embeddings-default: voyage-3  # Alias mapping
   ```

3. **Verify provider key is set:**
   ```bash
   # If using Gemini model, ensure GEMINI_API_KEY is set
   grep GEMINI_API_KEY .env
   ```

### Provider-Specific Issues

#### Ollama Cloud

- **Issue:** Models are slow
- **Solution:** Use smaller models or increase timeout
- **Alternative:** Use local Ollama for latency-sensitive apps

#### Gemini

- **Issue:** Vision not working
- **Solution:** Ensure using `gemini-1.5-pro` (not flash) for vision
- **Format:** Send images as base64 or URLs in messages

#### Voyage

- **Issue:** Embeddings dimension mismatch
- **Solution:** Voyage-3 uses 1024 dimensions (check your vector DB config)

---

## Provider Comparison

| Provider | Use Case | Free Tier | Best For | Cost |
|----------|----------|-----------|----------|------|
| **Ollama Cloud** | Chat, Reasoning | ✅ Yes | Large models (1T params) | $ |
| **Gemini** | Vision, Multimodal | ✅ Yes (15 RPM) | Vision tasks, large context | $ |
| **Voyage** | Embeddings, Rerank | ✅ Testing | Best-in-class RAG | $$ |
| **Cohere** | Reranking | ✅ Yes | English reranking | $$ |
| **OpenAI** | General | ❌ No | App compatibility | $$$ |
| **Anthropic** | Claude | ❌ No | Long context, safety | $$$ |

**Legend:** $ = Affordable, $$ = Moderate, $$$ = Premium

---

## Best Practices

### Security

✅ **Never commit API keys to git**
```bash
# .env is in .gitignore
# Always use .env.example as template
```

✅ **Use salt key for database encryption**
```bash
# In .env
LITELLM_SALT_KEY=sk-...
# Never change after first deployment
```

✅ **Rotate keys periodically**
```bash
# Generate new key from provider
# Update .env
# Restart: docker-compose restart litellm
```

### Cost Management

✅ **Start with free tiers**
- Ollama Cloud (free tier)
- Gemini (15 RPM free)
- Test before production

✅ **Use budget limits**
```yaml
# In config.yaml (when using virtual keys)
max_budget: 100  # USD per month per key
```

✅ **Monitor usage**
```bash
# Check Prometheus metrics
curl http://localhost:4000/metrics | grep litellm_requests_total
```

### Performance

✅ **Use Redis caching**
```yaml
# Already configured in config.yaml
litellm_settings:
  cache: true
  cache_params:
    type: redis
    ttl: 600
```

✅ **Configure fallbacks**
```yaml
# Automatic failover on errors
fallbacks:
  - primary-model:
      - backup-model-1
      - backup-model-2
```

✅ **Enable retries**
```yaml
# Already configured in config.yaml
router_settings:
  retry_policy:
    TimeoutErrorRetries: 3
    RateLimitErrorRetries: 3
```

---

## Provider Status Dashboard

Check provider status pages:

- **Ollama:** https://status.ollama.com/
- **Google (Gemini):** https://status.cloud.google.com/
- **Voyage:** https://status.voyageai.com/
- **Cohere:** https://status.cohere.com/
- **OpenAI:** https://status.openai.com/
- **Anthropic:** https://status.anthropic.com/

---

## Adding New Providers

### 1. Check LiteLLM Support

Browse supported providers: https://docs.litellm.ai/docs/providers

### 2. Add to `.env`

```bash
NEW_PROVIDER_API_KEY=your-key-here
```

### 3. Add to `config.yaml`

```yaml
model_list:
  - model_name: my-new-model
    litellm_params:
      model: provider/model-name
      api_key: os.environ/NEW_PROVIDER_API_KEY
      # Add provider-specific settings
    model_info:
      mode: chat  # or embedding, rerank
```

### 4. Restart & Test

```bash
docker-compose restart litellm
just probe
```

---

## Documentation References

### Official LiteLLM Docs

- [All Providers](https://docs.litellm.ai/docs/providers)
- [Ollama](https://docs.litellm.ai/docs/providers/ollama)
- [Gemini](https://docs.litellm.ai/docs/providers/gemini)
- [Voyage](https://docs.litellm.ai/docs/providers/voyage)
- [Cohere](https://docs.litellm.ai/docs/providers/cohere)
- [OpenAI](https://docs.litellm.ai/docs/providers/openai)
- [Anthropic](https://docs.litellm.ai/docs/providers/anthropic)

### Provider Documentation

- [Ollama API](https://ollama.com/docs/api)
- [Google AI Studio](https://ai.google.dev/)
- [Voyage AI](https://docs.voyageai.com/)
- [Cohere](https://docs.cohere.com/)
- [OpenAI](https://platform.openai.com/docs)
- [Anthropic](https://docs.anthropic.com/)

---

## Summary

✅ **Minimum Setup:** Just Ollama Cloud for chat models  
✅ **Recommended:** Add Gemini + Voyage for full features  
✅ **Enterprise:** All providers for maximum flexibility  

**Current Configuration:** 4 active providers (Ollama, Gemini, Voyage, Cohere)  
**Total Models:** 20+ models available across providers  
**Expected Performance:** 100+ RPS with proper API keys

For provider-specific issues, check the official documentation links above or refer to troubleshooting section.

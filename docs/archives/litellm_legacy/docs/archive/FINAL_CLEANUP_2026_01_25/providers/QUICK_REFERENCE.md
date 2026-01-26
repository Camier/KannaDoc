# Provider Quick Reference Card

**Fast lookup for provider setup** | See [`PROVIDER_SETUP.md`](../../PROVIDER_SETUP.md) for details

---

## Getting API Keys

| Provider | Sign Up URL | Key Format | Free Tier |
|----------|------------|------------|-----------|
| **Ollama Cloud** | https://ollama.com | `sk-ollama-...` | ✅ Yes |
| **Google Gemini** | https://aistudio.google.com/ | `AIza...` | ✅ 15 RPM |
| **Voyage AI** | https://www.voyageai.com/ | `voyage-...` | ✅ Testing |
| **Cohere** | https://cohere.com/ | Various | ✅ Yes |
| **OpenAI** | https://platform.openai.com/ | `sk-...` | ❌ No |
| **Anthropic** | https://console.anthropic.com/ | `sk-ant-...` | ❌ No |

---

## Add to .env

```bash
# Minimum (Free)
OLLAMA_API_KEY=sk-ollama-...

# Recommended (Full Features)
GEMINI_API_KEY=AIza...
VOYAGE_API_KEY=voyage-...

# Optional (Enterprise)
COHERE_API_KEY=...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Restart Services

```bash
docker-compose restart litellm
sleep 30
just check
```

---

## Test Models

```bash
export MASTER_KEY=$(grep LITELLM_MASTER_KEY .env | cut -d= -f2)

# Ollama (Chat)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "kimi-k2-1t-cloud", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}'

# Gemini (Chat)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-1.5-flash", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}'

# Voyage (Embeddings)
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "voyage-3", "input": "Test"}'
```

---

## Common Issues

### 401 Unauthorized
- Check API key format (correct prefix)
- Verify key is in `.env`
- Restart: `docker-compose restart litellm`

### 429 Rate Limit
- Check provider quota (Gemini free = 15 RPM)
- Wait or upgrade plan
- Use fallback models

### Model Not Found
- List models: `curl http://localhost:4000/v1/models -H "Authorization: Bearer $MASTER_KEY"`
- Check provider key is set
- Verify model name in `config.yaml`

---

## Provider Status

- Ollama: https://status.ollama.com/
- Google: https://status.cloud.google.com/
- Voyage: https://status.voyageai.com/
- Cohere: https://status.cohere.com/
- OpenAI: https://status.openai.com/
- Anthropic: https://status.anthropic.com/

---

**📚 Full Guide:** [`PROVIDER_SETUP.md`](../../PROVIDER_SETUP.md)

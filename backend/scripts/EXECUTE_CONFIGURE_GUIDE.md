# DeepSeek and GLM Model Configuration Guide

## Script Overview

The `configure_deepseek_glm.py` script properly configures DeepSeek and GLM models for Layra users.

### Models Configured

**DeepSeek Models:**
- `deepseek-chat` - Standard DeepSeek chat model
- `deepseek-reasoner` - DeepSeek R1 reasoning model
- `deepseek-v3.2` - Latest DeepSeek V3.2 model

**GLM Models:**
- `glm-4.7` - GLM-4.7 model (default)
- `glm-4-plus` - Enhanced GLM-4 Plus model
- `glm-4-flash` - Fast GLM-4 Flash model

### Configuration Details

Each model is configured with:
- **Provider identifier** (deepseek/zai)
- **API key** from environment variables
- **Provider SSOT resolution** via `backend/app/core/llm/providers.yaml`
- **Default parameters** (temperature, max_length, etc.)

## Prerequisites

1. **API Keys Required:**
   - `DEEPSEEK_API_KEY` - Set in `.env` file
   - `ZAI_API_KEY` - Set in `.env` file

2. **Database Access:**
   - MongoDB running and accessible
   - Valid MongoDB credentials in `.env`

## Execution Methods

### Method 1: Docker Compose Execution (Recommended)

Run the script within the Docker backend container:

```bash
# From project root
docker-compose exec backend python /app/scripts/configure_deepseek_glm.py
```

### Method 2: Direct Python Execution

If MongoDB is accessible locally:

```bash
cd /LAB/@thesis/layra/backend
python3 scripts/configure_deepseek_glm.py
```

### Method 3: Docker Network Execution

Execute script with Docker network access:

```bash
docker-compose run --rm backend python /app/scripts/configure_deepseek_glm.py
```

## What the Script Does

For each user (miko, thesis):

1. **Checks existing configuration**
   - If user config exists: Updates/adds models
   - If no config exists: Creates new config

2. **Configures each model:**
   - Sets correct `model_name` (exact API model name)
   - Sets correct `model_url` (provider API endpoint)
   - Sets correct `api_key` (from environment)
   - Sets correct provider-specific parameters

3. **Sets default model:**
   - Default: `glm-4.7` (selected_model)

## Verification

After execution, verify configurations:

```bash
# Check MongoDB for model configurations
docker-compose exec mongodb mongosh -u thesis -p thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac --authenticationDatabase admin chat_mongodb --eval "db.model_config.find().pretty()"
```

Expected output structure:
```javascript
{
  "_id": ObjectId("..."),
  "username": "thesis",
  "selected_model": "thesis_glm-4.7",
  "models": [
    {
      "model_id": "thesis_deepseek-chat",
      "model_name": "deepseek-chat",
      "model_url": "https://api.deepseek.com/v1",
      "api_key": "sk-...",
      "temperature": 0.7,
      "max_length": 4096,
      // ...
    },
    // ... other models
  ]
}
```

## Troubleshooting

### Authentication Failed Error

If you see `Authentication failed.`:

**Solution:** Use Docker Compose execution:
```bash
docker-compose exec backend python /app/scripts/configure_deepseek_glm.py
```

### Missing API Keys Error

If you see `Missing required API keys`:

**Solution:** Verify `.env` file contains:
```
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=...
```

### Connection Timeout Error

If you see connection timeout:

**Solution:** Verify services are running:
```bash
docker-compose ps
```

## Model API Endpoints

| Model | Provider | Base URL (resolved from SSOT) |
|-------|----------|----------|
| deepseek-chat | deepseek | https://api.deepseek.com/v1 |
| deepseek-reasoner | deepseek | https://api.deepseek.com/v1 |
| deepseek-v3.2 | deepseek | https://api.deepseek.com/v1 |
| glm-4.7 | zai | https://api.z.ai/api/paas/v4 |
| glm-4-plus | zai | https://api.z.ai/api/paas/v4 |
| glm-4-flash | zai | https://api.z.ai/api/paas/v4 |

## Post-Configuration Testing

Test the configured models via API:

```bash
# Test DeepSeek Chat
curl -X POST http://localhost:8090/api/v1/chat/conversations \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test",
    "message": "Hello, test DeepSeek chat!",
    "model_id": "thesis_deepseek-chat"
  }'

# Test GLM-4.7 (default)
curl -X POST http://localhost:8090/api/v1/chat/conversations \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test",
    "message": "Hello, test GLM-4.7!",
    "model_id": "thesis_glm-4.7"
  }'
```

## Safety Features

- **No hardcoded credentials** - All from environment
- **Idempotent operations** - Safe to run multiple times
- **Comprehensive logging** - Full audit trail
- **Error handling** - Graceful failure with detailed messages
- **API key validation** - Verifies keys before configuration

## Notes

- Script creates `model_id` as `{username}_{model_key}` format
- Default model set to `glm-4.7` for all users
- Existing model configurations are updated, not replaced
- Script logs all operations with timestamps
- Requires `motor` and `python-dotenv` packages

## References

- DeepSeek API: https://api.deepseek.com/docs
- Z.ai API: https://z.ai

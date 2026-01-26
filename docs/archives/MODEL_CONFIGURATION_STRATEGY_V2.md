# LAYRA v2.0.0 Model Configuration Strategy

## Executive Summary

This document provides a comprehensive model configuration strategy for LAYRA v2.0.0 using direct provider API integration (no LiteLLM proxy).

## Phase 1: API Keys to Import from ~/.007

### Recommended API Keys (Priority Order)

1. **OpenAI** (Currently imported) - Essential for premium models
   - Key already in .env: `OPENAI_API_KEY`

2. **DeepSeek** (Currently imported) - Reasoning models
   - Key already in .env: `DEEPSEEK_API_KEY`

3. **ZhipuAI (GLM)** - High performance Chinese models, competitive pricing
   - Source: `ZHIPUAI_API_KEY` from ~/.007
   - Add to .env: `ZHIPUAI_API_KEY=7c9a64caea6848d9b2a78cb452b8c564.eTEJlpK6BaCbFCfa`

4. **Moonshot (Kimi)** - Long context model (128k)
   - Source: `MOONSHOT_API_KEY` (or `KIMI_API_KEY`) from ~/.007
   - Add to .env: `MOONSHOT_API_KEY=sk-kimi-JJ5U2tXQ8Butav4NSUiCiOpzCf1ppJsOWFZ71VXKHbgbJ8FppwdHOFgiSmNNSluL`

5. **MiniMax** - Chinese conversational AI
   - Source: `MINIMAX_API_KEY` from ~/.007
   - Add to .env: `MINIMAX_API_KEY=<long_jwt_token>`

6. **Cohere** - RAG-optimized models
   - Source: `COHERE_API_KEY` from ~/.007
   - Add to .env: `COHERE_API_KEY=LgZ07DYc8xno8QxwAIGqlD4kJr9bOY9Vll93xEGH`

7. **Ollama Cloud** - Local model support (optional)
   - Source: `OLLAMA_CLOUD_API_KEY` from ~/.007
   - Add to .env: `OLLAMA_API_KEY=c8844b200c9f4f8099ca481fd2519e0a.NzluaD_ft_OvfI30zSSwQpXr`

### NOT Recommended to Import

- **Anthropic** - Key not available in ~/.007
- **Gemini** - Uses OAuth (not API key), not found in ~/.007

---

## Phase 2: Model Configuration Strategy

### Primary Model (General Chat)

**Selected:** `gpt-4o-mini` (OpenAI)
- **Rationale:** Fast, cost-effective, multilingual support, vision capabilities
- **Fallback:** `moonshot-v1-32k` (Moonshot/Kimi)

**Environment Variables:**
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini
```

### Backup Model (Failover)

**Selected:** `moonshot-v1-32k` (Moonshot/Kimi)
- **Rationale:** Long context (32k), competitive pricing, supports Chinese
- **Fallback:** `glm-4-air` (Zhipu)

**Environment Variables:**
```bash
BACKUP_LLM_PROVIDER=moonshot
BACKUP_LLM_MODEL=moonshot-v1-32k
```

### Specialized Models

#### 1. Reasoning/Complex Tasks
**Selected:** `deepseek-reasoner` (DeepSeek)
- **Use case:** Complex logical reasoning, step-by-step analysis
- **Note:** Does not support vision (images are stripped)
- **Fallback:** `command-r-plus` (Cohere)

**Environment Variables:**
```bash
REASONING_LLM_PROVIDER=deepseek
REASONING_LLM_MODEL=deepseek-reasoner
```

#### 2. Coding Tasks
**Selected:** `glm-4-plus` (Zhipu)
- **Use case:** Code generation, debugging, technical documentation
- **Rationale:** Strong coding performance, Chinese language support
- **Fallback:** `abab6.5g-chat` (MiniMax)

**Environment Variables:**
```bash
CODING_LLM_PROVIDER=zhipu
CODING_LLM_MODEL=glm-4-plus
```

#### 3. Chinese Language Processing
**Selected:** `glm-4-0520` (Zhipu)
- **Use case:** Chinese chat, translation, content generation
- **Fallback:** `moonshot-v1-128k` (Moonshot/Kimi)

**Environment Variables:**
```bash
CHINESE_LLM_PROVIDER=zhipu
CHINESE_LLM_MODEL=glm-4-0520
```

#### 4. Cost-Optimized (High Volume)
**Selected:** `glm-4-flash` (Zhipu)
- **Use case:** Background processing, high-volume tasks
- **Fallback:** `abab6.5s-chat` (MiniMax)

**Environment Variables:**
```bash
ECONOMY_LLM_PROVIDER=zhipu
ECONOMY_LLM_MODEL=glm-4-flash
```

---

## Phase 3: Provider Client Updates

### Completed Changes to `backend/app/rag/provider_client.py`

#### 1. Added New Providers to PROVIDERS Dictionary

```python
PROVIDERS = {
    # ... existing providers ...
    "moonshot": {
        "base_url": "https://api.moonshot.ai/v1",
        "env_key": "MOONSHOT_API_KEY",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
    },
    "kimi": {
        "base_url": "https://api.moonshot.ai/v1",
        "env_key": "KIMI_API_KEY",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "env_key": "ZHIPUAI_API_KEY",
        "models": ["glm-4-plus", "glm-4-air", "glm-4-flash", "glm-4-0520"]
    },
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "env_key": "MINIMAX_API_KEY",
        "models": ["abab6.5s-chat", "abab6.5g-chat", "abab6.5t-chat"]
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/v1",
        "env_key": "COHERE_API_KEY",
        "models": ["command-r-plus", "command-r", "command"]
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "env_key": "OLLAMA_API_KEY",
        "models": ["llama3", "llama3:70b", "mistral", "mixtral"]
    },
}
```

#### 2. Updated `get_provider_for_model` Method

Enhanced fallback detection for new providers:
- Moonshot/Kimi recognition
- GLM/Zhipu recognition  
- MiniMax recognition
- Cohere recognition
- Ollama recognition

---

## Phase 4: Default Configuration for New Users

### Recommended .env Template

```bash
# ============================================================================
# LLM PROVIDER CONFIGURATION
# ============================================================================
# API keys sourced from ~/.007

# Primary Provider (OpenAI)
OPENAI_API_KEY=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

# Backup Providers
DEEPSEEK_API_KEY=sk-29537d2ba74445f0894e53e48ca1d9ef
ZHIPUAI_API_KEY=7c9a64caea6848d9b2a78cb452b8c564.eTEJlpK6BaCbFCfa
MOONSHOT_API_KEY=sk-kimi-JJ5U2tXQ8Butav4NSUiCiOpzCf1ppJsOWFZ71VXKHbgbJ8FppwdHOFgiSmNNSluL
MINIMAX_API_KEY=<long_jwt_token>
COHERE_API_KEY=LgZ07DYc8xno8QxwAIGqlD4kJr9bOY9Vll93xEGH

# ============================================================================
# MODEL SELECTION
# ============================================================================

# Default Model (General Chat)
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini

# Backup Model (Failover)
BACKUP_LLM_PROVIDER=moonshot
BACKUP_LLM_MODEL=moonshot-v1-32k

# Specialized Models
REASONING_LLM_PROVIDER=deepseek
REASONING_LLM_MODEL=deepseek-reasoner

CODING_LLM_PROVIDER=zhipu
CODING_LLM_MODEL=glm-4-plus

CHINESE_LLM_PROVIDER=zhipu
CHINESE_LLM_MODEL=glm-4-0520

ECONOMY_LLM_PROVIDER=zhipu
ECONOMY_LLM_MODEL=glm-4-flash
```

### Model Selection Matrix

| Use Case | Primary Model | Backup Model | Provider | Notes |
|----------|--------------|-------------|----------|-------|
| General RAG Chat | `gpt-4o-mini` | `moonshot-v1-32k` | OpenAI/Moonshot | Vision supported, fast |
| Complex Reasoning | `deepseek-reasoner` | `command-r-plus` | DeepSeek/Cohere | No vision support |
| Code Generation | `glm-4-plus` | `abab6.5g-chat` | Zhipu/MiniMax | Strong coding skills |
| Chinese Chat | `glm-4-0520` | `moonshot-v1-128k` | Zhipu/Moonshot | Native Chinese support |
| Cost-Optimized | `glm-4-flash` | `abab6.5s-chat` | Zhipu/MiniMax | For high-volume tasks |

---

## Phase 5: Migration Plan for Existing Users

### Migration Steps

#### Step 1: Export Existing Configurations (Migration Script)

```python
# backend/scripts/migrate_models.py
"""
Migrate existing LiteLLM-based configurations to direct provider API.
"""
import asyncio
from app.db.mongo import get_mongo
from app.rag.provider_client import get_provider_for_model

async def migrate_conversation_configs():
    db = await get_mongo()
    conversations = await db.db["conversations"].find({}).to_list(None)
    
    migrated = 0
    for conv in conversations:
        if "model_config" in conv:
            config = conv["model_config"]
            old_model = config.get("model_name", "gpt-4o-mini")
            
            # Detect provider for new architecture
            provider = get_provider_for_model(old_model)
            
            # Update configuration
            conv["model_config"]["provider"] = provider
            conv["model_config"]["base_used"] = conv.get("model_config", {}).get("base_used", [])
            
            # Save
            await db.db["conversations"].update_one(
                {"_id": conv["_id"]},
                {"$set": {"model_config": conv["model_config"]}}
            )
            migrated += 1
    
    print(f"Migrated {migrated} conversation configurations")

if __name__ == "__main__":
    asyncio.run(migrate_conversation_configs())
```

#### Step 2: Update .env File

```bash
# Add to existing .env
ZHIPUAI_API_KEY=7c9a64caea6848d9b2a78cb452b8c564.eTEJlpK6BaCbFCfa
MOONSHOT_API_KEY=sk-kimi-JJ5U2tXQ8Butav4NSUiCiOpzCf1ppJsOWFZ71VXKHbgbJ8FppwdHOFgiSmNNSluL
MINIMAX_API_KEY=<long_jwt_token>
COHERE_API_KEY=LgZ07DYc8xno8QxwAIGqlD4kJr9bOY9Vll93xEGH

# Default model configuration updated
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini
```

#### Step 3: Restart Services

```bash
docker-compose down
docker-compose up -d
```

#### Step 4: Verify Migration

```bash
# Check that provider client can initialize
python -c "from app.rag.provider_client import ProviderClient; print('Providers:', list(ProviderClient.PROVIDERS.keys()))"

# Test model detection
python -c "from app.rag.provider_client import ProviderClient; print('gpt-4o ->', ProviderClient.get_provider_for_model('gpt-4o')); print('moonshot-v1 ->', ProviderClient.get_provider_for_model('moonshot-v1-32k'))"
```

---

## Appendix A: API Key Import Script

Create `backend/scripts/import_api_keys.sh`:

```bash
#!/bin/bash
# Import API keys from ~/.007 to .env

SOURCE_FILE="$HOME/.007"
ENV_FILE="/LAB/@thesis/layra/.env"

# Keys to import
KEYS=(
    "ZHIPUAI_API_KEY"
    "MOONSHOT_API_KEY"
    "MINIMAX_API_KEY"
    "COHERE_API_KEY"
    "OLLAMA_API_KEY"
)

echo "Importing API keys from ~/.007 to $ENV_FILE..."

for key in "${KEYS[@]}"; do
    # Extract value from source file
    value=$(grep "export $key=" "$SOURCE_FILE" | sed "s/export $key=//;s/\"//g")
    
    if [ -n "$value" ]; then
        # Check if key already exists in .env
        if grep -q "^${key}=" "$ENV_FILE"; then
            # Update existing key
            sed -i "s/^${key}=.*/${key}=${value}/" "$ENV_FILE"
            echo "Updated: $key"
        else
            # Append new key
            echo "${key}=${value}" >> "$ENV_FILE"
            echo "Added: $key"
        fi
    else
        echo "Warning: $key not found in $SOURCE_FILE"
    fi
done

echo "Done!"
```

---

## Appendix B: Model Cost Analysis (Estimates)

| Model | Input Cost / 1M | Output Cost / 1M | Notes |
|-------|-----------------|------------------|-------|
| gpt-4o-mini | $0.15 | $0.60 | Fast, cost-effective |
| gpt-4o | $2.50 | $10.00 | Premium, vision |
| deepseek-chat | $0.14 | $0.28 | Very cheap |
| deepseek-reasoner | $0.14 | $0.28 | Reasoning |
| moonshot-v1-8k | $0.012 | $0.012 | Very cheap |
| moonshot-v1-32k | $0.012 | $0.012 | Long context |
| glm-4-plus | $0.12 | $0.12 | Coding |
| glm-4-air | $0.12 | $0.12 | Fast |
| glm-4-flash | $0.10 | $0.10 | Economy |
| abab6.5s-chat | $0.02 | $0.02 | MiniMax |
| command-r-plus | $3.00 | $15.00 | RAG optimized |
| command-r | $0.50 | $1.50 | RAG optimized |

---

## Appendix C: Configuration Schema

### Conversation Model Config Structure

```python
{
    "model_name": "gpt-4o-mini",
    "provider": "openai",           # New: provider name
    "model_url": null,              # Legacy: can be null for direct API
    "api_key": null,                # Legacy: reads from env
    "base_used": [],                # Knowledge bases to search
    "temperature": 0.7,
    "max_length": 4096,
    "top_P": 0.9,
    "top_K": 3,
    "score_threshold": 10,
    "system_prompt": "You are LAYRA..."
}
```

---

## Summary

1. **API Keys to Import:** 7 providers from ~/.007 (OpenAI, DeepSeek already imported)
2. **Model Configuration:** 5-tier strategy (Primary, Backup, Reasoning, Coding, Chinese, Economy)
3. **Code Changes:** Updated `provider_client.py` with 6 new providers
4. **Migration Plan:** Script-based migration for existing users

This configuration provides:
- **Redundancy:** Multiple fallback providers
- **Cost Optimization:** Cost-effective alternatives for different use cases
- **Performance:** Models optimized for specific tasks
- **Language Support:** Strong Chinese language capabilities

# LAYRA Remediation Session - 2026-01-29

## Overview

This session fixed critical issues preventing the LAYRA RAG chat from working:
1. MongoDB schema drift
2. SSE endpoint bug
3. ZhipuAI Coding Plan configuration

## Issues Fixed

### 1. MongoDB Schema Drift (CRITICAL)

**Problem:**
- Backend connects to `chat_mongodb` database
- Database had OLD schema format
- Code expected NEW schema format
- Result: Frontend showed no models in dropdown

**Old Schema:**
```javascript
{
  username: "miko",
  chat_model: "miko_glm47",
  model_name: "glm-4.7",
  llm_provider: "zhipu",
  embedding_model: "local_colqwen",
  is_selected: true
}
```

**New Schema (Required by Code):**
```javascript
{
  username: "miko",
  selected_model: "miko_glm47",
  models: [
    {
      model_id: "miko_glm47",
      model_name: "glm-4.7",
      model_url: "https://open.bigmodel.cn/api/coding/paas/v4",
      api_key: "id.secret",
      base_used: [],
      system_prompt: "...",
      temperature: 0.7,
      max_length: 8192,
      top_P: 0.9,
      top_K: 3,
      score_threshold: 10
    }
  ]
}
```

**Fix:**
```bash
# Migrate existing data to new schema
db.model_config.deleteMany({username: "miko"})
db.model_config.insertOne({
  username: "miko",
  selected_model: "miko_glm47",
  models: [...]
})
```

**File:** `backend/app/db/repositories/model_config.py`

---

### 2. SSE Endpoint Bug (CRITICAL)

**Problem:**
- `/api/v1/sse/chat` passed `message_id` as 2nd positional argument
- Function signature has `model_config` as 2nd parameter
- Result: `message_id` was treated as `model_config`, causing errors

**Error:**
```
ValueError: RAG mode requires message_id parameter
```

**Buggy Code:**
```python
# WRONG - message_id becomes model_config!
ChatService.create_chat_stream(user_message, message_id)
```

**Fixed Code:**
```python
# CORRECT - use keyword argument
ChatService.create_chat_stream(user_message, message_id=message_id)
```

**File:** `backend/app/api/endpoints/sse.py:36`

---

### 3. ZhipuAI Coding Plan Configuration

**Problem:**
- GLM-4.5, GLM-4.6, GLM-4.7 require special "coding plan" endpoint
- Regular endpoint returns "余额不足" (insufficient balance)

**Solution:**
- Added `zhipu-coding` provider for coding plan endpoint
- Regular API: `https://open.bigmodel.cn/api/paas/v4`
- Coding Plan API: `https://open.bigmodel.cn/api/coding/paas/v4`

**Models Available:**

| Provider | Models | Endpoint |
|----------|--------|----------|
| zhipu | glm-4, glm-4-flash, glm-4-plus, glm-4v, glm-4-alltools | `/api/paas/v4` |
| zhipu-coding | glm-4.5, glm-4.6, glm-4.7 | `/api/coding/paas/v4` |

**File:** `backend/app/rag/provider_client.py`

---

## Working Configuration

### DeepSeek (Working)
```javascript
{
  model_id: "miko_deepseek_chat",
  model_name: "deepseek-chat",
  model_url: "https://api.deepseek.com/v1",
  api_key: "sk-..."
}
```

### GLM-4.7 Coding Plan (Working)
```javascript
{
  model_id: "miko_glm47",
  model_name: "glm-4.7",
  model_url: "https://open.bigmodel.cn/api/coding/paas/v4",
  api_key: "id.secret"  // JWT format
}
```

---

## Database Connection Info

**Environment Variables:**
```bash
MONGODB_URL=mongodb:27017
MONGODB_DB=chat_mongodb  # NOT "layra"!
```

**Direct MongoDB Access:**
```bash
docker exec layra-mongodb mongosh \
  "mongodb://thesis:<mongodb_password>@localhost:27017/chat_mongodb?authSource=admin"
```

---

## References

- [ZhipuAI HTTP API Documentation](https://docs.bigmodel.cn/cn/guide/develop/http/introduction)
- [Mastra ZhipuAI Coding Plan](https://mastra.ai/models/providers/zhipuai-coding-plan)

---

## Files Modified

1. `backend/app/api/endpoints/sse.py` - Fixed SSE endpoint bug
2. `backend/app/rag/provider_client.py` - Added zhipu-coding provider
3. `backend/app/db/repositories/model_config.py` - Schema documented
4. `chat_mongodb.model_config` - Migrated to new schema

---

## Testing Checklist

- [x] DeepSeek chat works
- [x] GLM-4.7 (coding plan) works
- [x] Models appear in frontend dropdown
- [x] SSE streaming works
- [x] JWT authentication for ZhipuAI works

---

## Next Steps

1. Add database migration script for schema updates
2. Add health check for model configuration
3. Document coding plan subscription requirements
4. Add error handling for insufficient balance

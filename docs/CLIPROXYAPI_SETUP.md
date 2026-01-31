# CLIProxyAPI Integration Guide

This guide explains how to integrate Gemini CLI (and other AI CLIs) into Layra via CLIProxyAPI.

## What is CLIProxyAPI?

CLIProxyAPI is a Docker service that provides an OpenAI-compatible API endpoint for various AI CLIs including:
- **Gemini CLI** (Google's official CLI)
- **OpenAI Codex**
- **Claude Code**
- **Qwen Code**
- **Antigravity** (Meta's AI CLI)

Instead of managing API keys for each provider separately, CLIProxyAPI handles authentication via OAuth and exposes a unified OpenAI-compatible endpoint.

## Architecture

```
Layra Frontend → Layra Backend → CLIProxyAPI → Gemini CLI (via OAuth)
                    ↑                ↑
               MongoDB (store     Config.yaml
               model config)      (OAuth tokens)
```

## Setup Process

### 1. Environment Configuration

Add these to your `.env` file:

```bash
# CLIProxyAPI Configuration
CLIPROXYAPI_BASE_URL=http://cliproxyapi:8317/v1
CLIPROXYAPI_API_KEY=layra-cliproxyapi-key
```

The `API_KEY` is used for authentication between Layra backend and CLIProxyAPI service.

### 2. Docker Compose Service

The service is already defined in `docker-compose.yml`:

```yaml
cliproxyapi:
  container_name: layra-cliproxyapi
  image: eceasy/cli-proxy-api:latest
  ports:
    - "8085:8085"  # Web UI for OAuth
    - "8317:8317"  # API endpoint
  volumes:
    - ${HOME}/.cli-proxy-api/config.yaml:/CLIProxyAPI/config.yaml:ro
    - cliproxyapi_auth:/root/.cli-proxy-api
  networks:
    - layra-net
```

### 3. CLIProxyAPI Configuration

Create `~/.cli-proxy-api/config.yaml`:

```yaml
host: ""
port: 8317
auth-dir: "/root/.cli-proxy-api"
api-keys:
  - "layra-cliproxyapi-key"  # Must match CLIPROXYAPI_API_KEY
request-retry: 3
debug: false
```

### 4. OAuth Authentication

After starting the services, authenticate with Google:

```bash
docker exec -it layra-cliproxyapi ./CLIProxyAPI --login
```

This will output a URL. Open it in your browser and complete OAuth with your Google account.

**Verification:**

```bash
# Check available models
curl -s http://localhost:8317/v1/models \
  -H "Authorization: Bearer layra-cliproxyapi-key" | jq '.data[].id'
```

Expected output:
```
gemini-2.5-flash
gemini-2.5-flash-lite
gemini-2.5-pro
gemini-3-flash-preview
gemini-3-pro-preview
```

## How System Models Work

### Backend Implementation

When `CLIPROXYAPI_BASE_URL` is set, the backend automatically:

1. **Fetches model list** from `ProviderClient.PROVIDERS["cliproxyapi"]["models"]`
2. **Creates system models** with `system_` prefix (e.g., `system_gemini-2.5-pro`)
3. **Returns actual credentials** in API responses:
   ```json
   {
     "model_id": "system_gemini-2.5-pro",
     "model_name": "gemini-2.5-pro",
     "model_url": "http://cliproxyapi:8317/v1",
     "api_key": "layra-cliproxyapi-key"
   }
   ```

### Key Backend Files

- **`backend/app/db/repositories/model_config.py`**:
  - `get_all_models_config()`: Auto-appends system models when env is configured
  - `get_selected_model_config()`: Returns real URL/key for system models
  - `update_selected_model()`: Allows selecting system models (not in DB)

- **`backend/app/rag/provider_client.py`**:
  - `PROVIDERS["cliproxyapi"]` model list
  - `get_provider_for_model()`: Routes to `cliproxyapi` provider for system models
  - `create_client()`: Reads `CLIPROXYAPI_BASE_URL` from env when creating client

### Frontend Implementation

- **`frontend/src/lib/api/configApi.tsx`**: Added `selectModel()` API call
- **`frontend/src/components/AiChat/ChatBox.tsx`**: 
  - `handleSaveConfig()`: Calls `updateModelConfig()` THEN `selectModel()` for ALL models (unified flow)
  - Refreshes local state after selection to ensure persistence
- **`frontend/src/components/AiChat/components/LlmSettingsSection.tsx`**: 
  - Disables URL/API key inputs for system models (read-only)
  - Shows grayed-out styling
- **`frontend/src/components/AiChat/components/ModelSelector.tsx`**: 
  - Hides delete button for system models

### Backend Persistence (Upsert Pattern)

System models use a "virtual-to-persistent" upsert pattern in `backend/app/db/repositories/model_config.py` via `_upsert_system_model_config()`:

- **First Save**: If the system model doesn't exist in the user's `models` array, it is inserted (`$push`). This persists the "virtual" model for the first time.
- **Subsequent Saves**: If the model already exists, it is updated in place (`$set` with `array_filters`).
- **Defaults**: Automatically uses `CLIPROXYAPI_BASE_URL` and `CLIPROXYAPI_API_KEY` from environment variables if fields are not provided.

This ensures that system model settings (system prompt, temperature, etc.) persist across sessions. For more details, see the [CHANGE_LOG](../operations/CHANGE_LOG.md) entry for commit `0cd2479`.

## User Flow

1. **Open Config Modal** → System models appear in dropdown (e.g., `system_gemini-2.5-pro`)
2. **Select Model** → URL and API key fields show the actual values (read-only)
3. **Save** → Frontend calls `update-model-config` (persists settings) THEN `select-model` (activates model)
4. **Chat** → Messages route through CLIProxyAPI to Gemini CLI

## Troubleshooting

### "unknown provider for model gemini-X"

**Cause**: Model name in `PROVIDERS["cliproxyapi"]["models"]` doesn't match CLIProxyAPI's actual models.

**Fix**: Check CLIProxyAPI's model list and update `backend/app/rag/provider_client.py`:

```bash
curl -s http://localhost:8317/v1/models \
  -H "Authorization: Bearer layra-cliproxyapi-key" | jq '.data[].id'
```

### "API key not found"

**Cause**: `CLIPROXYAPI_API_KEY` not set or mismatch between `.env` and `config.yaml`.

**Fix**: Verify both files have the same key.

### Model appears in dropdown but fields are empty

**Cause**: Frontend state stale after selection.

**Fix**: Already fixed in `ChatBox.tsx` - `handleSaveConfig` now calls `fetchModelConfig()` after selection.

### OAuth fails

**Cause**: Port 8085 not accessible or config.yaml mounted incorrectly.

**Fix**: 
```bash
# Check port
docker ps | grep cliproxyapi

# Check config mounted
docker exec layra-cliproxyapi cat /CLIProxyAPI/config.yaml
```

## Provider Routing Priority

In `provider_client.py`, the detection order ensures CLIProxyAPI models take precedence:

```python
# 1. Check CLIProxyAPI models FIRST (when CLIPROXYAPI_BASE_URL is set)
if os.getenv("CLIPROXYAPI_BASE_URL"):
    if model_name in cliproxyapi_models:
        return "cliproxyapi"

# 2. Generic checks come AFTER
if "gemini" in model_lower:
    return "gemini"  # Native Google API (only if not CLIProxyAPI)
```

This ensures `gemini-2.5-pro` routes to CLIProxyAPI, not native Gemini API.

## Model Naming Convention

- **CLIProxyAPI models**: Use names from `curl /v1/models` (e.g., `gemini-3-pro-preview`)
- **System model IDs**: Prefixed with `system_` (e.g., `system_gemini-3-pro-preview`)
- **UI Display**: Shows `model_name` (without `system_` prefix)

## Security Notes

- API keys are returned to frontend but marked as read-only
- System models cannot be deleted or modified (immutable)
- OAuth tokens stored in Docker volume `cliproxyapi_auth`
- Each user shares the same CLIProxyAPI instance (OAuth is per-deployment, not per-user)

## Related Files

| File | Purpose |
|------|---------|
| `backend/app/db/repositories/model_config.py` | System model creation and selection |
| `backend/app/rag/provider_client.py` | Provider routing and CLIProxyAPI config |
| `frontend/src/lib/api/configApi.tsx` | `selectModel()` API |
| `frontend/src/components/AiChat/ChatBox.tsx` | Save config logic |
| `frontend/src/components/AiChat/components/LlmSettingsSection.tsx` | Read-only UI for system models |
| `frontend/src/components/AiChat/components/ModelSelector.tsx` | Hide delete for system models |

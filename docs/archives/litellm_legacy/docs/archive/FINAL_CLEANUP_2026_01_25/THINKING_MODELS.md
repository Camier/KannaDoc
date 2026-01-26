# Ollama Thinking Models - Configuration Guide

## Supported Models with Thinking Capability

Based on [Ollama's official documentation](https://docs.ollama.com/capabilities/thinking):

| Model | Think Parameter | Notes |
|-------|-----------------|-------|
| **Qwen 3** (`qwen3`) | `true`/`false` | Default thinking enabled |
| **GPT-OSS** (`gpt-oss`) | `"low"`, `"medium"`, `"high"` | Cannot be fully disabled, only levels |
| **DeepSeek-v3.1** (`deepseek-v3.1`) | `true`/`false` | Hybrid mode (thinking + non-thinking) |
| **DeepSeek R1** (`deepseek-r1`) | `true`/`false` | Reasoning-focused model |
| **GLM-4.6** (`glm-4.6`) | `true`/`false` | Advanced reasoning |
| **Magistral** (`magistral`) | `true`/`false` | 24B reasoning model |

Browse all thinking models: https://ollama.com/search?c=thinking

## How Thinking Works

When thinking is enabled:
- **Ollama returns**: `message.thinking` (reasoning trace) + `message.content` (final answer)
- **LiteLLM transforms to**: `delta.reasoning_content` + `delta.content` (OpenAI-compatible format)

### Response Format Comparison

**Native Ollama format:**
```json
{
  "message": {
    "role": "assistant",
    "thinking": "Let me analyze this step by step...",
    "content": "The answer is 42."
  },
  "done": true,
  "done_reason": "stop"
}
```

**LiteLLM OpenAI-compatible format:**
```json
{
  "choices": [{
    "delta": {
      "role": "assistant",
      "reasoning_content": "Let me analyze this step by step...",
      "content": "The answer is 42."
    },
    "finish_reason": "stop"
  }]
}
```

## Configuration in config.yaml

### Models That Should Have Thinking DISABLED

If you want standard `content` responses (no reasoning trace), disable thinking:

```yaml
model_list:
  - model_name: qwen3-coder-480b-cloud
    litellm_params:
      model: openai/qwen3-coder:480b
      api_base: os.environ/OLLAMA_CLOUD_OPENAI_BASE
      api_key: os.environ/OLLAMA_CLOUD_API_KEY
      think: false  # Disable thinking (for models that support boolean think)
      keep_alive: -1
      timeout: 180
```

### Models That CANNOT Disable Thinking

**GPT-OSS** only accepts levels (`low`, `medium`, `high`). You cannot fully disable thinking:

```yaml
model_list:
  - model_name: gpt-oss-120b-cloud
    litellm_params:
      model: openai/gpt-oss:120b
      api_base: os.environ/OLLAMA_CLOUD_OPENAI_BASE
      api_key: os.environ/OLLAMA_CLOUD_API_KEY
      think: low  # Minimize but cannot fully disable (provider-specific)
      keep_alive: -1
      timeout: 180
```

### Configuration: merge_reasoning_content_in_choices

LiteLLM has a setting to merge `reasoning_content` into `content` with `<think>` tags:

```yaml
litellm_settings:
  merge_reasoning_content_in_choices: true  # Merge reasoning into content with <think> tags
```

**IMPORTANT:** We disabled this globally because:
1. **Streaming**: When enabled, thinking content appears as `<think>...</think>` tags in the `content` field
2. **OpenCode**: Doesn't strip `<think>` tags, so they appear in the output
3. **Better approach**: Let `reasoning_content` be a separate field; clients that support it can display/hide it appropriately

**Current configuration (recommended):**
- Global: `merge_reasoning_content_in_choices` is **disabled** (commented out)
- Per-model: No `merge_reasoning_content_in_choices` overrides
- Result: `reasoning_content` returned as a separate field in the API response

## Models in Current config.yaml That Support Thinking

Based on the models in your `config.yaml`:

| Model Name | Base Model | Thinking Support |
|------------|------------|------------------|
| `gpt-oss-120b-cloud` | `openai/gpt-oss:120b` | **Yes** (levels only) |
| `gpt-oss-20b-cloud` | `openai/gpt-oss:20b` | **Yes** (levels only) |
| `deepseek-v3-1-671b-cloud` | `openai/deepseek-v3.1:671b` | **Yes** |
| `kimi-k2-thinking-cloud` | `openai/kimi-k2-thinking:cloud` | **Yes** |
| `cogito` | `openai/cogito-2.1:671b` | Unknown |
| `qwen3-coder-480b-cloud` | `openai/qwen3-coder:480b` | **Yes** (qwen3 family) |

Tip: the authoritative source is `config.yaml` — search for `think:` to see which models have explicit thinking configured.

## Client Compatibility Issues

### OpenCode / AI SDK

OpenCode uses `@ai-sdk/openai-compatible` which expects `delta.content`. When models return `delta.reasoning_content`, OpenCode handles it properly IF:

1. **Model config has `reasoning: true`** in OpenCode's `opencode.json`
2. **LiteLLM returns `reasoning_content` as a separate field** (not merged with `<think>` tags)

If you’re using OpenCode: set `reasoning: true` for “thinking” models so `reasoning_content` is displayed/handled correctly.

**Do NOT use `merge_reasoning_content_in_choices: true`** - this causes `<think>` tags to appear in the output.

### Streaming vs Non-Streaming

Both work correctly when:
- `merge_reasoning_content_in_choices` is **disabled** (default)
- LiteLLM returns `reasoning_content` as a separate field
- OpenCode model config has `reasoning: true`

**Result:**
- Streaming: `delta.reasoning_content` contains thinking, `delta.content` contains the response
- Non-streaming: `message.reasoning_content` contains thinking, `message.content` contains the response

## Testing Commands

```bash
# Test with thinking enabled (default)
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-oss-20b-cloud", "messages": [{"role": "user", "content": "Say hi"}], "stream": true}'

# Test with thinking disabled (for supported models)
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-coder-480b-cloud", "messages": [{"role": "user", "content": "Say hi"}], "stream": true, "extra_body": {"think": false}}'
```

## Diagnostic Script

Run the diagnostic test:
```bash
cd /LAB/@litellm
source ~/.venvs/litellm/bin/activate
source ~/.007
python tests/test_ollama_stream.py gpt-oss-20b-cloud --raw
```

This shows raw SSE output to verify `reasoning_content` vs `content` fields.

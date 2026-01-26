# Provider Tuning Guide

This document aggregates precise tuning recommendations and parameter mappings for the specific providers used in this LiteLLM deployment.

## 1. DeepSeek
**Source:** `docs/providers/deepseek`

### Reasoning Models (`deepseek-reasoner`, `R1`)
*   **Parameter:** `reasoning_effort` or `thinking`
*   **Values:** `low`, `medium`, `high` (all map to `thinking: { "type": "enabled" }`)
*   **Behavior:** DeepSeek does not support "budget tokens" like Anthropic. It's a binary toggle.
*   **Precise Config:**
    ```yaml
    litellm_params:
      model: deepseek/deepseek-reasoner
      reasoning_effort: "medium" # Enables thinking mode
    ```

## 2. Mistral
**Source:** `docs/providers/mistral`

### Reasoning Support
*   **Supported Models:** Only **Magistral** series (e.g., `magistral-small-2506`, `magistral-medium-2506`).
*   **Unsupported:** `mistral-large`, `mistral-small`, `mixtral`.
*   **Mechanism:** LiteLLM injects a specialized system prompt when `reasoning_effort` is set.
*   **Precise Config:**
    ```yaml
    litellm_params:
      model: mistral/magistral-medium-2506
      reasoning_effort: "medium" # Injects chain-of-thought system prompt
    ```

## 3. Moonshot AI (Kimi)
**Source:** `docs/providers/moonshot`

### Critical Limitations
1.  **Temperature Range:** Strictly `[0, 1]`. LiteLLM automatically clamps values > 1.
    *   *Recommendation:* Use `temperature: 0.6` for creative tasks, `0.1` for precise tasks.
2.  **Temperature + N:** If `temperature < 0.3` AND `n > 1`, request fails.
    *   *LiteLLM Fix:* Automatically resets temperature to `0.3` if this combination is detected.
3.  **Tool Choice:** `tool_choice="required"` is **not supported**.
    *   *LiteLLM Fix:* Converts to a user message "Please select a tool...".

### Regional Endpoints
*   Global: `https://api.moonshot.ai/v1`
*   China: `https://api.moonshot.cn/v1` (Set `MOONSHOT_API_BASE` if needed).

## 4. Ollama (Local)
**Source:** `docs/providers/ollama`

### Advanced Parameters
Use `extra_body.options` to pass native Ollama parameters that aren't mapped to OpenAI standard fields.

| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| `num_ctx` | `8192` | Context window size (default 2048). |
| `keep_alive` | `-1` | Keep model in RAM indefinitely (prevents reloading lag). |
| `num_predict` | `4096` | Max tokens to generate (maps to `max_tokens`). |
| `mirostat` | `0` or `2` | Advanced sampling (0=disabled, 2=learning). |

### Precise Config Example
```yaml
litellm_params:
  model: ollama_chat/llama3.1
  extra_body:
    options:
      num_ctx: 8192
      keep_alive: -1
      num_predict: 4096
```

## 5. Anthropic (Claude)
**Source:** `docs/providers/anthropic`

### Reasoning (Thinking)
*   **Parameter:** `reasoning_effort`
*   **Values:** `low` (1k tokens), `medium` (2k), `high` (4k+).
*   **Behavior:** Maps to `budget_tokens`.
*   **Precise Config:**
    ```yaml
    litellm_params:
      model: anthropic/claude-3-7-sonnet-20250219
      reasoning_effort: "medium"
    ```

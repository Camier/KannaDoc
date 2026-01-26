# Ollama tool-calling notes (official doc)

- Source: https://docs.ollama.com/api (also mirrored at https://raw.githubusercontent.com/ollama/ollama/main/docs/api.md).
- Tool calling: pass a `tools` array on `POST /api/chat`; the model returns `tool_calls` and you can send tool results back with `tool_calls` / `tool_name` in messages.
- Parameters: `model`, `messages`, optional `tools`, `think` (for thinking models), `stream` (default true), `format` (json/JSON schema), `options` (model params like `temperature`), `keep_alive` to keep/unload models.
- Advanced: set `stream=false` for single response; `keep_alive: 0` unloads the model.

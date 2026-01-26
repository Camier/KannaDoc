# OpenCode Setup & Integration

This document details the installation, configuration, and integration of the `oh-my-opencode` CLI with the LiteLLM Proxy.

## 🚀 Installation

The OpenCode CLI was installed system-wide using npm:

```bash
npm install -g oh-my-opencode
```

## 🛠️ Configuration

A robust configuration has been created at `~/.opencode/opencode.jsonc`.

### Agents

The following specialized agents have been configured to use LiteLLM models via the Master Key:

| Agent | Role | Model (LiteLLM Mapped) | Provider |
| :--- | :--- | :--- | :--- |
| **architect** | System Design & Scalability | `deepseek-v3-1-671b-cloud` | OpenAI (Generic) |
| **debugger** | Log Analysis & Bug Fixing | `gpt-oss-120b-cloud` | OpenAI (Generic) |
| **reviewer** | Security & Code Quality | `mistral-large-3-675b-cloud` | OpenAI (Generic) |

### MCP Servers

The following Model Context Protocol (MCP) servers are enabled:

*   **Filesystem**: Access to `/LAB` and `/home/miko`.
*   **Memory**: Persistent memory context.
*   **Web Search**: Brave Search (requires `BRAVE_API_KEY`).
*   **GitHub**: Repository management (requires `GITHUB_TOKEN`).

### Skills

Standard skills have been installed in `~/.opencode/skills`:
*   `react-best-practices`
*   `web-design-guidelines`
*   `vercel-deploy-claimable`
*   Global skills: `git-workflow`, `docker-management`, `test-runner`

## 🔑 Authentication

The integration uses the **LiteLLM Master Key** for reliable, unlimited access to all models.

*   **API Key**: `sk-safKz-RaebX20rwBBgPuIa7Xln2BTRm-FmMP5jtggAo`
*   **Base URL**: `http://127.0.0.1:4000/v1`

## ⚠️ Known Issues & Notes

*   **Key Persistence**: Generated virtual keys were not persisting correctly across LiteLLM container restarts due to database configuration nuances (`store_model_in_db: false`). The Master Key was used as a reliable fallback.
*   **Environment Variables**: Ensure `BRAVE_API_KEY` and `GITHUB_TOKEN` are set in your shell or `opencode.jsonc` env sections for full MCP functionality.

## ✅ Verification

You can test the setup by running:

```bash
oh-my-opencode run "Analyze the project structure and suggest improvements"
```

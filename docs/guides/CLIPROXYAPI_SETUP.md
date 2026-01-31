# CLIProxyAPI Setup & Integration Guide

**Status**: ✅ Production Ready  
**Last Updated**: 2026-01-31  
**Integration**: OpenAI/Gemini/Claude Compatible API  

---

## 📋 Overview

[CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) is a powerful proxy server that wraps various CLI-based AI tools as standard API endpoints. It allows Layra to access premium models through OAuth subscriptions without direct API costs for each provider.

By integrating CLIProxyAPI, Layra gains access to high-performance models including Antigravity, Gemini CLI, Claude Code, and more, all through a unified OpenAI-compatible interface.

---

## 🚀 Prerequisites

Before integrating with Layra, ensure you have:

1. **CLIProxyAPI Installed**: Follow the [official installation guide](https://github.com/router-for-me/CLIProxyAPI).
2. **Active Subscription**: Ensure you have configured the necessary CLI tools and OAuth sessions in CLIProxyAPI.
3. **API Key**: Obtain your API key from the CLIProxyAPI configuration.
4. **Network Access**: Ensure Layra can reach the CLIProxyAPI server (default port `8317`).

For detailed CLIProxyAPI setup, refer to the [Official Help Center](https://help.router-for.me/).

---

## 🔧 Configuration

### Environment Variables

To enable CLIProxyAPI in Layra, add the following variables to your `.env` file:

```bash
# CLIProxyAPI Connection
CLIPROXYAPI_BASE_URL=http://host.docker.internal:8317/v1
CLIPROXYAPI_API_KEY=your_cliproxyapi_api_key_here
```

> **Note**: If running Layra in Docker on Linux, use your host's IP address or `host.docker.internal` (if configured) to reach CLIProxyAPI running on the host.

### Service Integration

Once configured, CLIProxyAPI models will appear as available providers in the Layra Model Management interface.

---

## 🤖 Supported Models

CLIProxyAPI provides access to the following premium models:

| Provider | Model Name | Description |
|----------|------------|-------------|
| **Antigravity** | `claude-opus-4-5-thinking` | Claude Opus 4.5 with extended thinking |
| **Antigravity** | `claude-sonnet-4-5-thinking` | Claude Sonnet 4.5 with extended thinking |
| **Antigravity** | `claude-sonnet-4-5` | Claude Sonnet 4.5 standard |
| **Gemini CLI** | `gemini-3-flash` | Latest Gemini 3 Flash model |
| **Gemini CLI** | `gemini-3-pro-preview` | Gemini 3 Pro preview |
| **Gemini CLI** | `gemini-2.5-pro` | Gemini 2.5 Pro (production) |
| **Gemini CLI** | `gemini-2.5-flash` | Gemini 2.5 Flash (fast) |

---

## 🛠️ Troubleshooting

### Connection Errors
**Issue**: `Connection refused` or `Max retries exceeded`.
- **Fix**: Verify CLIProxyAPI is running (`ps aux | grep cliproxy`).
- **Fix**: Check if the `CLIPROXYAPI_BASE_URL` is accessible from the Layra container (use `curl` inside the container).
- **Fix**: Ensure the port `8317` is not blocked by a firewall.

### Authentication Failures
**Issue**: `401 Unauthorized`.
- **Fix**: Double-check `CLIPROXYAPI_API_KEY` in your `.env` file.
- **Fix**: Verify the key is active in CLIProxyAPI settings.

### Model Not Found
**Issue**: `404 Model Not Found`.
- **Fix**: Ensure the specific CLI tool (e.g., `antigravity`) is correctly logged in and configured within CLIProxyAPI.
- **Fix**: Restart CLIProxyAPI to refresh the model list.

### Slow Response Times
- **Fix**: Check the latency of the underlying CLI tool.
- **Fix**: Ensure your internet connection is stable, as these tools rely on cloud-based OAuth sessions.

---

## 📚 References

- [CLIProxyAPI GitHub Repository](https://github.com/router-for-me/CLIProxyAPI)
- [CLIProxyAPI Help Documentation](https://help.router-for.me/)
- [Layra Configuration Guide](../core/CONFIGURATION.md)

---

Ultraworked with [Sisyphus](https://github.com/code-yeongyu/oh-my-opencode)
Co-authored-by: Sisyphus <clio-agent@sisyphuslabs.ai>

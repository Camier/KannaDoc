# LiteLLM Official CLI Guide

This guide mirrors **official LiteLLM CLI documentation**. For full coverage, see:
https://docs.litellm.ai/docs/proxy/management_cli

## Prerequisites
The CLI requires the proxy to be reachable and the proxy URL/API key set:

```bash
export LITELLM_PROXY_URL="http://127.0.0.1:4000"
export LITELLM_PROXY_API_KEY="sk-..."  # Master key
```

## Login
```bash
litellm-proxy login
```

## Models
```bash
litellm-proxy models list
litellm-proxy models info --model-id <model-id>
```

## Credentials
```bash
litellm-proxy credentials list
litellm-proxy credentials delete --credential-name <name>
```

## Keys
```bash
litellm-proxy keys list
litellm-proxy keys generate --duration 1hr --models all-team-models
litellm-proxy keys delete --key-aliases "<key-alias>"
```

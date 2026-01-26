# LiteLLM Proxy Composition Report

This document summarizes repo composition and limits LiteLLM behavior statements to **official documentation**. Local deployment details are defined in repo files.

## Official References
- Proxy config file (`config.yaml`): https://docs.litellm.ai/docs/proxy/configs
- OpenAI-compatible endpoints: https://docs.litellm.ai/docs/proxy/user_keys
- Health endpoints: https://docs.litellm.ai/docs/proxy/health
- Admin UI: https://docs.litellm.ai/docs/proxy/ui
- Virtual keys: https://docs.litellm.ai/docs/proxy/virtual_keys

## Local Composition (Repo Files)
These files define the local deployment and configuration:
- `config.yaml` (LiteLLM proxy configuration)
- `.env` and `.env.docker.example` (environment variables)
- `docker-compose.yml` (services and port mappings)
- `schema.prisma` (database schema used by LiteLLM proxy features in this repo)
- `bin/` (local helper scripts)
- `docs/` (runbooks and notes)

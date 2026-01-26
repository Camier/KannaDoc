# Known Issues & Resolutions (Jan 2026)

## Database & Schema (Resolved)
- **Missing Skills Table**: Resolved by manually creating `LiteLLM_SkillsTable` and regenerating the Prisma client. Dynamic skills injection is now operational.
- **Double Encryption**: Resolved. A previous re-seeding had nested encryption layers. The DB was wiped, and models were re-seeded with a single, healthy layer of encryption.
- **Model Duplicates**: Resolved. Redundant entries for `local-embeddings` and `arctic-embed` were removed from `LiteLLM_ProxyModelTable`.

## Environment & Runtime (Resolved)
- **Venv/Conda Mismatch**: All background services (Health, Rerank) were aligned to the primary `/home/miko/.conda/envs/litellm` environment.
- **Audit Compliance**: `bin/audit_consistency.py` was updated to support Mamba environments and dynamic systemd unit discovery.
- **Log Permissions**: Log file ownership was corrected to allow services to write to `logs/`.

## External Providers (Current Limits)
- **Gemini 3 Pro Preview**: Returning `429` due to reaching premium model request limits on the provider side.
- **GLM-4.7 Cloud**: Experiencing frequent timeouts (120s+). Using `glm-4.6-cloud` is recommended for stability.
- **Ollama RAM Constraints**: `ollama-qwen3-coder-30b` cannot run locally as it requires ~17.3GB RAM (Host has 16GB). Use cloud variants instead.

## Integration Status
- **TGI Integration**: Disabled (`ENABLE_TGI=0`) as no local TGI server is currently active.
- **Metrics Exporter**: Operational on port 9090.
- **Ollama Auto-Discovery**: Functional and providing local model access.
- **Rogue Processes**: Standardized on port 8079 for Rerank and 11436 for vLLM; old rogue listeners were purged.

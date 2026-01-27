# Archived Docker Compose Configurations

This directory contains historical docker-compose files that have been deprecated or replaced. They are kept here for reference purposes but should not be used for active deployments.

## Archived Files

### docker-compose.backup.yml
- **Date Archived:** 2026-01-27
- **Original Location:** `/docker-compose.backup.yml` (project root)
- **Purpose:** Backup snapshot of the main docker-compose.yml configuration
- **Why Archived:** Created as a safety backup during configuration changes. The active configuration is maintained in `/docker-compose.yml`
- **Key Differences:** Uses Apache Kafka image (identical to current main config)
- **Note:** This file should be deleted once the current configuration is confirmed stable

### docker-compose-no-local-embedding.yml
- **Date Archived:** 2026-01-27
- **Original Location:** `/deploy/docker-compose-no-local-embedding.yml`
- **Purpose:** Deployment variant without local embedding model support
- **Why Archived:** Replaced by environment variable configuration. The same functionality is now achieved by setting `EMBEDDING_MODEL=jina_embeddings_v4` in the standard docker-compose.yml
- **Key Differences:**
  - Uses Bitnami Kafka image instead of Apache Kafka
  - Does not include model-server service
  - Designed for deployments without GPU access
- **Migration Path:** Use `docker-compose.yml` with `EMBEDDING_MODEL=jina_embeddings_v4` environment variable

## Historical Context

During the project's evolution, multiple deployment variants were created to support different use cases:

1. **GPU Deployment** - Full local embeddings using ColQwen2.5
2. **No-GPU Deployment** - Cloud embeddings via Jina API
3. **Thesis Deployment** - Simplified single-user setup with Neo4j

The "No-GPU" variant was implemented as a separate compose file. This approach was deprecated in favor of:
- **Single compose file** (`docker-compose.yml`) with **environment-driven configuration**
- **Override files** for specific scenarios (GPU, development, thesis)
- **Reduced maintenance burden** - only one main file to update

## Active Deployment Files

For current deployments, use these files instead:

| File | Purpose | Usage |
|------|---------|-------|
| `/docker-compose.yml` | Main configuration | `docker compose up -d` |
| `/docker-compose.override.yml` | Development overrides | Auto-applied in dev |
| `/deploy/docker-compose.thesis.yml` | Thesis/solo deployment | `docker compose -f deploy/docker-compose.thesis.yml up -d` |
| `/deploy/docker-compose.gpu.yml` | GPU enablement | `docker compose -f docker-compose.yml -f deploy/docker-compose.gpu.yml up -d` |

See `/deploy/README.md` for detailed usage instructions.

# Orphan Docker Volumes

**Generated**: 2026-02-01  
**Status**: Informational

This document lists Docker volumes that exist but are NOT referenced in the current `docker-compose.yml`.

## Active Volumes (In Use)

These volumes are defined in `docker-compose.yml` and actively used:

| Volume | Purpose |
|--------|---------|
| `layra_kafka_data` | Kafka event logs |
| `layra_minio_data` | Object storage (files, documents) |
| `layra_redis_data` | Cache data |
| `layra_mysql_data` | MySQL relational data |
| `layra_mongo_data` | MongoDB application data |
| `layra_milvus_etcd` | Milvus metadata |
| `layra_milvus_minio` | Milvus internal storage |
| `layra_milvus_data` | Vector embeddings |
| `layra_model_weights` | ML model files (~5-10GB) |
| `layra_layra_sandbox_volume` | Python sandbox shared volume |
| `layra_mysql_migrations` | MySQL migration history |
| `layra_prometheus_data` | Prometheus metrics |
| `layra_grafana_data` | Grafana dashboards |
| `layra_cliproxyapi_auth` | CLI Proxy API auth tokens |

## Orphan Volumes (Safe to Remove)

These volumes are NOT in the current compose file and can be safely removed:

### From Old `deploy/` Setup

```bash
# These were created by old deploy/ compose files
docker volume rm deploy_cuda_cache
docker volume rm deploy_kafka_data
docker volume rm deploy_layra_sandbox_volume
docker volume rm deploy_milvus_data
docker volume rm deploy_milvus_etcd
docker volume rm deploy_milvus_minio
docker volume rm deploy_minio_data
docker volume rm deploy_model_weights
docker volume rm deploy_mongo_data
docker volume rm deploy_mysql_data
docker volume rm deploy_neo4j_data
docker volume rm deploy_neo4j_logs
docker volume rm deploy_redis_data
```

### Deprecated Services

```bash
# Neo4j was removed from stack
docker volume rm layra_neo4j_data
docker volume rm layra_neo4j_logs

# Old naming / duplicates
docker volume rm layra_colpali_models     # Superseded by model_weights
docker volume rm layra_cuda_cache         # Not in current compose
docker volume rm layra_sandbox_volume     # Duplicate of layra_layra_sandbox_volume
docker volume rm mysql_migrations         # No prefix - orphaned
```

## Cleanup Commands

### Preview (Dry Run)

```bash
# List orphan volumes (no prefix or deploy_ prefix)
docker volume ls | grep -E '^(deploy_|mysql_migrations$)'

# Check what would be removed
docker volume ls --format '{{.Name}}' | grep -E '^deploy_' | xargs -I{} echo "Would remove: {}"
```

### Remove All Orphans

```bash
# Remove deploy_ prefixed volumes (old setup)
docker volume ls --format '{{.Name}}' | grep '^deploy_' | xargs -r docker volume rm

# Remove deprecated layra volumes
docker volume rm layra_neo4j_data layra_neo4j_logs layra_colpali_models layra_cuda_cache 2>/dev/null

# Remove duplicates
docker volume rm layra_sandbox_volume mysql_migrations 2>/dev/null
```

## Volume Size Check

Before removing, check sizes:

```bash
docker system df -v | grep -E 'layra_|deploy_|mysql_'
```

## Caution

- **deploy_milvus_data** and **deploy_mongo_data** may contain important data if you previously used the deploy/ compose files
- **Always backup** before removing any volume with important data
- Some volumes may be in use by running containers - stop containers first

## One-Liner Cleanup

After confirming no important data:

```bash
# Stop all layra containers first
make down

# Remove all orphan volumes
docker volume ls --format '{{.Name}}' | grep '^deploy_' | xargs -r docker volume rm
docker volume rm layra_neo4j_data layra_neo4j_logs layra_colpali_models layra_cuda_cache layra_sandbox_volume mysql_migrations 2>/dev/null || true

# Restart
make up
```

# Docker Compose Deployment Guide

This guide explains the different Docker Compose configurations available for Layra and when to use each one.

## Quick Reference

| Deployment Mode | File(s) | GPU Required | Use Case |
|----------------|---------|--------------|----------|
| **Standard** | `docker-compose.yml` | Optional | Production, research, development with local or cloud embeddings |
| **Jina API (No GPU)** | `docker-compose.yml` + `EMBEDDING_MODEL=jina_embeddings_v4` | No | Limited/no GPU resources, quick testing |
| **Development** | `docker-compose.override.yml` (auto-applied) | Optional | Local development with custom settings |

**Note:** The legacy thesis compose file has been removed. For single-user demos, use the standard stack and set `SINGLE_TENANT_MODE=true`.

## Deployment Files

### docker-compose.yml (Root Directory)

**Purpose:** Main production configuration with full service stack

**Services Included:**
- Kafka (Apache image)
- MongoDB (persistent data)
- Milvus (vector database with MinIO backend)
- MinIO (object storage)
- Redis (caching)
- MySQL (relational data)
- Backend (FastAPI)
- Frontend (Next.js)
- Model Server (ColQwen2.5 embeddings)
- UnoServer (document conversion)

**Usage:**
```bash
# Standard deployment
./scripts/compose-clean up -d

# With Jina API embeddings (no GPU needed)
# Set EMBEDDING_MODEL=jina_embeddings_v4 in .env, then:
./scripts/compose-clean up -d
```

**When to Use:**
- Full-featured deployment
- Production environments
- Development with local embedding models
- Research workflows requiring GPU acceleration

**Environment Variables:**
See `.env.example` for required configuration. Key variables:
- `EMBEDDING_MODEL` - `colqwen2.5` (local GPU) or `jina_embeddings_v4` (cloud API)
- `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` - Required for LLM chat
- `MINIO_PUBLIC_URL` - Must be set to your server's public URL
- `SINGLE_TENANT_MODE` - Set to `true` for shared data across users

---

### docker-compose.override.yml (Root Directory)

**Purpose:** Optional local overrides for GPU/dev helpers (auto-applied by Docker Compose)

**What it Does:**
- Enables GPU access for the model-server service
- Configures CUDA_VISIBLE_DEVICES and NVIDIA runtime flags
- Adds Dozzle log viewer UI (port 8890)
- Automatically applied when running `./scripts/compose-clean up` from project root

**Usage:**
```bash
# Automatically applied in development
./scripts/compose-clean up

# Explicitly apply overrides
./scripts/compose-clean -f docker-compose.yml -f docker-compose.override.yml up -d --build

# Base configuration without auto-loading overrides
./scripts/compose-clean -f docker-compose.yml --no-override up -d
```

**When to Use:**
- Local development environment
- GPU debugging/tuning
- Optional log viewer access

**Prerequisites:**
- NVIDIA GPU driver installed
- nvidia-container-toolkit installed and configured
- Test with: `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`

**Note:** Docker Compose automatically loads `docker-compose.override.yml` if it exists in the same directory as `docker-compose.yml`. For production, prefer `docker-compose.yml` or `docker-compose.prod.yml`.

---

## Combining Configurations

Docker Compose supports multiple compose files using the `-f` flag. Files are merged in order, with later files overriding earlier ones.

**Examples:**

```bash
# Standard deployment with explicit override
./scripts/compose-clean -f docker-compose.yml -f docker-compose.override.yml up -d

# Base configuration without auto-loading overrides
./scripts/compose-clean -f docker-compose.yml --no-override up -d

# Custom deployment directory
./scripts/compose-clean -f /path/to/docker-compose.yml -f /path/to/docker-compose.override.yml up -d
```

## GPU Setup

### Prerequisites

1. **NVIDIA Driver**
   ```bash
   nvidia-smi  # Should show GPU info
   ```

2. **NVIDIA Container Toolkit**
   ```bash
   sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

3. **Verify GPU Access**
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
   ```

### Troubleshooting GPU Issues

| Problem | Solution |
|---------|----------|
| `could not select device driver ""` | Install nvidia-container-toolkit (see above) |
| GPU not visible inside container | Check `CUDA_VISIBLE_DEVICES` environment variable |
| Out of memory errors | Reduce batch size or use Jina API embeddings |

## Environment Configuration

### Required Files

1. **`.env`** - Main environment configuration
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

### Critical Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MINIO_PUBLIC_URL` | Yes | (none) | Public URL for MinIO (e.g., `http://your-server:9000`) |
| `SECRET_KEY` | Yes | (auto) | JWT signing key (min 32 characters) |
| `OPENAI_API_KEY` | No* | (none) | OpenAI API key for chat LLM |
| `DEEPSEEK_API_KEY` | No* | (none) | DeepSeek API key for chat LLM |
| `ZHIPUAI_API_KEY` | No* | (none) | ZhipuAI API key for chat LLM |
| `EMBEDDING_MODEL` | No | `colqwen2.5` | Embedding model: `colqwen2.5` or `jina_embeddings_v4` |
| `SINGLE_TENANT_MODE` | No | `false` | Share data across all users if `true` |

*At least one LLM API key is required for chat functionality

## Common Workflows

### Start Fresh Deployment
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # Set MINIO_PUBLIC_URL, API keys, etc.

# Start services
./scripts/compose-clean up -d

# Check status
./scripts/compose-clean ps
./scripts/compose-clean logs -f backend
```

### Update and Restart
```bash
# Pull latest changes
git pull

# Rebuild and restart
./scripts/compose-clean up -d --build

# View logs
./scripts/compose-clean logs -f
```

### Complete Reset (WARNING: Destroys Data)
```bash
# Stop and remove all containers
./scripts/compose-clean down -v

# Remove all volumes (deletes all data!)
docker volume rm layra_kafka_data layra_mongo_data layra_minio_data \
                 layra_redis_data layra_milvus_data layra_milvus_minio \
                 layra_milvus_etcd

# Start fresh
./scripts/compose-clean up -d
```

### Single-Tenant Demo (Optional)
```bash
# Set SINGLE_TENANT_MODE=true in .env, then:
./scripts/compose-clean up -d --build
```

### Access Service Containers
```bash
# Backend shell
docker exec -it layra-backend bash

# MongoDB shell
docker exec -it layra-mongodb-1 mongosh

# Redis CLI
docker exec -it layra-redis redis-cli

# MinIO MC (configure first)
docker exec -it layra-minio mc alias set local http://localhost:9000 minioadmin minioadmin
```

## Monitoring and Debugging

### View Logs
```bash
# All services
./scripts/compose-clean logs -f

# Specific service
./scripts/compose-clean logs -f backend
./scripts/compose-clean logs -f model-server

# Last 100 lines
./scripts/compose-clean logs --tail=100 backend
```

### Resource Usage
```bash
# Live stats
docker stats

# Check disk space
df -h

# Check volume sizes
docker system df -v
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/api/v1/health/check

# Service status
./scripts/compose-clean ps
```

## Network Architecture

All services communicate on the `layra-net` Docker network:

- **Backend** (port 8000) - FastAPI application
- **Frontend** (port 3000) - Next.js web interface
- **MinIO** (port 9000) - Object storage (files, documents)
- **MongoDB** (port 27017) - Primary database
- **Milvus** (port 19530) - Vector database
- **Redis** (port 6379) - Cache and message broker
- **Kafka** (port 9094 external) - Event streaming
- **MySQL** (port 3306) - Relational data
- **Model Server** (port 8005) - Embedding model inference
- **UnoServer** (port 2002) - Document conversion

## Persistent Data

### Volumes

| Volume | Purpose | Size Estimate |
|--------|---------|---------------|
| `layra_kafka_data` | Event logs | 1-5 GB |
| `layra_mongo_data` | Application data | 100 MB - 1 GB |
| `layra_minio_data` | Files, documents | Variable (user content) |
| `layra_redis_data` | Cache | 10-100 MB |
| `layra_milvus_data` | Vector embeddings | 1-10 GB per 100K documents |
| `layra_milvus_minio` | Milvus internal | 100 MB - 1 GB |
| `layra_milvus_etcd` | Milvus metadata | 10-50 MB |
| `layra_model_weights` | ML model files | 5-10 GB |
| `layra_mysql_data` | Relational data | 10-100 MB |

### Backup and Restore

**Backup:**
```bash
# MinIO data
docker run --rm -v layra_minio_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/minio-backup-$(date +%Y%m%d).tar.gz -C /data .

# MongoDB data
docker exec layra-mongodb-1 mongodump --db layra --out /tmp/backup
docker cp layra-mongodb-1:/tmp/backup ./mongodb-backup-$(date +%Y%m%d)
```

**Restore:**
```bash
# MinIO
docker run --rm -v layra_minio_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/minio-backup-YYYYMMDD.tar.gz -C /data

# MongoDB
docker cp ./mongodb-backup-YYYYMMDD layra-mongodb-1:/tmp/restore
docker exec layra-mongodb-1 mongorestore --db layra /tmp/restore
```

## Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Check what's using the port
sudo lsof -i :8000

# Change port in docker-compose.yml
# or stop the conflicting service
```

**Permission Denied on Volumes**
```bash
# Fix volume permissions
./scripts/compose-clean down
sudo chown -R $USER:$USER /var/lib/docker/volumes/layra_*
./scripts/compose-clean up -d
```

**Container Keeps Restarting**
```bash
# Check logs
./scripts/compose-clean logs service-name

# Inspect the container
docker inspect layra-service-name
```

**Out of Disk Space**
```bash
# Clean up unused images
docker system prune -a --volumes

# Check what's taking space
docker system df -v
```

### Getting Help

1. Check logs: `./scripts/compose-clean logs -f [service]`
2. Check service status: `./scripts/compose-clean ps`
3. Review this guide
4. Check archived configurations in `scripts/archive/docker-compose/`
5. Open an issue with:
   - Docker Compose version
   - Error messages from logs
   - System info (OS, Docker version, GPU model)

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit)
- Project Main README: `/README.md`
- Rollback Strategy: `deploy/README.md`

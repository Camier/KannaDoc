# Production Deployment Guide

This document outlines the steps and prerequisites for deploying LAYRA (KannaDoc) in a production environment.

## Prerequisites

### Hardware Requirements
- **GPU**: NVIDIA GPU with at least 16GB VRAM (required for `local_colqwen` embedding model).
- **CPU**: Multi-core processor (8+ cores recommended).
- **RAM**: 32GB+ system memory recommended.
- **Storage**: SSD with at least 100GB free space for models and data.

### Software Requirements
- **Docker**: Version 20.10.0 or higher.
- **Docker Compose**: Version 1.29.0 or higher (supporting `deploy.resources.limits`).
- **NVIDIA Container Toolkit**: Required for GPU pass-through to containers.

### Network Requirements
- Ports to be opened on the host (depending on your firewall configuration):
  - `8090`: Public access via Nginx (Proxy to Frontend and API).
  - `3001`: Grafana Dashboard access.
  - `9090`: Prometheus (Internal or restricted access recommended).
  - `9080/9081`: MinIO Console (restricted access recommended).

---

## Environment Configuration

Copy `.env.example` to `.env` and configure the following critical variables:

### Security
- `ALLOWED_ORIGINS`: Explicit list of allowed CORS origins (e.g., `https://your-domain.com`). **Must not be `*`**.
- `SECRET_KEY`: Generate a secure random hex string using `openssl rand -hex 32`.

### Database Passwords
Ensure these are set to strong, unique values:
- `REDIS_PASSWORD`
- `MONGODB_ROOT_PASSWORD`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `MINIO_SECRET_KEY`

### LLM & APIs
- `OPENAI_API_KEY`: Required if using OpenAI models.
- `MINIMAX_API_KEY`: Required for Entity Extraction V2.
- `EMBEDDING_MODEL`: Set to `local_colqwen` (requires GPU) or `jina_embeddings_v4` (requires `JINA_API_KEY`).

---

## Deployment Steps

1.  **Prepare the environment**:
    ```bash
    cp .env.example .env
    # Edit .env with your production values
    vi .env
    ```

2.  **Build production images**:
    ```bash
    docker compose -f docker-compose.prod.yml build
    ```

3.  **Start the stack**:
    ```bash
    docker compose -f docker-compose.prod.yml up -d
    ```

4.  **Verify running services**:
    ```bash
    docker compose -f docker-compose.prod.yml ps
    ```

---

## Health Check Verification

The system provides two levels of health monitoring:

### 1. Liveness Probe (Fast)
Verifies the API is up and responding.
- **URL**: `GET http://localhost:8090/api/v1/health/check`
- **Expected Response**: `{"status": "UP", ...}`

### 2. Readiness Probe (Deep)
Verifies all backend dependencies (MySQL, MongoDB, Redis, Milvus, MinIO, Kafka) are accessible.
- **URL**: `GET http://localhost:8090/api/v1/health/ready`
- **Expected Response**: `200 OK` with `"status": "healthy"`.

---

## Backup and Restore

### Backup
A comprehensive backup script is provided in `deploy/scripts/backup.sh`. It performs logical dumps of databases and volume snapshots for object/vector stores.

```bash
# Create a full backup in the default location (/tmp/layra_backups)
./deploy/scripts/backup.sh

# Or specify an output directory
./deploy/scripts/backup.sh /path/to/backups/
```

### Restore
Refer to `deploy/ROLLBACK_STRATEGY.md` for detailed instructions on restoring from backups and rolling back service versions.

---

## Monitoring and Observability

### Dashboards
- **Grafana**: `http://localhost:3001`
  - Default Credentials: `admin` / `${GRAFANA_PASSWORD}` (default is `admin` if not changed in `.env`).
  - Pre-configured with "System Overview" dashboards.
- **Prometheus**: `http://localhost:9090`
  - Used for querying raw metrics and alert status.

### Logging
- Logs are stored in JSON format for easy ingestion.
- **Container Logs**: `docker compose -f docker-compose.prod.yml logs -f [service_name]`
- **Log Rotation**: Both application logs and Docker container logs are configured for rotation (50MB max-size, 3 files).

---

## Troubleshooting

### GPU Issues
If `model-server` fails to start or detect the GPU:
1.  Verify `nvidia-smi` works on the host.
2.  Ensure `nvidia-container-toolkit` is installed and Docker is restarted.
3.  Check `docker-compose.prod.yml`'s `model-server` deploy section for correct GPU reservation.

### Connection Timeouts
If `/api/v1/health/ready` returns `degraded` or `unhealthy`:
1.  Check the `checks` field in the response to identify the failing service.
2.  Inspect logs for that service: `docker compose -f docker-compose.prod.yml logs <service_name>`.
3.  Ensure your firewall allows internal Docker network communication (default bridge).

### Feature Degradation
- **Sandbox**: The Python code sandbox is **DISABLED** in production for security reasons (no Docker socket mount). Features requiring the sandbox will return an error or fallback behavior.

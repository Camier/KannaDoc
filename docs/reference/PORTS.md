# Layra System Ports Reference

This document provides a comprehensive reference of all ports used by the Layra system, including their purpose, configurability, and default values.

## Quick Reference

| Service | Internal Port | External Port | Configurable | Default Value |
|---------|---------------|---------------|--------------|---------------|
| **Application** |
| Nginx (Frontend) | 80 | 8090 | No | 8090 |
| Backend API | 8000 | - | No | 8000 |
| Model Server | 8005 | - | Yes | 8005 |
| **Databases** |
| MySQL | 3306 | - | Yes | 3306 |
| MongoDB | 27017 | - | Yes | 27017 |
| Redis | 6379 | - | Yes | 6379 |
| Milvus (Vector DB) | 19530 | - | Yes | 19530 |
| Qdrant (Vector DB) | 6333/6334 | 6333/6334 | Yes | 6333 |
| **Storage** |
| MinIO API | 9000 | - | Yes | 9000 |
| MinIO Console | 9001 | - | Yes | 9001 |
| **Messaging** |
| Kafka (Internal) | 9092 | - | Infrastructure | 9092 |
| Kafka (External) | 9094 | - | Infrastructure | 9094 |
| Kafka Controller | 9093 | - | Infrastructure | 9093 |
| **Monitoring** |
| Prometheus | 9090 | 9090 | No | 9090 |
| Grafana | 3000 | 3001 | No | 3001 |
| **Document Processing** |
| UnoServer | 2003 | - | Yes | 2003 |
| **Milvus Dependencies** |
| Milvus Etcd | 2379 | - | Infrastructure | 2379 |
| Milvus Standalone | 9091 | - | Infrastructure | 9091 |

## Detailed Port Configuration

### User-Facing Ports (Configurable)

These ports are exposed to end users and can be configured via environment variables.

#### MinIO Ports

**Purpose:** Object storage for files and documents

- **API Port:** 9000 (default)
  - Environment variable: `MINIO_URL` (internal), `MINIO_PUBLIC_URL` (external)
  - Example: `MINIO_URL=http://minio:9000`
  - Example: `MINIO_PUBLIC_URL=http://your-domain.com:9000`

- **Console Port:** 9001 (default)
  - Configured in docker-compose.yml
  - Command: `server /data --console-address :9001`

**Configuration:**
```bash
# .env
MINIO_URL=http://minio:9000
MINIO_PUBLIC_URL=http://your-domain.com:9000
MINIO_PUBLIC_PORT=9000
```

**Note:** For production deployment, always set `MINIO_PUBLIC_URL` to your actual domain name. The fallback uses `server_ip:minio_public_port` which only works for localhost access.

#### Model Server Port

**Purpose:** Embedding generation and model inference

- **Port:** 8005 (default)
- **Environment variable:** `MODEL_SERVER_URL`
- **Example:** `MODEL_SERVER_URL=http://model-server:8005`

**Configuration:**
```bash
# .env
MODEL_SERVER_URL=http://model-server:8005
```

**Used by:**
- `/backend/app/rag/get_embedding.py` - Text and image embeddings
- Backend workflow engine for model inference

#### Database Ports

**MySQL (Relational Database)**
- **Port:** 3306 (default)
- **Environment variable:** Embedded in `DB_URL`
- **Example:** `DB_URL=mysql+asyncmy://user:pass@mysql:3306/dbname`

**MongoDB (Document Store)**
- **Port:** 27017 (default)
- **Environment variable:** `MONGODB_URL`
- **Example:** `MONGODB_URL=mongodb:27017`

**Redis (Cache & Message Broker)**
- **Port:** 6379 (default)
- **Environment variable:** `REDIS_URL`
- **Example:** `REDIS_URL=redis:6379`

**Milvus (Vector Database)**
- **Port:** 19530 (default)
- **Environment variable:** `MILVUS_URI`
- **Example:** `MILVUS_URI=http://milvus-standalone:19530`

**Qdrant (Alternative Vector DB)**
- **HTTP Port:** 6333
- **Metrics Port:** 6334
- **Environment variable:** `QDRANT_URL`
- **Example:** `QDRANT_URL=http://qdrant:6333`

#### Document Processing Ports

**UnoServer (LibreOffice conversion)**
- **Port:** 2003 (default)
- **Environment variable:** `UNOSERVER_BASE_PORT`
- **Example:** `UNOSERVER_BASE_PORT=2003`

### Infrastructure Ports (Documented Only)

These ports are used for internal service communication and should generally not be changed.

#### Kafka Ports

**Purpose:** Distributed event streaming platform

- **9092** - Internal PLAINTEXT listener (broker-to-broker)
- **9093** - Controller listener (controller coordination)
- **9094** - External listener (client connections)

**Configuration:**
- Environment variable: `KAFKA_BROKER_URL`
- Default value: `kafka:9094`
- Example: `KAFKA_BROKER_URL=kafka:9094`

**Internal Configuration (docker-compose.yml):**
```yaml
KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093,EXTERNAL://:9094
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092,EXTERNAL://kafka:9094
```

#### Milvus Dependency Ports

**Etcd (Milvus metadata store)**
- **Port:** 2379
- **Purpose:** Distributed key-value store for Milvus coordination

**Milvus Standalone**
- **Port:** 9091
- **Purpose:** Milvus health check and metrics endpoint

### Monitoring Ports (Configurable)

These ports are exposed for monitoring and visualization.

#### Prometheus

**Purpose:** Metrics collection and storage

- **Port:** 9090
- **External mapping:** 9090:9090
- **Access:** http://localhost:9090
- **Configuration:** `docker-compose.yml` port mapping

#### Grafana

**Purpose:** Metrics visualization and dashboards

- **Internal Port:** 3000
- **External Port:** 3001 (mapped to avoid conflicts)
- **Access:** http://localhost:3001
- **Configuration:** `docker-compose.yml` port mapping

### Application Ports (Fixed)

These ports are defined by the application architecture and should not be changed.

#### Nginx (Frontend Gateway)

**Purpose:** Reverse proxy and static file serving

- **Internal Port:** 80
- **External Port:** 8090
- **Access:** http://localhost:8090
- **Configuration:** `docker-compose.yml` port mapping

#### Backend API

**Purpose:** FastAPI application server

- **Port:** 8000 (internal only, accessed via Nginx)
- **Health check:** http://localhost:8000/api/v1/health/check
- **Configuration:** Internal to Docker network

## Port Conflict Resolution

If you encounter port conflicts on your system:

1. **Identify the conflicting port:**
   ```bash
   # Linux/Mac
   lsof -i :<port>

   # Or
   netstat -tulpn | grep <port>
   ```

2. **Configure alternative ports:**
   - Edit `.env` file and set the appropriate `*_PORT` or `*_URL` variable
   - Update `docker-compose.yml` port mappings if needed

3. **Restart services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Security Considerations

### Internal vs External Ports

- **Internal Ports** (e.g., 3306, 27017, 6379): Only accessible within Docker network
- **External Ports** (e.g., 8090, 9000, 9090): Mapped to host and accessible externally

### Production Deployment

For production deployments:

1. **Change default passwords** for all services
2. **Use HTTPS** for external endpoints (configure SSL/TLS certificates)
3. **Restrict external access** to monitoring ports (Prometheus, Grafana)
4. **Set `MINIO_PUBLIC_URL`** to your actual domain name
5. **Configure firewall rules** to only expose necessary ports
6. **Use internal DNS** for service-to-service communication

## Port Reference by Service

```yaml
# Docker Compose Port Mappings Summary

services:
  nginx:
    ports: ["8090:80"]              # Frontend gateway

  backend:
    # No external port mapping (accessed via nginx)

  model-server:
    # No external port mapping (internal only)

  mysql:
    # Port 3306 (internal only)

  mongodb:
    # Port 27017 (internal only)

  redis:
    # Port 6379 (internal only)

  minio:
    # Port 9000 (internal API)
    # Port 9001 (console, internal only)

  kafka:
    # Ports 9092, 9093, 9094 (internal only)

  milvus-standalone:
    # Port 19530 (internal only)
    # Port 9091 (health check, internal only)

  milvus-etcd:
    # Port 2379 (internal only)

  qdrant:
    ports: ["6333:6333", "6334:6334"]  # Vector DB

  prometheus:
    ports: ["9090:9090"]              # Monitoring

  grafana:
    ports: ["3001:3000"]              # Dashboards

  unoserver:
    # Port 2003 (internal only)
```

## Troubleshooting

### Port Already in Use

**Error:** `Error: bind: address already in use`

**Solution:**
```bash
# Find process using the port
sudo lsof -i :<port>

# Kill the process or use a different port
```

### Connection Refused

**Error:** `Connection refused` or `ECONNREFUSED`

**Possible causes:**
1. Service not running
2. Wrong port in configuration
3. Firewall blocking connection
4. Service not exposed in Docker network

**Solution:**
```bash
# Check if service is running
docker ps

# Check service logs
docker logs <container_name>

# Verify port configuration
docker-compose config
```

### Presigned URL Generation Fails

**Error:** MinIO presigned URLs use localhost instead of actual IP

**Solution:**
```bash
# Set MINIO_PUBLIC_URL in .env
MINIO_PUBLIC_URL=http://your-actual-domain.com:9000

# Or set MINIO_PUBLIC_PORT if using default IP
MINIO_PUBLIC_PORT=9000
```

## Related Documentation

- [Configuration Guide](/docs/CONFIGURATION.md)
- [Deployment Guide](/docs/DEPLOYMENT.md)
- [Security Best Practices](/docs/SECURITY.md)
- [Environment Variables](/.env.example)

## Version History

- **2026-01-27:** Initial documentation
  - Documented all system ports
  - Added configuration examples
  - Added troubleshooting section
  - Made model-server port configurable
  - Made MinIO public port configurable

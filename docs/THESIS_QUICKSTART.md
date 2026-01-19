# Layra Solo Thesis Deployment - Quick Start Guide

## 🚀 5-Minute Setup

### Prerequisites

```bash
# Check GPU
nvidia-smi

# Check Docker
docker --version
docker compose version

# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### Step 1: Configure Environment

```bash
cd /LAB/@thesis/layra

# Edit passwords in .env.thesis
nano .env.thesis
```

**Critical passwords to change:**
- `NEO4J_PASSWORD` - Neo4j database
- `REDIS_PASSWORD` - Redis cache
- `MONGODB_ROOT_PASSWORD` - MongoDB
- `MINIO_SECRET_KEY` - Object storage
- `SIMPLE_PASSWORD` - Application login

### Step 2: Deploy

```bash
# Run deployment script
./deploy-thesis.sh
```

**Expected timeline:**
- First run: 5-10 minutes (downloading 15GB models)
- Subsequent runs: 1-2 minutes

### Step 3: Access

```bash
# Layra Application
URL: http://localhost:8090
Username: thesis
Password: (from SIMPLE_PASSWORD)

# Neo4j Browser
URL: http://localhost:7474
Username: neo4j
Password: (from NEO4J_PASSWORD)
```

## 📊 Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER ACCESS LAYER                         │
│  http://localhost:8090 (Layra)                              │
│  http://localhost:7474 (Neo4j Browser)                      │
├─────────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ frontend    │  │ backend     │  │ model-      │         │
│  │ (Next.js)   │  │ (FastAPI)   │  │ server      │         │
│  │ :3000       │  │ :8000       │  │ (GPU)       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Neo4j   │ │ Milvus   │ │ MongoDB  │ │  Redis   │        │
│  │ :7687    │ │ :19530   │ │ :27017   │ │ :6379    │        │
│  │ (Graph)  │ │ (Vector) │ │ (Docs)   │ │ (Cache)  │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐                                  │
│  │  MinIO   │ │  Kafka   │                                  │
│  │ :9000    │ │ :9094    │                                  │
│  │ (Files)  │ │ (Queue)  │                                  │
│  └──────────┘ └──────────┘                                  │
├─────────────────────────────────────────────────────────────┤
│                    AI PROCESSING                              │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ ColQwen2.5   │  │ Unoserver    │                        │
│  │ (Embeddings) │  │ (Document    │                        │
│  │              │  │  Conversion) │                        │
│  │ ~15GB GPU    │  │              │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Common Tasks

### View Logs

```bash
# All services
docker compose -f docker-compose.thesis.yml logs -f

# Specific service
docker compose -f docker-compose.thesis.yml logs -f backend
docker compose -f docker-compose.thesis.yml logs -f model-server
docker compose -f docker-compose.thesis.yml logs -f neo4j
```

### Restart Services

```bash
# All services
docker compose -f docker-compose.thesis.yml restart

# Specific service
docker compose -f docker-compose.thesis.yml restart backend
```

### Stop Deployment

```bash
docker compose -f docker-compose.thesis.yml down
```

### Clean Restart

```bash
# Stop and remove volumes (⚠️ deletes data)
docker compose -f docker-compose.thesis.yml down -v

# Redeploy
./deploy-thesis.sh
```

### Access Containers

```bash
# Backend shell
docker exec -it layra-backend bash

# Neo4j shell
docker exec -it layra-neo4j cypher-shell

# Neo4j bash
docker exec -it layra-neo4j bash

# MongoDB shell
docker exec -it layra-mongodb mongosh -u thesis -p
```

## 🔧 Configuration

### Adjust GPU Memory

Edit `docker-compose.thesis.yml`:
```yaml
model-server:
  deploy:
    resources:
      limits:
        memory: 8G  # Increase if you have more GPU memory
```

### Adjust Worker Count

Edit `.env.thesis`:
```bash
MAX_WORKERS=8  # Increase for more parallel processing
```

### Change Model Download Source

Edit `.env.thesis`:
```bash
# China mirror (faster in China)
MODEL_BASE_URL=https://hf-mirror.com/vidore

# Official (slower but reliable)
MODEL_BASE_URL=https://huggingface.co/vidore
```

## 📈 Performance Tuning

### For RTX 3090 (24GB)

```bash
# .env.thesis
MAX_WORKERS=4
EMBEDDING_IMAGE_DPI=200

# docker-compose.thesis.yml - model-server
CUDA_VISIBLE_DEVICES=0
```

### For RTX 4090 (24GB)

```bash
# .env.thesis
MAX_WORKERS=6
EMBEDDING_IMAGE_DPI=300  # Higher quality
```

### For A100 (40GB+)

```bash
# .env.thesis
MAX_WORKERS=10
EMBEDDING_IMAGE_DPI=300
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8090
sudo lsof -i :8090

# Kill the process
sudo kill -9 <PID>
```

### GPU Not Available

```bash
# Check GPU status
nvidia-smi

# Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Restart Docker if needed
sudo systemctl restart docker
```

### Model Download Failed

```bash
# Check logs
docker compose -f docker-compose.thesis.yml logs model-weights-init

# Manually retry
docker compose -f docker-compose.thesis.yml restart model-weights-init
```

### Backend Not Starting

```bash
# Check dependencies
docker compose -f docker-compose.thesis.yml ps

# Check backend logs
docker compose -f docker-compose.thesis.yml logs backend

# Verify health check
curl http://localhost:8090/api/v1/health/check
```

### Neo4j Not Accessible

```bash
# Check Neo4j logs
docker compose -f docker-compose.thesis.yml logs neo4j

# Reset Neo4j password
docker exec -it layra-neo4j cypher-shell
# Then: ALTER USER neo4j SET PASSWORD 'new_password';
```

## 💾 Data Management

### Backup All Data

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup MongoDB
docker exec layra-mongodb mongodump --archive=/backup/mongo.tar.gz
docker cp layra-mongodb:/backup/mongo.tar.gz backups/$(date +%Y%m%d)/

# Backup Neo4j
docker exec layra-neo4j neo4j-admin database dump neo4j --to-path=/backup
docker cp layra-neo4j:/backup/* backups/$(date +%Y%m%d)/neo4j/

# Backup MinIO
docker cp layra-minio:/data backups/$(date +%Y%m%d)/minio_data
```

### Restore from Backup

```bash
# Restore MongoDB
docker cp backups/20240119/mongo.tar.gz layra-mongodb:/backup/mongo.tar.gz
docker exec layra-mongodb mongorestore --archive=/backup/mongo.tar.gz

# Restore Neo4j
docker cp backups/20240119/neo4j/* layra-neo4j:/backup/
docker exec layra-neo4j neo4j-admin database load neo4j --from-path=/backup --force
```

### Clear All Data

```bash
# ⚠️ WARNING: This deletes all data
docker compose -f docker-compose.thesis.yml down -v
./deploy-thesis.sh
```

## 📘 API Documentation

### Interactive API Docs

| Documentation | URL |
|--------------|-----|
| **Swagger UI** | http://localhost:8090/api/docs |
| **ReDoc** | http://localhost:8090/api/redoc |

### Key Endpoints

| Category | Path | Description |
|----------|------|-------------|
| Auth | `/api/v1/auth/login` | User authentication |
| Health | `/api/v1/health/check` | System health check |
| Workflows | `/api/v1/workflow/*` | Workflow management |
| Chat | `/api/v1/chat/*` | Real-time chat (SSE) |
| Knowledge Base | `/api/v1/knowledge-base/*` | Document management |

### Configuration Note

The backend is running with OpenAPI documentation enabled. Access the interactive API explorer to explore all available endpoints, request/response schemas, and try out API calls directly from the browser.

---

## 📚 Next Steps

1. **API Documentation**: http://localhost:8090/api/docs (Swagger UI)
2. **Create First Workflow**: http://localhost:8090/work-flow
3. **Upload Documents**: http://localhost:8090/knowledge-base
4. **Explore Neo4j**: http://localhost:7474
5. **Read Documentation**: `docs/NEO4J_INTEGRATION.md`

## 🆘 Support

- **Logs**: `docker compose -f docker-compose.thesis.yml logs -f`
- **Status**: `docker compose -f docker-compose.thesis.yml ps`
- **Health**: `curl http://localhost:8090/api/v1/health/check`

---

**Deployment Time**: ~5-10 minutes (first run)
**Disk Space**: ~100GB recommended
**GPU Memory**: 16GB+ recommended
**RAM**: 32GB recommended

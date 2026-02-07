# Layra Quick Start (Standard Stack)

**Version:** 2.1.0  
**Last Updated:** 2026-01-28

> ⚠️ **Important:** Use `./scripts/compose-clean` (or `./scripts/start_layra.sh`) to avoid host env var pollution overriding `.env`.

## 🚀 5-Minute Setup

## 🆕 Recent Significant Changes (2026-01-25)

- ✅ **LiteLLM Removed** - Now using direct OpenAI/DeepSeek APIs
- ✅ **Neo4j Removed** (default stack) - Saves 500MB RAM
- ✅ **KB Corruption Fixed** - 0 duplicates, validated
- ✅ **Documentation Reorganized** - See [INDEX.md](../INDEX.md)

*Details: [CHANGES_20260125.md](CHANGES_20260125.md)*

## 📊 Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER ACCESS LAYER                         │
│  http://localhost:8090 (Layra)                              │
│  Neo4j: disabled (not deployed)                             │
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
│  │  MySQL   │ │ Milvus   │ │ MongoDB  │ │  Redis   │        │
│  │ :3306    │ │ :19530   │ │ :27017   │ │ :6379    │        │
│  │ (Rel)    │ │ (Vector) │ │ (Docs)   │ │ (Cache)  │        │
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
./scripts/compose-clean logs -f

# Specific service
./scripts/compose-clean logs -f backend
./scripts/compose-clean logs -f model-server
```

### Restart Services

```bash
# All services
./scripts/compose-clean restart

# Specific service
./scripts/compose-clean restart backend
```

### Stop Deployment

```bash
./scripts/compose-clean down
```

### Clean Restart

```bash
# Stop and remove volumes (⚠️ deletes data)
./scripts/compose-clean down -v

# Redeploy
./scripts/start_layra.sh
```

### Access Containers

```bash
# Backend shell
docker exec -it layra-backend bash

# MongoDB shell
docker exec -it layra-mongodb mongosh -u <mongo_user> -p
```

## 🔧 Configuration

### Adjust GPU Memory

Edit `docker-compose.yml`:
```yaml
model-server:
  deploy:
    resources:
      limits:
        memory: 8G  # Increase if you have more GPU memory
```

### Adjust Worker Count

Edit `.env`:
```bash
MAX_WORKERS=8  # Increase for more parallel processing
```

### Change Model Download Source

Edit `.env`:
```bash
# China mirror (faster in China)
MODEL_BASE_URL=https://hf-mirror.com/vidore

# Official (slower but reliable)
MODEL_BASE_URL=https://huggingface.co/vidore
```

## 📈 Performance Tuning

### For RTX 3090 (24GB)

```bash
# .env
MAX_WORKERS=4
EMBEDDING_IMAGE_DPI=200

# docker-compose.yml - model-server
CUDA_VISIBLE_DEVICES=0
```

### For RTX 4090 (24GB)

```bash
# .env
MAX_WORKERS=6
EMBEDDING_IMAGE_DPI=300  # Higher quality
```

### For A100 (40GB+)

```bash
# .env
MAX_WORKERS=10
EMBEDDING_IMAGE_DPI=300
```
## 🔍 Deployment Audit & Verification

### Quick Health Check
```bash
# Verify all services are running
./scripts/compose-clean ps

# Check backend API health
curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/v1/health/check
# Should return: 200
```

### Service Status Verification
```bash
# Check healthy containers
docker ps --filter "health=healthy" --format "table {{.Names}}\t{{.Status}}"

# Expected services (all healthy):
# - layra-backend, layra-frontend, layra-nginx
# - layra-mysql, layra-redis, layra-mongodb
# - layra-minio, layra-milvus-standalone, layra-milvus-etcd, layra-milvus-minio
# - layra-kafka, layra-kafka-init, layra-unoserver
# - layra-model-server, layra-model-weights-init
```

### Credential Verification
```bash
# Extract key env config from backend container
docker exec layra-backend env | grep -E '(MINIO|MYSQL|MONGODB|REDIS|KAFKA|MILVUS)' | grep -v PATH

# Verify application login
curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<username>","password":"<password>"}' \
  -s | grep -q "access_token" && echo "Auth OK"
```

### Resource Monitoring
```bash
# Check resource usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
  $(docker ps --filter "name=layra-" --format "{{.Names}}")

# Check GPU utilization (if available)
docker exec layra-model-server nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader
```

### Log Inspection
```bash
# Recent backend logs (last 20 lines)
./scripts/compose-clean logs --tail=20 backend

# Check for Kafka connectivity issues
./scripts/compose-clean logs backend | grep -i kafka | tail -10

# Monitor real-time logs
./scripts/compose-clean logs -f --tail=50
```

### Comprehensive Audit Script
A complete deployment audit can be performed with:
```bash
cd /LAB/@thesis/layra
./scripts/snapshot_data.sh audit
```
*(Requires `scripts/snapshot_data.sh` to be executable)*


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
./scripts/compose-clean logs model-weights-init

# Manually retry
./scripts/compose-clean restart model-weights-init
```

### Backend Not Starting

```bash
# Check dependencies
./scripts/compose-clean ps

# Check backend logs
./scripts/compose-clean logs backend

# Verify health check
curl http://localhost:8090/api/v1/health/check
```

### Deep Forensics & Migration

- **System-wide issues?** See [CONSOLIDATED_REPORT.md](CONSOLIDATED_REPORT.md)
- **KB issues?** See [DRIFT_FORENSICS_20260125.md](DRIFT_FORENSICS_20260125.md)
- **Migration from v1.x?** See [LITELLM_REMOVAL_GUIDE.md](LITELLM_REMOVAL_GUIDE.md)

## 💾 Data Management

### Backup All Data

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup MongoDB
docker exec layra-mongodb mongodump --archive=/backup/mongo.tar.gz
docker cp layra-mongodb:/backup/mongo.tar.gz backups/$(date +%Y%m%d)/

# Backup MinIO
docker cp layra-minio:/data backups/$(date +%Y%m%d)/minio_data
```

### Restore from Backup

```bash
# Restore MongoDB
docker cp backups/20240119/mongo.tar.gz layra-mongodb:/backup/mongo.tar.gz
docker exec layra-mongodb mongorestore --archive=/backup/mongo.tar.gz
```

### Clear All Data

```bash
# ⚠️ WARNING: This deletes all data
./scripts/compose-clean down -v
./scripts/start_layra.sh
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

### Deploy Thesis Workflow Blueprint (Optional)

Once the system is running, you can deploy the pre-configured thesis workflow blueprint. This requires an existing user account.

```bash
# Set credentials for the target user
export THESIS_USERNAME=<username>
export THESIS_PASSWORD=<password>

# Deploy full iterative workflow (recommended)
python3 scripts/deploy_thesis_workflow_full.py

# Or deploy simplified workflow (faster)
python3 scripts/deploy_thesis_workflow_full_simple.py
```

This will create a workflow named `thesis_<UUID>` in the system, ready for processing.

### 📊 System Verification & Milvus Access

After deployment, verify that vector search is functional:

```bash
# Check Milvus collection from inside backend container
docker exec layra-backend python3 -c "
from pymilvus import MilvusClient
client = MilvusClient('http://milvus-standalone:19530')
collections = client.list_collections()
for col in collections:
    print(f'Collection: {col}')
    stats = client.get_collection_stats(col)
    print(f'Row count: {stats.get(\"row_count\", 0)}')
"

# Expected output:
# Collection: <collection_name>
# Row count: <row_count>
```

**Important Note about Milvus Access:**
- Containers access Milvus internally via `http://milvus-standalone:19530`.
- The host can access Milvus via `http://127.0.0.1:19531` (published from `docker-compose.yml` to avoid clashing with a host Milvus on `:19530`).
- If you run diagnostics *inside* a container, do not use `http://127.0.0.1:19530` (it points to the container itself).

For quick verification:
```bash
docker exec layra-backend python3 -c "from pymilvus import MilvusClient; client = MilvusClient('http://milvus-standalone:19530'); print('Collections:', client.list_collections())"
```

### Verify Deployed Workflow

Check that the thesis workflow blueprint is properly deployed:

```bash
# List workflows for a user
curl -s -X GET http://localhost:8090/api/v1/workflow/users/<username>/workflows \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8090/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=<username>&password=<password>" | jq -r '.access_token')" | jq .

# Expected output includes workflow IDs that start with "thesis_"
```

### Test RAG Query via API

```bash
# Create a conversation (prerequisite for chat)
curl -s -X POST http://localhost:8090/api/v1/chat/conversations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test_conv_1",
    "username": "<username>",
    "conversation_name": "Test Conversation",
    "chat_model_config": {
      "selected_model": "local_colqwen",
      "knowledge_bases": ["<knowledge_base_id>"]
    }
  }'
```

**Workflow Location**: `workflows/thesis_blueprint_minutieux/` - Contains code nodes and prompts for thesis automation.

---

## 📚 Next Steps

1. **API Documentation**: http://localhost:8090/api/docs (Swagger UI)
2. **Create First Workflow**: http://localhost:8090/work-flow
3. **Upload Documents**: http://localhost:8090/knowledge-base
4. **Read Documentation**: `docs/INDEX.md`

## 🤖 Workflow Execution

### Execute a Workflow (Example)
```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=<username>&password=<password>" \
  -s | jq -r '.access_token')

# List workflows
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8090/api/v1/workflow/users/<username>/workflows | jq

# Execute workflow (fill your variables)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "<username>",
    "nodes": [...], # Retrieve via GET /workflow/workflows/{workflow_id}
    "edges": [...],
    "start_node": "node_start",
    "global_variables": {
      "thesis_topic": "Your thesis topic here",
      "thesis_language": "fr",
      "thesis_degree": "PhD",
      "thesis_format": "standard",
      "discipline_hint": "Science",
      "granularity_target": 3,
      "target_length_pages": 250,
      "citation_style": "APA",
      "min_sources_per_subsection": 3,
      "min_sources_per_chapter": 12,
      "requirements": {},
      "seed_axes_json": {},
      "kb_map": {},
      "macro_outline": {},
      "micro_outline": {},
      "exports": {}
    }
  }' \
  http://localhost:8090/api/v1/workflow/execute | jq

# Monitor progress via SSE
curl -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/event-stream" \
  http://localhost:8090/api/v1/sse/workflow/<username>/{task_id}

# Check task status in Redis
docker exec layra-backend redis-cli get "workflow:{task_id}:state"
```

### Example Python Script
See `test_execute.py` for a complete example.

## 🆘 Support

- **Logs**: `./scripts/compose-clean logs -f`
- **Status**: `./scripts/compose-clean ps`
- **Health**: `curl http://localhost:8090/api/v1/health/check`

---

**Deployment Time**: ~5-10 minutes (first run)
**Disk Space**: ~100GB recommended
**GPU Memory**: 16GB+ recommended
**RAM**: 32GB recommended

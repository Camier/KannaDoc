# Layra Solo Thesis Deployment - Quick Start Guide

**Version:** 2.0.0 (Post-LiteLLM Removal)  
**Last Updated:** 2026-01-25

> ⚠️ **Important:** This guide reflects recent architecture changes. See [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) if upgrading from v1.x

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

# Copy example env (if starting fresh)
cp .env.example .env

# Edit configuration
nano .env
```

**Required Configuration:**

**A. LLM Provider API Keys** (NEW in v2.0)
```bash
# Add your provider API keys
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...

# Default provider for new users
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini
```

**Get API keys:**
- OpenAI: https://platform.openai.com/api-keys
- DeepSeek: https://platform.deepseek.com/api_keys

**B. Critical Passwords to Change:**
- `REDIS_PASSWORD` - Redis cache
- `MONGODB_ROOT_PASSWORD` - MongoDB
- `MYSQL_PASSWORD` - MySQL database
- `MINIO_SECRET_KEY` - Object storage
- `NEO4J_PASSWORD` - Neo4j (if enabled)

### Step 2: Deploy

```bash
# Run deployment script
./scripts/deploy-thesis.sh
```

**Expected timeline:**
- First run: 5-10 minutes (downloading 15GB models)
- Subsequent runs: 1-2 minutes

### Step 3: Access

```bash
# Layra Application
URL: http://localhost:8090
Username: thesis
Password: thesis_deploy_b20f1508a2a983f6 (Default - Change immediately!)

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
./scripts/deploy-thesis.sh
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
## 🔍 Deployment Audit & Verification

### Quick Health Check
```bash
# Verify all services are running
docker compose -f docker-compose.thesis.yml ps

# Check backend API health
curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/v1/health/check
# Should return: 200

# Verify Neo4j accessibility
curl -s http://localhost:7474 | grep -q "Neo4j" && echo "Neo4j OK"
```

### Service Status Verification
```bash
# Check healthy containers
docker ps --filter "health=healthy" --format "table {{.Names}}\t{{.Status}}"

# Expected services (all healthy):
# - layra-backend, layra-mysql, layra-redis, layra-mongodb
# - layra-milvus-standalone, layra-model-server, layra-neo4j
# - layra-minio, layra-unoserver, layra-kafka
```

### Credential Verification
```bash
# Extract credentials from backend container
docker exec layra-backend env | grep -E '(SIMPLE|NEO4J|MINIO|MYSQL|MONGODB|REDIS)' | grep -v PATH

# Verify application login
curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"thesis","password":"YOUR_PASSWORD"}' \
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
docker compose -f docker-compose.thesis.yml logs --tail=20 backend

# Check for Kafka connectivity issues
docker compose -f docker-compose.thesis.yml logs backend | grep -i kafka | tail -10

# Monitor real-time logs
docker compose -f docker-compose.thesis.yml logs -f --tail=50
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
./scripts/deploy-thesis.sh
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

### Deploy Thesis Workflow Blueprint

Once the system is running, you can deploy the pre-configured thesis workflow blueprint:

```bash
# Set the thesis user password (default: thesis_deploy_b20f1508a2a983f6)
export THESIS_PASSWORD=thesis_deploy_b20f1508a2a983f6

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
# Collection: colqwenthesis_34f1ab7f_5fbe_4a7a_bf73_6561f8ce1dd7
# Row count: 126144 (or similar)
```

**Important Note about Milvus Access:**
- Milvus port 19530 is **NOT exposed to host** for security reasons
- Services access Milvus internally via `milvus-standalone:19530`
- Diagnostic scripts like `check_milvus_schema.py` must run **inside containers** (script has been copied to `/app/`):
  ```bash
  docker exec layra-backend python3 /app/check_milvus_schema.py
  ```
  For quick verification:
  ```bash
  docker exec layra-backend python3 -c "from pymilvus import MilvusClient; client = MilvusClient('http://milvus-standalone:19530'); print('Collections:', client.list_collections())"
  ```

**Current Deployment Verification (2026-01-22):**
- ✅ 29 PDFs ingested into knowledge base (ethnopharmacology focus)
- ✅ 180,208 vector embeddings stored in Milvus collection (as of 2026-01-22)
- ✅ GPU embeddings working (model-server processing ~25s per batch)
- ✅ Neo4j accessible at http://localhost:7474
- ✅ Frontend accessible at http://localhost:8090 (user: `thesis`)
- ✅ Workflow deployed: "Minutieux" thesis blueprint

### Verify Deployed Workflow

Check that the thesis workflow blueprint is properly deployed:

```bash
# List workflows for thesis user
curl -s -X GET http://localhost:8090/api/v1/workflow/users/thesis/workflows \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8090/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=thesis&password=thesis_deploy_b20f1508a2a983f6" | jq -r '.access_token')" | jq .

# Expected output includes workflow ID: thesis_74a550b6-1746-4e4f-b9c0-881ac8717341
```

### Test RAG Query via API

```bash
# Create a conversation (prerequisite for chat)
curl -s -X POST http://localhost:8090/api/v1/chat/conversations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test_conv_1",
    "username": "thesis",
    "conversation_name": "Test Conversation",
    "chat_model_config": {
      "selected_model": "local_colqwen",
      "knowledge_bases": ["thesis_34f1ab7f-5fbe-4a7a-bf73-6561f8ce1dd7"]
    }
  }'
```

**Workflow Location**: `workflows/thesis_blueprint_minutieux/` - Contains code nodes and prompts for thesis automation.

---

## 📚 Next Steps

1. **API Documentation**: http://localhost:8090/api/docs (Swagger UI)
2. **Create First Workflow**: http://localhost:8090/work-flow
3. **Upload Documents**: http://localhost:8090/knowledge-base
4. **Explore Neo4j**: http://localhost:7474
5. **Read Documentation**: `docs/NEO4J_INTEGRATION.md`

## 🤖 Workflow Execution

### Execute Thesis Blueprint
```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=thesis&password=thesis_deploy_b20f1508a2a983f6" \
  -s | jq -r '.access_token')

# List workflows
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8090/api/v1/workflow/users/thesis/workflows | jq

# Execute workflow (update thesis_topic)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "thesis",
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
  http://localhost:8090/api/v1/sse/workflow/thesis/{task_id}

# Check task status in Redis
docker exec layra-backend redis-cli get "workflow:{task_id}:state"
```

### Example Python Script
See `test_execute.py` for a complete example.

### Current Workflow Status
- **Workflow ID**: `thesis_74a550b6-1746-4e4f-b9c0-881ac8717341`
- **Task ID**: `a12ae5c9-f051-4c2e-b26a-39d5ab6cbe7d` (executing)
- **Knowledge Base**: `thesis_34f1ab7f-5fbe-4a7a-bf73-6561f8ce1dd7` (26 PDFs)
- **Milvus Collection**: `colqwenthesis_34f1ab7f_5fbe_4a7a_bf73_6561f8ce1dd7` (180k embeddings)

## 🆘 Support

- **Logs**: `docker compose -f docker-compose.thesis.yml logs -f`
- **Status**: `docker compose -f docker-compose.thesis.yml ps`
- **Health**: `curl http://localhost:8090/api/v1/health/check`

---

**Deployment Time**: ~5-10 minutes (first run)
**Disk Space**: ~100GB recommended
**GPU Memory**: 16GB+ recommended
**RAM**: 32GB recommended

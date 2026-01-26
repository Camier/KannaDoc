# LAYRA Quick Reference Card

> **One-page reference for common tasks**  
> **Version:** 2.0.0  
> **Last Updated:** 2026-01-25

---

## 🚀 Access

**URL:** http://localhost:8090  
**User:** `thesis`  
**Password:** `thesis_deploy_b20f1508a2a983f6`  
**API Key:** `thesis-key-2412d62f0b22dfd6c6c4b70f11e1b53b`

---

## 🐳 Docker Commands

### Start System
```bash
cd /LAB/@thesis/layra
docker-compose -f deploy/docker-compose.thesis.yml --env-file .env up -d
```

### Stop System
```bash
docker-compose -f deploy/docker-compose.thesis.yml --env-file .env down
```

### View Logs
```bash
docker logs layra-backend --tail 50 -f
docker logs layra-milvus-standalone --tail 50
```

### Container Status
```bash
docker ps --filter "name=layra" --format "table {{.Names}}\t{{.Status}}"
```

### Health Check
```bash
curl http://localhost:8090/api/v1/health/check
```

---

## 🗄️ Services

| Service | Port | Purpose |
|---------|------|---------|
| **Nginx** | 8090 | Web access |
| **Backend** | 8000 (internal) | API |
| **Frontend** | 3000 (internal) | UI |
| **MySQL** | 3306 (internal) | Auth DB |
| **MongoDB** | 27017 (internal) | Chat DB |
| **Redis** | 6379 (internal) | Cache |
| **Kafka** | 9094 (internal) | Queue |
| **MinIO** | 9000 (internal) | Files |
| **Milvus** | 19530 (internal) | Vectors |

**Total:** 13 containers (12 running + 1 init)

---

## 🔑 Environment Variables

**Critical Settings (`.env`):**

```bash
# Server
SERVER_IP=http://localhost:8090



# LLM Providers (NEW in v2.0)
OPENAI_API_KEY=sk-proj-...
DEEPSEEK_API_KEY=sk-...
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o-mini

# Database
DB_URL=mysql+asyncmy://thesis:${MYSQL_PASSWORD}@mysql:3306/layra_db
MONGODB_URL=mongodb:27017
REDIS_URL=redis:6379

# Storage
MINIO_URL=http://minio:9000
MILVUS_URI=http://milvus-standalone:19530

# Messaging
KAFKA_BROKER_URL=kafka:9094
```

---

## 🛠️ Common Tasks

### Re-ingest Documents
```bash
docker exec -it layra-backend python3 scripts/ingest_sync.py
```

### Create User
```bash
docker exec -it layra-backend python3 scripts/change_credentials.py
```

### Database Migration
```bash
docker exec -it layra-backend alembic upgrade head
```

### Clean Milvus (Reset Vectors)
```bash
docker-compose -f deploy/docker-compose.thesis.yml down
docker volume rm layra_milvus_data layra_milvus_etcd
docker volume create layra_milvus_data
docker volume create layra_milvus_etcd
docker-compose -f deploy/docker-compose.thesis.yml --env-file .env up -d
```

### View Backend Config
```bash
docker exec layra-backend env | grep -E "DB_|REDIS_|MONGO|MINIO|KAFKA|MILVUS"
```

---

## 📊 Resource Usage

| Component | RAM | Notes |
|-----------|-----|-------|
| Backend | 834MB | Main app |
| MySQL | 459MB | Database |
| Kafka | 339MB | Queue |
| Milvus | 139MB | Vectors |
| Others | ~500MB | Combined |
| **Total** | **~2.3GB** | Idle state |

---

## 🐛 Quick Fixes

### Milvus Won't Start
**Symptom:** `panic: dirty recovery info`
```bash
docker-compose down
docker volume rm layra_milvus_data layra_milvus_etcd
docker volume create layra_milvus_data layra_milvus_etcd
docker-compose up -d
```

### Backend Connection Error
```bash
# Check backend logs
docker logs layra-backend --tail 50

# Restart backend
docker restart layra-backend
```

### Frontend Not Loading
```bash
# Check nginx
docker logs layra-nginx

# Check frontend build
docker logs layra-frontend
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[ssot/stack.md](stack.md)** | ⭐ **Primary Reference** |
| **[START_HERE.md](../START_HERE.md)** | Quick onboarding |
| **[THESIS_QUICKSTART.md](../THESIS_QUICKSTART.md)** | Deployment guide |
| **[ANTI_COMPLEXITY.md](../ANTI_COMPLEXITY.md)** | Complexity prevention |
| **[CHANGES_20260125.md](../CHANGES_20260125.md)** | v2.0.0 changelog |

---

## 🔍 System Info

**Version:** 2.0.0  
**Mode:** Thesis (Solo)  
**Containers:** 13  
**Networks:** 1 (deploy_layra-net)  
**LLM:** Direct provider APIs  
**Embedding:** Local ColQwen (if GPU available)

---

## 📞 Emergency

**System broken?**
1. Check logs: `docker logs layra-backend --tail 100`
2. Check health: `curl localhost:8090/api/v1/health/check`
3. Full restart: `docker-compose down && docker-compose up -d`
4. Consult: [CONSOLIDATED_REPORT.md](../CONSOLIDATED_REPORT.md)

**Data lost?**
- Volumes persist through restarts
- Check: `docker volume ls | grep layra`
- Backup `.env` and MySQL/MinIO volumes

---

**Last Updated:** 2026-01-25  
**For detailed info:** See [stack.md](stack.md)

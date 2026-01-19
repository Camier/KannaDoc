# Stack SSOT

> **Single Source of Truth** for the LAYRA Technology Stack.
> Last Updated: 2026-01-18

---

## 1. Core Services & Architecture

| Service | Type | Tech Stack | Port (Internal/External) | Purpose |
|---------|------|------------|--------------------------|---------|
| **Backend** | API | Python 3.12, FastAPI | 8000 | Main business logic, Auth, Workflow Engine |
| **Frontend** | UI | Next.js 15, React 19 | 3000 | User Interface, Web Chat |
| **Model Server** | ML | Python, PyTorch | 8005 | LLM Inference (ColBERT), Visual RAG |
| **Unoserver** | Tool | LibreOffice, Python | 2003+ | Document Conversion (PDF/Office) |
| **Sandbox** | Exec | Python 3.12 (Isolated) | N/A | Secure Code Execution Environment |

## 2. Infrastructure & Data

| Component | Technology | Version | Usage |
|-----------|------------|---------|-------|
| **Vector DB** | Milvus | v2.5.6 | Visual Embeddings storage |
| **Relational DB** | MySQL | 9.0.1 | User data, Metadata, Auth |
| **NoSQL DB** | MongoDB | 7.0.12 | Chat history, Workflow state |
| **Cache/Queue** | Redis | 7.2.5 | Task queue, Locks, Caching |
| **Event Bus** | Kafka | 3.8.0 | Async task decoupling |
| **Object Store** | MinIO | RELEASE.2024-10 | File storage (Knowledge Base) |
| **Coordination** | Etcd | v3.5.18 | Service discovery for Milvus |
| **Proxy** | Nginx | Alpine | 8090 | Reverse proxy, Static assets |

## 3. Key Dependencies

### Backend (Python)
- **Framework:** `fastapi[all]==0.115.11`
- **ORM:** `sqlalchemy[asyncio]==2.0.39`
- **Async DB:** `asyncmy==0.2.10` (MySQL), `motor==3.7.0` (Mongo)
- **ML/AI:** `pymilvus==2.5.6`, `openai==1.66.3`, `pillow==11.1.0`
- **Utils:** `pydantic==2.10.6`, `alembic==1.15.1`

### Frontend (TypeScript)
- **Framework:** `next==15.2.4`
- **UI:** `tailwindcss==4.1.2`, `@xyflow/react==12.6.0` (Nodes)
- **State:** `zustand==4.5.5`
- **Markdown:** `react-markdown==10.1.0`, `katex==0.16.21`

## 4. Environment & Configuration

- **Orchestration:** Docker Compose v2 (`layra-net` bridge network)
- **Configuration:** `pydantic_settings` reading `.env` (with `.env.example` baseline)
- **Volumes:**
  - `layra_sandbox_volume`: Shared between Backend and Sandbox
  - `model_weights`: Shared between Init and Model Server
  - Persistent data volumes for all DBs (mysql, mongo, redis, minio, milvus, kafka)

## 5. Development & Deployment

- **Linting:** `ruff` (Python), `eslint` (TS)
- **Testing:** `pytest` (Backend integration/unit)
- **Build:** Multi-stage Docker builds (Node/Python)
- **Migration:** Alembic (SQL), Custom Scripts (Password Hash)

---

**Policy:** Any architectural change (adding a service, changing a major version, switching ports) MUST be reflected here first.

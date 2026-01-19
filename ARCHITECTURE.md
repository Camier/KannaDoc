# 🏗️ LAYRA System Architecture

This document visualizes the "Visual-Native" architecture of LAYRA as deployed on this system, optimized for local GPU acceleration.

## 📊 Component Diagram

```ascii
                                  🌐 USER (Browser)
                                         |
                                         v
                              +----------------------+
                              |     NGINX (8090)     |  <-- Entry Point
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              |   BACKEND (FastAPI)  |  <-- Orchestrator
                              +----------+-----------+
                               /    |    |    |    \
                              /     |    |    |     \
        (Async Tasks)        /      |    |    |      \      (Hot Data/Cache)
  +-----------------------+ v       |    |    |       v +------------------+
  | KAFKA (Task Queue)    |         |    |    |         | REDIS            |
  | + Init & Partitions   |<--------+    |    +-------->| + Token/Locks    |
  +-----------------------+              |              +------------------+
                                         |
   +-------------------------------------+-----------------------------------+
   |                       PROCESSING LAYER (GPU/CPU)                        |
   |                                                                         |
   |  +---------------------+       +-------------------------------------+
   |  |      UNOSERVER      |       |           MODEL SERVER              |
   |  | (LibreOffice/Uno)   |       |         (FastAPI + Torch)           |
   |  +----------+----------+       +------------------+------------------+
   |             ^                                     ^                     |
   |             |                                     |                     |
   |    [1. Convert Docs]                     [2. Visual Embedding]          |
   |      PDF/Office ->                       Images -> Vectors              |
   |        Images                               (ColQwen2.5)                |
   |                                                   ^                     |
   |                                                   |                     |
   |                                          [ 🚀 GPU RTX 3090 ]            |
   +-------------------------------------------------------------------------+
                                         |
                                         v
   +-------------------------------------+-----------------------------------+
   |                          STORAGE LAYER                                  |
   +-------------------+  +-------------------+  +------------------------+  |
   |      MILVUS       |  |      MINIO        |  |    DATABASES           |  |
   |   (Vector DB)     |  | (Object Storage)  |  |                        |  |
   |                   |  |                   |  | [MySQL]   Auth/Users   |  |
   | + Vectors (Etcd)  |  | + Raw Files (PDF) |  | [MongoDB] Chat History |
   | + Metadata        |  | + Page Images     |  |           Workflows    |
   +-------------------+  +-------------------+  +------------------------+
   +-------------------------------------------------------------------------+
```

## 🧠 Data Flow Details

### 1. Ingestion (The "Eyes")
*   **Storage**: Documents are stored in **MinIO** buckets.
*   **Conversion**: **Unoserver** uses LibreOffice to render PDFs and Office files into high-quality images.
*   **Embedding**: **Model Server** uses **ColQwen2.5** running on the **RTX 3090** to transform visual layouts into multi-vector embeddings.
*   **Indexing**: These visual vectors are stored in **Milvus** for extremely fast spatial retrieval.

### 2. Retrieval (The "Brain")
*   **Query Path**: User text queries are converted to vectors by the Model Server.
*   **Visual Match**: Milvus finds the specific *image patches* or *pages* that look like the information requested (preserving tables, charts, and layout).
*   **Response**: The Backend merges this visual context with LLM reasoning.

### 3. Orchestration (The "Nerves")
*   **Kafka**: Ensures background tasks (like heavy document indexing) don't block the UI.
*   **Redis**: Handles real-time locking and user session tokens.
*   **MySQL/Mongo**: Separate concerns between user management (SQL) and complex workflow/chat history (NoSQL).

## 🔐 Security & API Layer

### API Documentation
*   **Swagger UI**: Interactive API explorer available at `/api/docs`
*   **ReDoc**: Alternative documentation at `/api/redoc`
*   **OpenAPI Spec**: Machine-readable spec at `/api/v1/openapi.json`

### Security Features
*   **CORS Protection**: Configurable allowed origins via `ALLOWED_ORIGINS` environment variable
*   **Credential Security**: `.env` file excluded from git tracking to prevent accidental credential exposure
*   **Production Ready**: Disables credential-based authentication when using wildcard CORS origins (`*`) for security

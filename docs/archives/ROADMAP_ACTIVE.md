# 🛣️ Actionable Roadmap: LAYRA Refactoring & Optimization

This roadmap focuses on immediate complexity reduction and structural hygiene, paving the way for the Repository Pattern and Frontend decomposition.

## 🟢 Phase 0: Hygiene & Consolidation (Completed)

### 1. 🧹 Codebase Hygiene (The "Mongo" Cleanup)
- [x] **Verify & Prune `mongo.py`**: Reduced from 1,600+ to ~110 lines.
- [x] **Delete Dead Files**: Cleaned up reports, one-off scripts, and backups.
- [x] **Remove Dead Directories**: Cleaned up empty or redundant directories.

### 2. 🐳 Infrastructure Consolidation
- [x] **Merge Docker Compose**: Single `docker-compose.yml` with unified GPU settings.
- [x] **Cleanup**: Removed redundant deploy files.

---

## 🟡 Phase 1: Architecture & Patterns (Completed)

### 3. 🏗️ Repository Pattern Implementation
- [x] **Manager**: Created `RepositoryManager` for dependency injection.
- [x] **Migration**: Migrated ALL API endpoints and core services.
- [x] **Deduplication**: Added content-hash based deduplication for file uploads.

---

## 🔵 Phase 2: Frontend Decomposition (Completed)

### 4. ⚛️ Component Decomposition
- [x] **FlowEditor**: Verified modular structure under `FlowEditor/` sub-components.

---

## 🟠 Phase 3: Data & Embeddings (Current Focus)

### 5. 📊 Advanced Data Management
- [ ] **KB Search Preview**: Implement a dedicated UI/API to test retrieval quality.
- [ ] **Embedding Refresh**: Tooling to migrate embeddings between models.
- [ ] **Deduplication UI**: Visual indicator for skipped duplicates in the UI.

---

## 🚀 Next Step
Move to **Phase 3: Data & Embeddings**.
1. Implement a **Knowledge Base Search Preview** feature to verify embedding quality.
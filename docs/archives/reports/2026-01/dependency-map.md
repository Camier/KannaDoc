# MongoDB → Repository Migration Dependency Map

Generated during Phase 1 of repository migration

---

## Summary Statistics

- **Total files to migrate**: 11
- **Total MongoDB method calls**: ~70
- **MongoDB class instances**: ~30 endpoint dependencies

---

## File-by-File Migration Map

### 1. backend/app/api/endpoints/chat.py

**Current Import**: `from app.db.mongo import MongoDB, get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.create_conversation()` | `ConversationRepository.create_conversation()` |
| `db.update_conversation_name()` | `ConversationRepository.update_conversation_name()` |
| `db.update_conversation_model_config()` | `ConversationRepository.update_conversation_model_config()` |
| `db.get_conversation()` | `ConversationRepository.get_conversation()` |
| `db.get_conversations_by_user()` | `ConversationRepository.get_conversations_by_user()` |
| `db.delete_conversation()` | `ConversationRepository.delete_conversation()` |
| `db.delete_all_conversation()` | `ConversationRepository.delete_all_conversation()` |
| `db.create_knowledge_base()` | `KnowledgeBaseRepository.create_knowledge_base()` |

**Dependency Injection Changes**:
- Before: `db: MongoDB = Depends(get_mongo)`
- After: `conv_repo: ConversationRepository = Depends(get_conversation_repo), kb_repo: KnowledgeBaseRepository = Depends(get_kb_repo)`

---

### 2. backend/app/api/endpoints/base.py

**Current Import**: `from app.db.mongo import MongoDB, get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.get_knowledge_bases_by_user()` | `KnowledgeBaseRepository.get_knowledge_bases_by_user()` |
| `db.db.files.count_documents()` | `FileRepository.count_files_by_kb()` *(NEW)* |
| `db.create_knowledge_base()` | `KnowledgeBaseRepository.create_knowledge_base()` |
| `db.update_knowledge_base_name()` | `KnowledgeBaseRepository.update_knowledge_base_name()` |
| `db.bulk_delete_files_from_knowledge()` | `FileRepository.delete_files_bulk()` |
| `db.delete_file_from_knowledge_base()` | `KnowledgeBaseRepository.delete_file_from_knowledge_base()` |
| `db.delete_knowledge_base()` | `KnowledgeBaseRepository.delete_knowledge_base()` |
| `db.get_all_knowledge_bases_by_user()` | `KnowledgeBaseRepository.get_all_knowledge_bases_by_user()` |
| `db.get_conversations_by_user()` | `ConversationRepository.get_conversations_by_user()` |
| `db.get_chatflows_by_user()` | `ChatflowRepository.get_chatflows_by_user()` |
| `db.delete_knowledge_bases_bulk()` | `KnowledgeBaseRepository.delete_knowledge_bases_bulk()` |
| `db.get_kb_files_with_pagination()` | `KnowledgeBaseRepository.get_kb_files_with_pagination()` |
| `db.get_user_files_with_pagination()` | `KnowledgeBaseRepository.get_user_files_with_pagination()` |
| `db.get_knowledge_base_by_id()` | `KnowledgeBaseRepository.get_knowledge_base_by_id()` |

**Dependency Injection Changes**:
- Before: `db: MongoDB = Depends(get_mongo)`
- After: Multiple repositories based on endpoint needs

---

### 3. backend/app/api/endpoints/auth.py

**Current Import**: `from app.db.mongo import MongoDB, get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| Uses SQLAlchemy `db` for User operations | No change needed (SQL) |

**Note**: This file uses SQLAlchemy for User model, not MongoDB. Only the import needs updating if used elsewhere.

---

### 4. backend/app/api/endpoints/chatflow.py

**Current Import**: `from app.db.mongo import MongoDB, get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.create_chatflow()` | `ChatflowRepository.create_chatflow()` |
| `db.update_chatflow_name()` | `ChatflowRepository.update_chatflow_name()` |
| `db.get_chatflow()` | `ChatflowRepository.get_chatflow()` |
| `db.get_files_by_knowledge_base_id()` | `KnowledgeBaseRepository.get_files_by_knowledge_base_id()` |
| `db.get_chatflows_by_workflow_id()` | `ChatflowRepository.get_chatflows_by_workflow_id()` |
| `db.delete_chatflow()` | `ChatflowRepository.delete_chatflow()` |
| `db.delete_workflow_all_chatflow()` | `ChatflowRepository.delete_workflow_all_chatflow()` |

---

### 5. backend/app/api/endpoints/config.py

**Current Import**: `from app.db.mongo import get_mongo, MongoDB`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.add_model_config()` | `ModelConfigRepository.create_model_config()` |
| `db.delete_model_config()` | `ModelConfigRepository.delete_model_config()` |
| `db.update_model_config()` | `ModelConfigRepository.update_model_config()` |
| `db.update_selected_model()` | `ModelConfigRepository.update_selected_model()` |
| `db.get_selected_model_config()` | `ModelConfigRepository.get_selected_model_config()` |
| `db.get_all_models_config()` | `ModelConfigRepository.get_all_models_config()` |

---

### 6. backend/app/api/endpoints/workflow.py

**Current Import**: (not scanned, but expected)

| Method Call | Target Repository |
|-------------|-------------------|
| `db.create_workflow()` | `WorkflowRepository.create_workflow()` |
| `db.update_workflow()` | `WorkflowRepository.update_workflow()` |
| `db.get_workflow()` | `WorkflowRepository.get_workflow()` |
| `db.get_workflows_by_user()` | `WorkflowRepository.get_workflows_by_user()` |
| `db.delete_workflow()` | `WorkflowRepository.delete_workflow()` |

---

### 7. backend/app/rag/llm_service.py

**Current Import**: `from app.db.mongo import get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.get_conversation_model_config()` | `ConversationRepository.get_conversation_model_config()` |
| `db.get_file_and_image_info()` | `FileRepository.get_file_and_image_info()` |
| `db.add_turn()` | `ConversationRepository.add_turn()` |

**Changes**:
- Before: `db = await get_mongo()`
- After: `conv_repo = await get_conversation_repo(), file_repo = await get_file_repo()`

---

### 8. backend/app/rag/utils.py

**Current Import**: `from app.db.mongo import get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.get_knowledge_base_by_id()` | `KnowledgeBaseRepository.get_knowledge_base_by_id()` |
| `db.create_files()` | `FileRepository.create_files()` |
| `db.knowledge_base_add_file()` | `KnowledgeBaseRepository.knowledge_base_add_file()` |
| `db.add_images()` | `FileRepository.add_images()` |
| `db.delete_file_from_knowledge_base()` | `KnowledgeBaseRepository.delete_file_from_knowledge_base()` |
| `db.delete_files_bulk()` | `FileRepository.delete_files_bulk()` |

---

### 9. backend/app/rag/mesage.py

**Current Import**: `from app.db.mongo import get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.get_chatflow()` | `ChatflowRepository.get_chatflow()` |
| `db.get_conversation()` | `ConversationRepository.get_conversation()` |

---

### 10. backend/app/workflow/llm_service.py

**Current Import**: `from app.db.mongo import get_mongo`

| Method Call | Target Repository |
|-------------|-------------------|
| `db.get_file_and_image_info()` | `FileRepository.get_file_and_image_info()` |
| `db.chatflow_add_turn()` | `ChatflowRepository.chatflow_add_turn()` |

---

### 11. backend/app/main.py

**Current Import**: (likely contains MongoDB initialization)

**Changes**: Update any MongoDB initialization to use RepositoryFactory if needed

---

## Missing Methods to Add

Based on the dependency map, these methods are referenced but may not exist in repositories:

### FileRepository
- [ ] `count_files_by_kb(knowledge_base_id: str) -> int` - Used in base.py:48

### KnowledgeBaseRepository
- [ ] `get_files_by_knowledge_base_id(knowledge_base_id: str) -> List[Dict]` - Used in chatflow.py:61

### ChatflowRepository
- [ ] `get_chatflows_by_workflow_id(workflow_id: str) -> List[Dict]` - Used in chatflow.py:98
- [ ] `delete_workflow_all_chatflow(workflow_id: str) -> Dict` - Used in chatflow.py:138

---

## Repository Factory Functions Needed

Create these dependency injection functions in `backend/app/db/repositories/__init__.py`:

```python
async def get_conversation_repo() -> ConversationRepository:
    from app.db.mongo import get_mongo
    mongo = await get_mongo()
    return ConversationRepository(mongo.db)

async def get_kb_repo() -> KnowledgeBaseRepository:
    from app.db.mongo import get_mongo
    mongo = await get_mongo()
    return KnowledgeBaseRepository(mongo.db)

async def get_file_repo() -> FileRepository:
    from app.db.mongo import get_mongo
    mongo = await get_mongo()
    return FileRepository(mongo.db)

async def get_chatflow_repo() -> ChatflowRepository:
    from app.db.mongo import get_mongo
    mongo = await get_mongo()
    return ChatflowRepository(mongo.db)

async def get_workflow_repo() -> WorkflowRepository:
    from app.db.mongo import get_mongo
    mongo = await get_mongo()
    return WorkflowRepository(mongo.db)

async def get_model_config_repo() -> ModelConfigRepository:
    from app.db.mongo import get_mongo
    mongo = await get_mongo()
    return ModelConfigRepository(mongo.db)
```

---

## Priority Order for Migration

1. **Phase 3.1**: Add missing methods to repositories (gap analysis)
2. **Phase 3.2**: Create dependency injection functions
3. **Phase 3.3**: Migrate low-risk endpoints first (config.py, chatflow.py)
4. **Phase 3.4**: Migrate medium-risk endpoints (auth.py, workflow.py)
5. **Phase 3.5**: Migrate high-risk endpoints (chat.py, base.py)
6. **Phase 4**: Migrate RAG and workflow modules

---

## Risk Assessment by File

| File | Risk Level | Reason |
|------|------------|--------|
| config.py | LOW | Simple CRUD operations |
| chatflow.py | LOW-MED | Moderate complexity |
| auth.py | MED | User authentication, uses SQL |
| workflow.py | MED | Core workflow logic |
| chat.py | HIGH | Core conversation feature |
| base.py | HIGH | Many methods, complex logic |
| llm_service.py | HIGH | Core RAG functionality |
| utils.py | HIGH | File handling logic |
| mesage.py | MED | Message retrieval |
| workflow/llm_service.py | HIGH | Workflow RAG |

---

## Verification Checklist

After migration, verify:
- [ ] No `from app.db.mongo import MongoDB` in production code
- [ ] No `db: MongoDB = Depends(get_mongo)` in endpoints
- [ ] All repositories have dependency injection functions
- [ ] All tests pass with new repository pattern
- [ ] Performance benchmarks match or improve

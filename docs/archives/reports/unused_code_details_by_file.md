# DETAILED UNUSED CODE BY FILE
## Specific Line Numbers and Code References

This document provides the exact location of each unused item for precise cleanup.

---

## BACKEND PYTHON - DETAILED FINDINGS

### CRITICAL: Entire Files to Delete

#### 1. `/backend/app/db/repositories/BEFORE_AFTER_CHAT.py`
- **Lines:** 1-369 (entire file)
- **Type:** Documentation/Example file
- **Safe to Delete:** YES
- **Action:** Delete entire file
```bash
rm /LAB/@thesis/layra/backend/app/db/repositories/BEFORE_AFTER_CHAT.py
```

---

### HIGH: Files with 10+ Unused Items

#### 2. `/backend/app/db/repositories/__init__.py`
**Unused Imports (20 items):**
```
Line 36: from .base_repository import BaseRepository
Line 37: from .model_config_repository import ModelConfigRepository
Line 38: from .conversation_repository import ConversationRepository
Line 39: from .knowledge_base_repository import KnowledgeBaseRepository
Line 40: from .file_repository import FileRepository
Line 41: from .node_repository import NodeRepository
Line 42: from .workflow_repository import WorkflowRepository
Line 43: from .chatflow_repository import ChatflowRepository
Line 44: def get_base_repo
Line 45: def get_model_config_repo
Line 46: def get_conversation_repo
Line 47: def get_knowledge_base_repo
Line 48: def get_file_repo
Line 49: def get_node_repo
Line 50: def get_workflow_repo
Line 51: def get_chatflow_repo
```
**Recommendation:** Review - these may be exported for external use

#### 3. `/backend/app/workflow/workflow_engine_new.py`
**Unused Imports (23 items):**
```
Line 2: import asyncio
Line 3: import json
Line 4: import re
Line 6: import uuid
Line 7: import docker
Line 9: from dotenv import load_dotenv
Line 11: from fastapi import APIRouter
Line 12: from fastapi import Depends
Line 13: from fastapi import HTTPException
Line 14: from pydantic import BaseModel
Line 15: from pydantic import Field
Line 16: from pydantic import validator
Line 17: from app.db.mongo import get_mongo
Line 18: from app.db.redis import get_redis
Line 19: from app.workflow.llm_service import ChatService
Line 20: from app.workflow.components.checkpoint_manager import WorkflowCheckpointManager
Line 21: from app.workflow.graph import WorkflowGraph
Line 22: from app.workflow.sandbox import CodeSandbox
Line 23: from app.workflow.mcp_tools import mcp_tools
Line 24: from app.workflow.utils import replace_template
Line 25: from app.workflow.utils import find_outermost_braces
Line 26: from app.core.logging import logger
```
**Recommendation:** Review - this appears to be a new version of workflow engine

---

### MEDIUM: API Endpoints with Unused Functions

#### 4. `/backend/app/api/endpoints/base.py`
**Unused Functions (13):**
```
Function: re_name (pattern for validation)
Function: download_file
Function: delete_file
Function: delete_knowledge_base
Function: create_knowledge_base
Function: rename_knowledge_base
Function: get_all_knowledge_bases
Function: get_knowledge_base_files
Function: get_knowledge_base_file
Function: upload_file
Function: re_knowledge_base
Function: re_username
Function: re_base_name
```
**Note:** These may be endpoint handlers not registered to router

#### 5. `/backend/app/api/endpoints/chat.py`
**Unused Functions (9):**
```
Function: re_name
Function: get_conversation
Function: delete_all_conversations_by_user
Function: get_conversations_by_user
Function: delete_conversation
Function: upload_file
Function: re_conversation_id
Function: re_username
Function: re_parent_id
```

#### 6. `/backend/app/api/endpoints/workflow.py`
**Unused Functions (12):**
```
Function: re_name
Function: execute_workflow
Function: create_workflow
Function: get_custom_nodes
Function: execute_test_code
Function: get_all_workflow_data
Function: get_workflow
Function: delete_workflow
Function: rename_workflow
Function: get_workflow_nodes
Function: re_workflow_id
Function: re_username
```

#### 7. `/backend/app/api/endpoints/config.py`
**Unused Functions (8):**
```
Function: get_all_models
Function: get_selected_model
Function: update_model_config
Function: delete_model_config
Function: add_model_config
Function: get_base_used
Function: re_model_name
Function: re_username
```

---

### MEDIUM: Database Layer

#### 8. `/backend/app/db/cache.py`
**Unused Functions (17):**
```
Function: invalidate_user_data
Function: set_search_results
Function: get_many
Function: set_kb_metadata
Function: set_model_config
Function: delete
Function: get_task
Function: set_task
Function: clear_user
Function: get_user_keys
Function: user_exists
Function: create_user
Function: health_check
Function: initialize
Function: close
Function: _serialize
Function: _deserialize
```
**Action:** Verify if replaced by Redis or other caching

#### 9. `/backend/app/db/redis.py`
**Unused Functions (7):**
```
Function: get_redis_pool
Function: get_redis_connection
Function: get_task_connection
Function: get_lock_connection
Function: get_token_connection
Function: get_chat_connection
Function: get_api_key_connection
```

#### 10. `/backend/app/db/qdrant.py`
**Unused Functions (10):**
```
Function: insert_multi_vectors
Function: check_collection
Function: load_collection
Function: delete_collection
Function: get_collection_info
Function: search
Function: delete_files
Function: health_check
Function: initialize
Function: close
```

#### 11. `/backend/app/db/vector_db.py`
**Unused Functions (9):**
```
Function: check_collection
Function: delete_collection
Function: insert
Function: delete_files
Function: health_check
Function: initialize
Function: close
Function: _convert_to_float_list
Function: _batch_insert
```

---

### MEDIUM: Utility Layer

#### 12. `/backend/app/utils/kafka_consumer.py`
**Unused Functions (10):**
```
Function: stop
Function: send_to_dlq
Function: process_file_task
Function: start
Function: consume_messages
Function: _get_task_connection
Function: _process_task
Function: _send_to_dlq
Function: _log_error
Function: close
```

#### 13. `/backend/app/utils/kafka_producer.py`
**Unused Functions (5):**
```
Function: send_workflow_task
Function: stop
Function: send_embedding_task
Function: start
Function: close
```

#### 14. `/backend/app/workflow/sandbox.py`
**Unused Functions (7):**
```
Function: commit
Function: execute
Function: get_all_images
Function: start
Function: delete_image
Function: _execute_command
Function: _cleanup
```

#### 15. `/backend/app/workflow/components/checkpoint_manager.py`
**Unused Functions (5):**
```
Function: rollback_to_checkpoint
Function: should_checkpoint
Function: load_checkpoint
Function: list_checkpoints
Function: save_checkpoint
```

#### 16. `/backend/app/workflow/components/llm_client.py`
**Unused Functions (4):**
```
Function: get_provider_timeout
Function: call_with_circuit_breaker
Function: call_with_retry
Function: retry_with_backoff
```

---

### HIGH: Unused Classes

#### 17. `/backend/app/models/conversation.py`
**Unused Classes (7):**
```
Class: ConversationSummary
Class: TurnInput
Class: UserMessage
Class: GetUserFiles
Class: ConversationCreate
Class: ConversationOutput
Class: ConversationUpdateModelConfig
Class: ConversationRenameInput
```

#### 18. `/backend/app/models/workflow.py`
**Unused Classes (8):**
```
Class: WorkflowCreate
Class: NodesInput
Class: LLMInputOnce
Class: TestFunctionCode
Class: Workflow
Class: GetTools
Class: TestConditionNode
Class: UserMessage
Class: WorkflowRenameInput
```

#### 19. `/backend/app/workflow/executors/`
**All executor classes appear unused (7 total):**
```
File: base_executor.py - Class: BaseExecutor
File: code_node_executor.py - Class: CodeNodeExecutor
File: condition_executor.py - Class: ConditionExecutor
File: http_node_executor.py - Class: HTTPNodeExecutor
File: llm_node_executor.py - Class: LLMNodeExecutor
File: quality_gate_executor.py - Class: QualityGateExecutor
File: vlm_node_executor.py - Class: VLMNodeExecutor
```

---

## FRONTEND TYPESCRIPT - DETAILED FINDINGS

### LOW: Unused Imports (47 total)

#### 20. `/frontend/src/app/[locale]/ai-chat/page.tsx`
```
Line 7: withAuth from '@/middlewares/withAuth'
```
**Note:** May be used in HOC - verify before removing

#### 21. `/frontend/src/app/[locale]/knowledge-base/page.tsx`
```
Line 16: UploadFile from '@/types/types'
Line 14: withAuth from '@/middlewares/withAuth'
```

#### 22. `/frontend/src/app/[locale]/layout.tsx`
```
Line 5: Inter from 'next/font/google'
```

#### 23. `/frontend/src/app/[locale]/sign-in/page.tsx`
```
Line ?: transferableAbortSignal from 'util'
```

#### 24. `/frontend/src/app/[locale]/work-flow/page.tsx`
```
Line ?: withAuth from '@/middlewares/withAuth'
```

#### 25. `/frontend/src/components/Workflow/FlowEditor.tsx`
```
Line ?: type Connection from '@xyflow/react'
Line ?: nodeTypesInfo from '@/types/types'
```

#### 26. `/frontend/src/components/Workflow/CustomEdge.tsx`
```
Line ?: CustomEdgeProps from '@/types/types'
```

#### 27. `/frontend/src/components/Workflow/CustomNode.tsx`
```
Line ?: CustomNodeProps from '@/types/types'
```

#### 28. `/frontend/src/stores/authStore.ts`
```
Line ?: create from 'zustand'
```
**Note:** `create` may be used but aliased

#### 29. `/frontend/src/stores/flowStore.ts`
```
Line ?: create from 'zustand'
```

#### 30. `/frontend/src/stores/WorkflowVariableStore.ts`
```
Line ?: create from 'zustand'
```

#### 31. `/frontend/src/lib/api/configApi.tsx`
```
Line ?: axios from 'axios'
```

#### 32. `/frontend/src/types/types.ts`
```
Line ?: Node from '@xyflow/react'
Line ?: Edge from '@xyflow/react'
Line ?: NodeProps from '@xyflow/react'
Line ?: EdgeProps from '@xyflow/react'
```

---

## COMMENTED CODE TO REMOVE

### 33. `/frontend/src/app/[locale]/ai-chat/page.tsx`
```
Line 354: //const response = await fetch("http://192.168.1.5:8000/api/v1/sse/chat", {
```
**Action:** Remove this commented-out fetch call

### 34. `/frontend/src/components/AiChat/KnowledgeConfigModal.tsx`
```
Line 244: //const response = await createKnowledgeBase(user.name, newBaseName);
```
**Action:** Remove this commented-out API call

### 35. `/frontend/src/components/Workflow/NodeSettings/KnowledgeConfigModal.tsx`
```
Line 248: //const response = await createKnowledgeBase(user.name, newBaseName);
```
**Action:** Remove this commented-out API call

---

## PRIORITY CLEANUP ORDER

### Safe to Remove Immediately (Phase 1)
1. **File:** `backend/app/db/repositories/BEFORE_AFTER_CHAT.py`
   - Action: Delete entire file
   - Risk: NONE

2. **Commented code** (3 locations)
   - Action: Remove commented lines
   - Risk: NONE

### Review and Test (Phase 2)
3. **Unused TypeScript imports** (47 items)
   - Action: Remove after verifying each file
   - Risk: LOW

4. **Unused Python imports** (125 items)
   - Action: Remove after running tests
   - Risk: MEDIUM

5. **Unused utility functions** (50+ functions)
   - Action: Remove after checking tests
   - Risk: MEDIUM

### Deep Review Required (Phase 3)
6. **Unused endpoint functions** (200+ functions)
   - Action: Review with team, add `# noqa: planned`
   - Risk: HIGH

7. **Unused classes** (61 classes)
   - Action: Verify not used dynamically
   - Risk: HIGH

---

## CLEANUP COMMANDS

### Remove Single Unused Import (Example)
```python
# Before
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query

# After (remove 'Query')
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
```

### Remove Single Unused Function (Example)
```python
# Before
def unused_function():
    pass

def used_function():
    pass

# After
def used_function():
    pass
```

### Batch Remove Unused Imports (Backend)
```bash
# Run after manual verification
cd /LAB/@thesis/layra/backend

# Example: Remove Query from api/endpoints/base.py
sed -i 's/from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile/from fastapi import APIRouter, Depends, HTTPException, UploadFile/g' app/api/endpoints/base.py
```

---

## VERIFICATION AFTER CLEANUP

For each file modified:

```bash
# 1. Check syntax
python -m py_compile path/to/file.py

# 2. Run tests
pytest tests/ -v

# 3. Check for references
grep -r "FunctionName" --include="*.py" .

# 4. Git diff
git diff path/to/file.py
```

---

## NOTES

1. **False Positives:** Some items may be used dynamically or in configuration files
2. **Future Use:** Some functions may be planned features (add `# noqa: planned` comments)
3. **Testing:** Always run full test suite after removing code
4. **Backup:** The cleanup script creates automatic backups
5. **Incremental:** Remove one category at a time, test between each

---

## END OF DETAILED REPORT

For summary statistics and recommendations, see:
`UNUSED_CODE_ANALYSIS_REPORT.md`

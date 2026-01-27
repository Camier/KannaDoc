# Pydantic Model Consolidation - Breaking Changes

## Summary

This document describes the breaking changes introduced by consolidating duplicate Pydantic models into a shared module.

## Date

2026-01-27

## Changes

### New File Created

- `/backend/app/models/shared.py` - Contains shared Pydantic models used across multiple domains

### Models Consolidated

#### 1. TurnOutput
**Previous locations:**
- `/backend/app/models/chatflow.py` (line 18)
- `/backend/app/models/conversation.py` (line 37)

**New location:**
- `/backend/app/models/shared.py`

**Fields:** No changes (12 identical fields)
```python
message_id: str
parent_message_id: str
user_message: dict
temp_db: str
ai_message: dict
file_used: list
user_file: list
status: str
timestamp: str
total_token: int
completion_tokens: int
prompt_tokens: int
```

#### 2. UserMessage (BREAKING CHANGE)
**Previous locations:**
- `/backend/app/models/conversation.py` (line 71) - had field `temp_db: str`
- `/backend/app/models/workflow.py` (line 74) - had field `temp_db_id: str`

**New location:**
- `/backend/app/models/shared.py`

**Standardized field name:**
```python
temp_db_id: str  # Was 'temp_db' in conversation.py, now standardized to 'temp_db_id'
```

**Rationale:** The field name `temp_db_id` is more descriptive and matches the pattern used in other parts of the codebase (e.g., `conversation_id`, `parent_id`).

## Impact Analysis

### Files Updated

#### Model Files
1. `/backend/app/models/chatflow.py` - Now imports `TurnOutput` from shared
2. `/backend/app/models/conversation.py` - Now imports `TurnOutput` and `UserMessage` from shared
3. `/backend/app/models/workflow.py` - Now imports `UserMessage` from shared

#### Usage Files (Updated for temp_db_id field change)
1. `/backend/app/api/endpoints/sse.py` - Import updated, `WorkflowMessage` alias removed
2. `/backend/app/workflow/workflow_engine.py` - Import updated
3. `/backend/app/core/llm/chat_service.py` - Updated to use `temp_db_id` consistently
4. `/backend/tests/test_rag_pipeline.py` - Test fixture updated to use `temp_db_id`

### Files Unaffected (Database Layer)

The following files continue to use `temp_db` in database operations:
- `/backend/app/db/mongo.py` - Database model uses `temp_db` (correct)
- `/backend/app/api/endpoints/chat.py` - Database operations use `temp_db` (correct)
- `/backend/app/api/endpoints/chatflow.py` - Database operations use `temp_db` (correct)
- `/backend/tests/test_repositories.py` - Test fixtures use `temp_db` (correct)

**Note:** The database field name remains `temp_db`. The Pydantic model's `temp_db_id` field is mapped to the database's `temp_db` field through the service layer.

## Migration Guide

### For API Consumers

If you're using the API endpoints that accept `UserMessage`:

**Before:**
```json
{
  "conversation_id": "conv_123",
  "parent_id": "",
  "user_message": "Hello",
  "temp_db": "kb_123"
}
```

**After:**
```json
{
  "conversation_id": "conv_123",
  "parent_id": "",
  "user_message": "Hello",
  "temp_db_id": "kb_123"
}
```

### For Frontend Code

Update all references to `temp_db` to `temp_db_id` in:
- Form submissions
- Type definitions
- API calls

### For Backend Code

**Import changes:**
```python
# Before
from app.models.conversation import UserMessage
from app.models.workflow import UserMessage as WorkflowMessage

# After
from app.models.shared import UserMessage
```

**Field access changes:**
```python
# Before
user_message.temp_db  # conversation.py version
user_message.temp_db_id  # workflow.py version

# After (standardized)
user_message.temp_db_id
```

## Testing

### Tests Updated
- `/backend/tests/test_rag_pipeline.py` - Updated to use `temp_db_id`

### Tests Unaffected
- `/backend/tests/test_repositories.py` - Uses `TurnInput` which still has `temp_db` (correct for database layer)
- `/backend/tests/test_repositories/fixtures.py` - Database fixtures use `temp_db` (correct)

## Verification Checklist

- [x] Created `/backend/app/models/shared.py` with `TurnOutput` and `UserMessage`
- [x] Updated `/backend/app/models/chatflow.py` to import `TurnOutput` from shared
- [x] Updated `/backend/app/models/conversation.py` to import both models from shared
- [x] Updated `/backend/app/models/workflow.py` to import `UserMessage` from shared
- [x] Updated `/backend/app/api/endpoints/sse.py` to use shared `UserMessage`
- [x] Updated `/backend/app/workflow/workflow_engine.py` to use shared `UserMessage`
- [x] Updated `/backend/app/core/llm/chat_service.py` to use `temp_db_id` consistently
- [x] Updated `/backend/tests/test_rag_pipeline.py` to use `temp_db_id`
- [x] Verified database layer still uses `temp_db` (correct separation of concerns)
- [x] Removed duplicate model definitions from all files
- [x] Documented breaking changes

## Rollback Plan

If issues arise, revert the changes:
1. Restore original `TurnOutput` and `UserMessage` definitions in `chatflow.py`, `conversation.py`, and `workflow.py`
2. Update imports in dependent files back to original locations
3. Revert `chat_service.py` changes to handle both `temp_db` and `temp_db_id` field names

## Benefits

1. **DRY Principle:** Single source of truth for shared models
2. **Consistency:** Standardized field names across domains
3. **Maintainability:** Changes to shared models only need to be made once
4. **Type Safety:** IDE and type checkers can better track model usage
5. **Clarity:** Clear separation between API models and database models

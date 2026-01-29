# Workflow Executors - Archived

**Date Archived:** 2026-01-28
**Reason:** Incomplete refactoring - never integrated into workflow_engine.py

## Archived Files

| File | Lines | Purpose |
|------|-------|---------|
| `base_executor.py` | 104 | Base executor class |
| `vlm_node_executor.py` | 328 | VLM node execution |
| `llm_node_executor.py` | 126 | LLM node execution |
| `code_node_executor.py` | ~100 | Code node execution |
| `http_node_executor.py` | 99 | HTTP node execution |
| `condition_executor.py` | 118 | Condition node execution |
| `quality_gate_executor.py` | 296 | Quality gate (archived separately) |
| `__init__.py` | 22 | Package exports |
| **Total** | **~1,200** | Complete executor framework |

## Why Were These Archived?

The executor pattern was an **incomplete refactoring** that was **never integrated**:

### Evidence of Non-Integration

1. **Zero imports in workflow_engine.py**: No files import from `executors/`
2. **Only self-imports**: `__init__.py` only imports within the package itself
3. **Git history**: Shows incomplete refactoring work
4. **Alternative approach used**: workflow_engine.py has inline execution logic

### Current Node Execution in workflow_engine.py

The workflow engine executes nodes directly without the executor abstraction:

```python
# Example: LLM node execution in workflow_engine.py (lines ~800+)
if node_data["type"] == "llm":
    # Direct execution without executor
    response = await llm_service.create_chat_stream(...)
```

### Why the Refactoring Was Abandoned

1. **Complexity**: Executor pattern added significant abstraction overhead
2. **Performance**: Direct execution was simpler and faster
3. **Debugging**: Direct execution is easier to debug and trace
4. **Time constraints**: Refactoring was never completed

## Architecture Comparison

### Current (Direct Execution)
```
workflow_engine.py
    ├── Node type check (if/elif/else)
    ├── Direct function call
    └── Inline error handling
```

### Abandoned (Executor Pattern)
```
workflow_engine.py
    ├── Node factory
    ├── executor_instance.execute(node_data)
    └── executor returns NodeResult
```

## Restoration

If you want to reintegrate the executor pattern:

1. **Complete the executor implementations**: All nodes must be covered
2. **Create proper factory**: Node type → executor mapping
3. **Update workflow_engine.py**: Replace inline execution with executor calls
4. **Handle state management**: Executors need access to workflow context
5. **Add comprehensive tests**: Executor pattern needs test coverage
6. **Performance testing**: Ensure no regression

Estimated effort: **2-3 weeks**

## Alternative: Remove Entirely

Given the incomplete state and lack of integration, consider:

1. **Keep archived** as reference for future refactoring
2. **Document current architecture** in `docs/architecture/`
3. **Focus on other improvements** (see remediation plan)

## References

- See `docs/plans/2026-01-28-codebase-remediation.md` for full context
- See `backend/app/workflow/workflow_engine.py` for current execution logic
- See git history for original refactoring attempt

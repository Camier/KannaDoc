# Workflow Engine Architecture

**Version:** 2.2.0 (Fault Tolerance Enhanced)
**Last Updated:** 2026-01-26

---

## Overview

The Layra Workflow Engine is a fault-tolerant, distributed execution engine for complex AI workflows. It supports long-running workflows with state persistence, error recovery, and quality-based conditional routing.

**Key Features:**
- DAG-based execution with loop support
- Circuit breaker protection for LLM calls
- Provider-specific timeouts (DeepSeek-r1: 300s, GLM: 180s)
- Automatic checkpointing with rollback capability
- Quality assessment for conditional gates
- Exponential backoff retry logic
- Memory-safe context management

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                     WorkflowEngine                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ CheckpointManager│  │QualityAssessment │                │
│  │                  │  │     Engine        │                │
│  │ • Auto-save      │  │ • Multi-dimension │                │
│  │ • Rollback       │  │   scoring         │                │
│  │ • Recovery       │  │ • Pass/fail      │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │         Circuit Breaker + Retry System            │      │
│  │  • Provider-specific timeouts                     │      │
│  │  • Exponential backoff (3 retries)                │      │
│  │  • 10% jitter to prevent thundering herd          │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Execution Flow

```
┌──────────┐     ┌────────────┐     ┌──────────────┐
│   Start  │────>│ Pre-Check  │────>│ Create       │
│          │     │            │     │ Checkpoint   │
└──────────┘     └────────────┘     └──────────────┘
                                             │
                    ┌────────────────────────┴────────────────────────┐
                    │                                                 │
                    ▼                                                 ▼
            ┌───────────────┐                                 ┌─────────────┐
            │ Loop Node     │                                 │ VLM Node    │
            │ • Count-based │                                 │ • Circuit   │
            │ • Condition   │                                 │   breaker   │
            │ • Limit: 1000 │                                 │ • Retry x3  │
            └───────────────┘                                 └─────────────┘
                    │                                                 │
                    │                 ┌──────────────────────────────┘
                    │                 │
                    ▼                 ▼
            ┌───────────────┐  ┌──────────────┐
            │ Condition     │  │ Error?       │
            │ Gate          │  │ • Rollback   │
            │ • Quality     │  │ • Recovery   │
            │   assessment  │  │ • DLQ        │
            └───────────────┘  └──────────────┘
                    │                 │
                    └─────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Auto         │
                    │ Checkpoint   │
                    │ • After gate │
                    │ • After loop │
                    │ • Every 5    │
                    │   nodes      │
                    └──────────────┘
```

---

## Fault Tolerance Features

### 1. Circuit Breaker Pattern

**Purpose:** Prevent cascading failures when LLM services are unavailable.

**Configuration:**

| Provider | Failure Threshold | Recovery Timeout |
|----------|-------------------|------------------|
| DeepSeek Reasoner | 3 | 300s |
| Zhipu GLM | 5 | 180s |
| Default LLM | 5 | 60s |
| Vector DB | 3 | 30s |
| MongoDB | 5 | 45s |

**Implementation:** `backend/app/core/circuit_breaker.py`

```python
@llm_service_circuit
async def _llm_call_with_circuit_breaker(...):
    """LLM call wrapped with circuit breaker protection."""
    model_name = model_config.get("model_name", "")
    timeout = get_provider_timeout(model_name)
    return ChatService.create_chat_stream(...)
```

### 2. Provider-Specific Timeouts

**DeepSeek Reasoning Models:**
- `deepseek-r1`, `deepseek-reasoner` → 300s timeout
- Reasoning models require more time for complex inference

**Zhipu GLM Models:**
- `glm-4.7`, `glm-4.7` → 180s timeout
- Moderate timeout for Chinese language models

**Default:**
- OpenAI, Moonshot, others → 120s timeout

### 3. Retry with Exponential Backoff

**Configuration:**
- **Max Retries:** 3
- **Base Delay:** 1.0s
- **Max Delay:** 60.0s
- **Jitter:** 10% (prevents thundering herd)

**Backoff Schedule:**
```
Attempt 1: Immediate
Attempt 2: 1.0s ± 0.1s
Attempt 3: 2.0s ± 0.2s
Attempt 4: 4.0s ± 0.4s
```

### 4. Automatic Checkpointing

**Triggers:**
- Before node execution (for rollback)
- After condition gates
- After loop iterations
- Every N nodes (default: 5)

**Storage:**
- Redis with 24-hour retention
- Keeps last 10 checkpoints
- Automatic cleanup of old checkpoints

**Usage:**

```python
# Manual checkpoint
await checkpoint_manager.save_checkpoint(reason="manual")

# Automatic rollback on error
try:
    result = await self.execute_node(node)
except Exception as e:
    await checkpoint_manager.rollback_to_checkpoint()

# List available checkpoints
checkpoints = await checkpoint_manager.list_checkpoints()
```

### 5. Loop Safety Limits

**Configurable Maximums:**

| Loop Type | Limit | Configurable |
|-----------|-------|--------------|
| Count | User-set `maxCount` | Yes |
| Condition | 1000 | `LOOP_LIMITS["condition"]` |
| Default | 1000 | `LOOP_LIMITS["default"]` |

**Purpose:** Prevent infinite loops in long-running workflows.

### 6. Quality Assessment Engine

**Multi-Dimensional Scoring:**

| Dimension | Weight | Metric |
|-----------|--------|--------|
| Completeness | 0.3 | Word count ≥ 100 |
| Coherence | 0.3 | Paragraphs + structure |
| Relevance | 0.2 | Keyword overlap |
| Length | 0.2 | Target length ratio |

**Pass/Fail Threshold:** 0.6 (60%)

**Usage:**

```python
assessor = QualityAssessmentEngine(global_variables)
assessment = assessor.assess_content_quality(
    content=generated_text,
    node_id="n15_review",
)

if assessment["passed"]:
    # Continue to next node
else:
    # Route to refinement
```

---

## State Persistence

### Global Variables

The workflow engine maintains 19 global variables for state tracking:

**Configuration (User-Set):**
- `thesis_topic`, `thesis_language`, `thesis_degree`
- `thesis_format`, `discipline_hint`
- `granularity_target`, `target_length_pages`
- `citation_style`, `min_sources_per_subsection`

**State Tracking (Runtime):**
- `loop_idx`, `chapter_idx`, `subsection_idx`
- `axes_count`, `chapters_count`, `subsections_count`
- `gaps_found`

**Data Structures:**
- `requirements`, `seed_axes`, `kb_map`
- `macro_outline`, `micro_outline`, `coverage`
- `chapters_list`, `subsections_list`
- `user_changes`, `patch_actions`, `exports`

### Context Management

**Memory Limits:**
- `MAX_CONTEXT_SIZE`: 1000 entries per node
- `MAX_CONTEXT_ENTRIES`: 10,000 total entries

**Auto-Cleanup:**
When limit exceeded, oldest entries are removed, keeping only the most recent.

---

## Error Handling

### Node-Level Errors

```python
try:
    result = await self.execute_node(node)
    if not result:
        return
    self.execution_status[node.node_id] = True

    # Auto-checkpoint after success
    if await checkpoint_manager.should_checkpoint(node, "node"):
        await checkpoint_manager.save_checkpoint(reason="after_node")

except Exception as e:
    # Attempt rollback
    rollback_success = await checkpoint_manager.rollback_to_checkpoint()

    if rollback_success:
        raise ValueError(f"Node {node.node_id} failed and rolled back: {e}")
    else:
        raise
```

### Workflow-Level Errors

**Cancellation:**
```python
async def check_cancellation(self):
    redis_conn = await redis.get_task_connection()
    status = await redis_conn.hget(f"workflow:{self.task_id}:operator", "status")
    if status == b"canceling":
        await self.cleanup()
        raise ValueError("Workflow canceled")
```

### Dead Letter Queue

Failed workflows are logged to Redis streams:
```python
await redis_conn.xadd(
    f"workflow:events:{self.task_id}",
    {
        "type": "workflow",
        "status": "error",
        "error": str(e),
        "create_time": str(datetime.now()),
    }
)
```

---

## Performance Considerations

### Memory Management

- Context cleanup every 10,000 entries
- Node-level context limit of 1,000 entries
- Checkpoint snapshots (not full context)

### Circuit Breaker State

- **Closed:** Normal operation
- **Open:** Rejecting requests (after threshold)
- **Half-Open:** Testing recovery

### Timeout Strategy

Provider-specific timeouts prevent:
- Blocking on slow reasoning models
- Wasted resources on failed calls
- Cascading timeouts in workflows

---

## Configuration

### Environment Variables

```bash
# Circuit Breaker
CIRCUIT_BREAKER_ENABLED=true
DEFAULT_FAILURE_THRESHOLD=5
DEFAULT_RECOVERY_TIMEOUT=60

# Checkpoint
CHECKPOINT_ENABLED=true
CHECKPOINT_INTERVAL_NODES=5
CHECKPOINT_MAX_CHECKPOINTS=10

# Loop Limits
LOOP_LIMIT_CONDITION=1000
LOOP_LIMIT_DEFAULT=1000
```

### Code Configuration

```python
# backend/app/workflow/workflow_engine.py

CHECKPOINT_CONFIG = {
    "enabled": True,
    "interval_nodes": 5,
    "on_loop_complete": True,
    "on_condition_gate": True,
    "max_checkpoints": 10,
}

# NOTE: LLM timeouts are configured via settings / per-user model config.
```

---

## Troubleshooting

### Common Issues

**Issue:** Circuit breaker frequently opens
**Solution:**
- Check LLM service health
- Increase `recovery_timeout`
- Reduce `failure_threshold`

**Issue:** Checkpoints not saving
**Solution:**
- Verify Redis connection
- Check `CHECKPOINT_CONFIG["enabled"]`
- Review Redis memory limits

**Issue:** Loop hitting safety limit
**Solution:**
- Review loop condition logic
- Increase `LOOP_LIMITS["condition"]`
- Add early termination condition

**Issue:** Quality gate always failing
**Solution:**
- Adjust quality criteria weights
- Lower pass threshold from 0.6
- Review generated content quality

---

## API Reference

### CheckpointManager

```python
class WorkflowCheckpointManager:
    async def save_checkpoint(reason: str = "manual") -> dict
    async def load_checkpoint(checkpoint_id: str = None) -> bool
    async def rollback_to_checkpoint(checkpoint_id: str = None) -> bool
    async def list_checkpoints() -> list
    async def should_checkpoint(node: TreeNode, node_type: str) -> bool
```

### QualityAssessmentEngine

```python
class QualityAssessmentEngine:
    def assess_content_quality(
        content: str,
        node_id: str,
        criteria: dict = None,
    ) -> dict

    def get_assessment_summary() -> dict
```

### Circuit Breaker Decorators

```python
@llm_service_circuit
async def protected_llm_call(...): ...

@deepseek_reasoner_circuit
async def protected_reasoning_call(...): ...

@zhipu_llm_circuit
async def protected_glm_call(...): ...
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.2.0 | 2026-01-26 | Fault tolerance enhancements: circuit breaker, checkpoints, retry, quality gates |
| 2.1.0 | 2026-01-25 | Loop safety limits, context cleanup |
| 2.0.0 | 2026-01-24 | DAG execution engine, state persistence |
| 1.0.0 | 2026-01-20 | Initial workflow engine |

---

## Related Documentation

- [Workflow Operations](../docs/work-flow/workflow.md) - User-facing workflow guide
- [Node Types](../docs/work-flow/nodes/) - Individual node documentation
- [TROUBLESHOOTING](operations/TROUBLESHOOTING.md) - Common issues and fixes
- [CHANGE_LOG](operations/CHANGE_LOG.md) - Version history

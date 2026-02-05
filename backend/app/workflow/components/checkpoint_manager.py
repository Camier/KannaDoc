"""
Checkpoint manager for workflow state and recovery.

Enhanced checkpoint management for workflow recovery. Supports automatic
checkpointing and rollback capabilities.
"""

import json
from typing import Optional, List
from datetime import datetime

from app.db.redis import redis
from app.core.logging import logger
from app.workflow.components.constants import CHECKPOINT_CONFIG


class WorkflowCheckpointManager:
    """
    Enhanced checkpoint management for workflow recovery.
    Supports automatic checkpointing and rollback capabilities.
    """

    def __init__(self, task_id: str, engine):
        """
        Initialize checkpoint manager.

        Args:
            task_id: Unique identifier for the workflow task
            engine: Reference to WorkflowEngine for state access
        """
        self.task_id = task_id
        self.engine = engine
        self.checkpoint_count = 0
        self.last_checkpoint_node = None

    async def save_checkpoint(self, reason: str = "manual") -> dict:
        """
        Save a workflow checkpoint with metadata.

        Args:
            reason: Why checkpoint was created (manual, auto, loop, gate, error)

        Returns:
            Checkpoint metadata
        """
        import time

        checkpoint_id = f"{self.task_id}_{int(time.time())}"
        self.checkpoint_count += 1

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "task_id": self.task_id,
            "created_at": datetime.now().isoformat(),
            "reason": reason,
            "node": self.last_checkpoint_node,
            "checkpoint_number": self.checkpoint_count,
            "state": {
                "global_variables": dict(self.engine.global_variables),
                "execution_status": dict(self.engine.execution_status),
                "loop_index": dict(self.engine.loop_index),
                "execution_stack": [
                    node.node_id for node in self.engine.execution_stack
                ],
                "context": self.engine.context,
                "context_snapshot": self._get_context_snapshot(),
            },
        }

        # Save to Redis with expiry
        redis_conn = await redis.get_task_connection()
        checkpoint_key = f"workflow:{self.task_id}:checkpoint:{checkpoint_id}"

        await redis_conn.setex(
            checkpoint_key,
            86400,  # 24 hour retention
            json.dumps(checkpoint),
        )

        # Add to checkpoint index
        await redis_conn.zadd(
            f"workflow:{self.task_id}:checkpoints",
            {checkpoint_id: self.checkpoint_count},
        )

        # Trim old checkpoints
        await self._trim_checkpoints(redis_conn)

        logger.info(
            f"Workflow {self.task_id}: Checkpoint #{self.checkpoint_count} saved "
            f"(reason={reason}, node={self.last_checkpoint_node})"
        )

        return checkpoint

    async def load_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """
        Load workflow from checkpoint.

        Args:
            checkpoint_id: Specific checkpoint to load, or latest if None

        Returns:
            True if loaded successfully
        """
        redis_conn = await redis.get_task_connection()

        # Get latest checkpoint if not specified
        if checkpoint_id is None:
            checkpoints = await redis_conn.zrevrange(
                f"workflow:{self.task_id}:checkpoints", 0, 0
            )
            if not checkpoints:
                logger.warning(f"Workflow {self.task_id}: No checkpoints found")
                return False
            checkpoint_id = checkpoints[0]

        checkpoint_key = f"workflow:{self.task_id}:checkpoint:{checkpoint_id}"
        data = await redis_conn.get(checkpoint_key)

        if not data:
            logger.error(
                f"Workflow {self.task_id}: Checkpoint {checkpoint_id} not found"
            )
            return False

        checkpoint = json.loads(data)

        # Restore state
        state = checkpoint["state"]
        self.engine.global_variables = state["global_variables"]
        self.engine.execution_status = state["execution_status"]
        self.engine.loop_index = state["loop_index"]
        self.engine.context = state.get("context", {})
        execution_stack = state.get("execution_stack", [])
        if execution_stack:
            from app.workflow.graph import TreeNode

            nodes = [TreeNode.get_node(node_id) for node_id in execution_stack]
            self.engine.execution_stack = [node for node in nodes if node is not None]
        self.last_checkpoint_node = checkpoint.get("node")

        logger.info(
            f"Workflow {self.task_id}: Restored from checkpoint {checkpoint_id} "
            f"(#{checkpoint['checkpoint_number']}, created={checkpoint['created_at']})"
        )

        return True

    async def rollback_to_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """
        Rollback workflow to a previous checkpoint.

        Args:
            checkpoint_id: Specific checkpoint to rollback to, or latest if None

        Returns:
            True if rollback successful
        """
        logger.warning(f"Workflow {self.task_id}: Rolling back to checkpoint...")
        success = await self.load_checkpoint(checkpoint_id)

        if success:
            # Clear execution state after rollback point
            redis_conn = await redis.get_task_connection()
            await redis_conn.xadd(
                f"workflow:events:{self.task_id}",
                {
                    "type": "workflow",
                    "status": "rollback",
                    "result": "",
                    "error": f"Rolled back to checkpoint",
                    "create_time": str(datetime.now()),
                },
            )

        return success

    def _get_context_snapshot(self) -> dict:
        """
        Get a lightweight snapshot of current context.

        Returns:
            Dict with context snapshot
        """
        snapshot = {}
        for node_id, entries in self.engine.context.items():
            if entries:
                # Store only the most recent entry
                snapshot[node_id] = {
                    "last_result": entries[-1].get("result", "")[:200],
                    "entry_count": len(entries),
                }
        return snapshot

    async def _trim_checkpoints(self, redis_conn):
        """
        Keep only the most recent checkpoints.

        Args:
            redis_conn: Redis connection
        """
        max_checkpoints = CHECKPOINT_CONFIG["max_checkpoints"]
        await redis_conn.zremrangebyrank(
            f"workflow:{self.task_id}:checkpoints",
            0,
            -(max_checkpoints + 1),
        )

    async def list_checkpoints(self) -> List[dict]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint metadata
        """
        redis_conn = await redis.get_task_connection()
        checkpoint_ids = await redis_conn.zrevrange(
            f"workflow:{self.task_id}:checkpoints", 0, -1
        )

        checkpoints = []
        for cid in checkpoint_ids:
            key = f"workflow:{self.task_id}:checkpoint:{cid}"
            data = await redis_conn.get(key)
            if data:
                checkpoints.append(json.loads(data))

        return checkpoints

    async def should_checkpoint(self, node, node_type: str) -> bool:
        """
        Determine if a checkpoint should be created at this node.

        Args:
            node: Current node
            node_type: Node type

        Returns:
            True if checkpoint should be created
        """
        if not CHECKPOINT_CONFIG["enabled"]:
            return False

        self.last_checkpoint_node = node.node_id

        # Checkpoint at condition gates
        if node_type == "condition" and CHECKPOINT_CONFIG["on_condition_gate"]:
            return True

        # Checkpoint after loop iterations
        if node_type == "loop" and CHECKPOINT_CONFIG["on_loop_complete"]:
            # Check if this is a loop exit (node is in loop_parent.loop_last)
            if node.loop_parent and node in node.loop_parent.loop_last:
                return True

        # Checkpoint based on node interval
        # This would need to track node count - implemented in WorkflowEngine

        return False

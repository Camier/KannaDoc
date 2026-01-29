# workflow/executors/base_executor.py
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from app.workflow.graph import TreeNode
from app.workflow.components.constants import MAX_CONTEXT_SIZE, MAX_CONTEXT_ENTRIES
from app.core.logging import logger

if TYPE_CHECKING:
    from app.workflow.sandbox import CodeSandbox


class NodeResult:
    """Result of node execution"""

    def __init__(
        self,
        success: bool,
        output: Any = None,
        error: Optional[str] = None,
        updated_variables: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.updated_variables = updated_variables or {}


class BaseExecutor(ABC):
    """Base class for node executors"""

    def __init__(
        self,
        global_variables: Dict[str, Any],
        context: Dict[str, Any],
        sandbox=None,
        task_id: Optional[str] = None,
        checkpoint_manager=None,
    ):
        self.global_variables = global_variables
        self.context = context
        self.sandbox = sandbox
        self.task_id = task_id
        self.checkpoint_manager = checkpoint_manager
        self._total_context_entries = 0

    def _add_to_context(self, node_id: str, result: Any):
        """
        Add result to node context with size limits.

        Implements context cleanup to prevent memory leaks by:
        - Limiting entries per node (MAX_CONTEXT_SIZE)
        - Limiting total entries (MAX_CONTEXT_ENTRIES)
        """
        if node_id not in self.context:
            self.context[node_id] = []

        # Check per-node limit
        if len(self.context[node_id]) >= MAX_CONTEXT_SIZE:
            self.context[node_id] = self.context[node_id][-MAX_CONTEXT_SIZE:]
            self._total_context_entries = sum(
                len(entries) for entries in self.context.values()
            )
        else:
            self.context[node_id].append({"result": result})
            self._total_context_entries += 1

        # Check total context limit and cleanup if needed
        if self._total_context_entries > MAX_CONTEXT_ENTRIES:
            self._cleanup_context_if_needed()

    def _cleanup_context_if_needed(self):
        """
        Clean up context dictionary to prevent memory leaks.
        """
        entries_to_remove = self._total_context_entries - (MAX_CONTEXT_ENTRIES // 2)

        for node_id in list(self.context.keys()):
            node_entries = self.context.get(node_id, [])
            if not node_entries:
                continue

            while len(node_entries) > 0 and entries_to_remove > 0:
                removed = node_entries.pop(0)
                entries_to_remove -= 1
                self._total_context_entries -= 1

        logger.debug(
            f"Context cleanup: Removed entries, total entries now: "
            f"{self._total_context_entries}"
        )

    @abstractmethod
    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute a node and return result.

        Args:
            node: The TreeNode to execute

        Returns:
            NodeResult containing execution results
        """
        pass

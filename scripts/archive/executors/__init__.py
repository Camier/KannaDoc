# workflow/executors/__init__.py
"""
NOTE: The executors package is NOT currently used by workflow_engine.py.
It was an incomplete refactoring that was never integrated.

The quality_gate_executor was archived to scripts/archive/quality_assessment/
as it used fake hardcoded scores (0.75, 0.85) for quality metrics.

Status: This entire executors/ directory is abandoned and should be either:
1. Integrated into workflow_engine.py, or
2. Removed entirely

See docs/plans/2026-01-28-codebase-remediation.md for details.
"""

from .base_executor import BaseExecutor, NodeResult
from .vlm_node_executor import VLMNodeExecutor
from .llm_node_executor import LLMNodeExecutor
from .code_node_executor import CodeNodeExecutor
from .http_node_executor import HTTPNodeExecutor
from .condition_executor import ConditionExecutor
# from .quality_gate_executor import QualityGateExecutor, QualityAssessment, Decision  # ARCHIVED

__all__ = [
    "BaseExecutor",
    "NodeResult",
    "VLMNodeExecutor",
    "LLMNodeExecutor",
    "CodeNodeExecutor",
    "HTTPNodeExecutor",
    "ConditionExecutor",
    # "QualityGateExecutor",  # ARCHIVED - used fake scores
    # "QualityAssessment",  # ARCHIVED
    # "Decision",  # ARCHIVED
]

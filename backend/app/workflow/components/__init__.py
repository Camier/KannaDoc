"""
Workflow engine components.

This package contains reusable components extracted from monolithic
workflow engine, providing better separation of concerns and testability.
"""

# Use relative imports for package consistency
from .constants import (
    MAX_CONTEXT_SIZE,
    MAX_CONTEXT_ENTRIES,
    LOOP_LIMITS,
    CHECKPOINT_CONFIG,
)

# NOTE: QualityAssessmentEngine was archived to scripts/archive/quality_assessment/
# The workflow_engine.py has its own local implementation that is used instead.
# from .quality_assessment import QualityAssessmentEngine  # ARCHIVED

from .checkpoint_manager import WorkflowCheckpointManager
from .llm_client import LLMClient

__all__ = [
    # Constants
    "MAX_CONTEXT_SIZE",
    "MAX_CONTEXT_ENTRIES",
    "LOOP_LIMITS",
    "CHECKPOINT_CONFIG",
    # Components
    # "QualityAssessmentEngine",  # ARCHIVED - using local implementation in workflow_engine.py
    "WorkflowCheckpointManager",
    "LLMClient",
]

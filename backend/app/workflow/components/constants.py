"""
Workflow engine constants and configuration.

This module contains shared constants used across the workflow engine
and its components, providing a single source of truth for configuration values.
"""

# Memory limits for context storage to prevent memory leaks
MAX_CONTEXT_SIZE = 1000  # Maximum entries per node
MAX_CONTEXT_ENTRIES = 10000  # Total entries before cleanup

# Loop iteration limits for safety
LOOP_LIMITS = {
    "count": None,  # maxCount is set by user
    "condition": 1000,  # safety limit for condition-based loops
    "default": 1000,
}

# Checkpoint configuration
CHECKPOINT_CONFIG = {
    "enabled": True,
    "interval_nodes": 5,  # Auto-checkpoint every N nodes
    "on_loop_complete": True,  # Checkpoint after each loop iteration
    "on_condition_gate": True,  # Checkpoint after condition nodes
    "max_checkpoints": 10,  # Keep only recent checkpoints
}

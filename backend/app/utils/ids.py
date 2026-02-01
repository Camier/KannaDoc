"""
ID Parsing Utilities

Provides consistent parsing and validation for composite ID formats used across the application.
"""

from typing import Optional


# Milvus collection name utilities
def to_milvus_collection_name(base_id: str) -> str:
    """
    Convert a base/knowledge base ID to Milvus collection name.
    Replaces hyphens with underscores and adds 'colqwen' prefix.

    Args:
        base_id: Base ID (e.g., "kb_550e8400-e29b-41d4-a716-446655440000")

    Returns:
        Milvus collection name

    Example:
        >>> to_milvus_collection_name("kb_550e8400-e29b-41d4-a716-446655440000")
        "colqwenkb_550e8400_e29b_41d4_a716_446655440000"
    """
    return "colqwen" + base_id.replace("-", "_")

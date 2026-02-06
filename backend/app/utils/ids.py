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
    base_id = (base_id or "").strip()

    # Thesis corpus: some deployments pass raw Milvus collection names (e.g. ColPali patch
    # collections like "colpali_kanna_128" or "default.colpali_kanna_128").
    # Keep these as-is (MilvusClient does not use the database prefix in collection_name).
    if "." in base_id:
        _db, candidate = base_id.split(".", 1)
        if candidate.startswith("colpali_") or candidate.endswith("_pages_sparse"):
            return candidate

    if base_id.startswith("colpali_") or base_id.endswith("_pages_sparse"):
        return base_id

    # Already-converted collection names should not be double-prefixed.
    if base_id.startswith("colqwen"):
        return base_id.replace("-", "_")

    return "colqwen" + base_id.replace("-", "_")

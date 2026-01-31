"""
ID Parsing Utilities

Provides consistent parsing and validation for composite ID formats used across the application.
"""

import re
from typing import Optional, Tuple

# Pattern for username_uuid format
USERNAME_UUID_PATTERN = re.compile(r"^([^_]+)_(.+)$")


def parse_username_from_id(composite_id: str) -> Optional[str]:
    """
    Extract username from a composite ID (format: username_uuid).

    Args:
        composite_id: ID in format "username_uuid"

    Returns:
        Username part or None if format is invalid

    Example:
        >>> parse_username_from_id("john_550e8400-e29b-41d4-a716-446655440000")
        "john"
    """
    if not composite_id:
        return None

    match = USERNAME_UUID_PATTERN.match(composite_id)
    if match:
        return match.group(1)
    return None


def parse_id_parts(composite_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Split a composite ID into username and UUID parts.

    Args:
        composite_id: ID in format "username_uuid"

    Returns:
        Tuple of (username, uuid) or (None, None) if invalid

    Example:
        >>> parse_id_parts("john_550e8400-e29b-41d4-a716-446655440000")
        ("john", "550e8400-e29b-41d4-a716-446655440000")
    """
    if not composite_id:
        return None, None

    match = USERNAME_UUID_PATTERN.match(composite_id)
    if match:
        return match.group(1), match.group(2)
    return None, None


def is_valid_composite_id(composite_id: str) -> bool:
    """
    Validate if a string is a properly formatted composite ID.

    Args:
        composite_id: String to validate

    Returns:
        True if valid username_uuid format
    """
    if not composite_id:
        return False
    return USERNAME_UUID_PATTERN.match(composite_id) is not None


def build_composite_id(username: str, uuid: str) -> str:
    """
    Build a composite ID from username and UUID parts.

    Args:
        username: User identifier
        uuid: Unique identifier

    Returns:
        Composite ID string

    Example:
        >>> build_composite_id("john", "550e8400-e29b-41d4-a716-446655440000")
        "john_550e8400-e29b-41d4-a716-446655440000"
    """
    return f"{username}_{uuid}"


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


def from_milvus_collection_name(collection_name: str) -> Optional[str]:
    """
    Extract base ID from Milvus collection name.

    Args:
        collection_name: Milvus collection name

    Returns:
        Base ID or None if not a colqwen collection
    """
    if not collection_name.startswith("colqwen"):
        return None
    base_part = collection_name[7:]  # Remove 'colqwen' prefix
    return base_part.replace("_", "-")

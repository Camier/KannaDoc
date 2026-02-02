"""Shared utility for safely parsing string values in workflow nodes."""

import ast
import json
from typing import Any


def safe_parse(v: Any) -> Any:
    """
    Safely parse a string value to its Python literal representation.

    Uses ast.literal_eval which only evaluates literals (strings, numbers,
    tuples, lists, dicts, booleans, None) - NOT arbitrary code.

    Args:
        v: Value to parse (if string, attempts parsing)

    Returns:
        Parsed value or original if parsing fails
    """
    if not isinstance(v, str):
        return v

    # Try JSON first (safer and more common)
    try:
        return json.loads(v)
    except (json.JSONDecodeError, TypeError):
        pass

    # Fall back to ast.literal_eval for Python literals
    try:
        return ast.literal_eval(v)
    except (ValueError, SyntaxError, TypeError):
        return v

"""
Shared utility functions for Datalab processing modules.
Provides validation, hashing, and path sanitization.
"""

import hashlib
import logging
import os
import re
import time
import random
from pathlib import Path
from typing import Optional

from app.core.utils import (
    calculate_sha256_file,
    calculate_sha256_string,
    is_valid_pdf,
    sanitize_path_component,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"
DATALAB_ROOT = Path(os.environ.get("DATALAB_ROOT", "/LAB/@thesis/datalab"))


def validate_file_size(file_path: Path, max_size_mb: int = 100) -> None:
    """
    Validate that a file is within acceptable size limits.

    Args:
        file_path: Path to the file to validate
        max_size_mb: Maximum file size in megabytes (default: 100MB)

    Raises:
        ValueError: If file exceeds maximum size
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"File too large: {size_mb:.1f}MB exceeds maximum {max_size_mb}MB"
        )

    if file_size == 0:
        raise ValueError(f"File is empty: {file_path}")


def generate_unique_id(length: int = 8) -> str:
    """
    Generate a short unique identifier using hash of time and random data.

    Args:
        length: Length of the ID to generate (default: 8 characters)

    Returns:
        Short unique identifier string
    """
    seed = f"{time.time_ns()}-{random.random()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:length]


# =============================
# API Key Validation
# =============================


def validate_api_key_format(api_key: str, raise_on_invalid: bool = True) -> bool:
    """
    Validate that an API key follows expected format.

    DataLab API keys don't require a specific prefix, just minimum length.

    Args:
        api_key: The API key string to validate
        raise_on_invalid: If True, raises ValueError on invalid format;
                         if False, returns False

    Returns:
        True if valid format, False otherwise (when raise_on_invalid=False)

    Raises:
        ValueError: If API key format is invalid and raise_on_invalid=True
    """
    if not api_key or not isinstance(api_key, str):
        if raise_on_invalid:
            raise ValueError("API key must be a non-empty string")
        return False

    api_key = api_key.strip()

    # Check minimum length (API keys should be at least 10 characters)
    if len(api_key) < 10:
        error_msg = (
            f"API key seems too short ({len(api_key)} chars), must be at least 10"
        )
        if raise_on_invalid:
            raise ValueError(error_msg)
        return False

    # Check for reasonable length (most API keys are under 200 chars)
    if len(api_key) > 200:
        error_msg = f"API key seems too long ({len(api_key)} chars)"
        if raise_on_invalid:
            raise ValueError(error_msg)
        return False

    # Check for valid characters (alphanumeric, underscore, hyphen, common special chars)
    if not re.match(r"^[A-Za-z0-9_\-\.]+$", api_key):
        error_msg = "API key contains invalid characters"
        if raise_on_invalid:
            raise ValueError(error_msg)
        return False

    return True


__all__ = [
    "MAX_FILE_SIZE",
    "PDF_MAGIC_BYTES",
    "calculate_sha256_string",
    "calculate_sha256_file",
    "sanitize_path_component",
    "generate_unique_id",
    "is_valid_pdf",
    "validate_file_size",
    "validate_api_key_format",
    "DATALAB_ROOT",
]

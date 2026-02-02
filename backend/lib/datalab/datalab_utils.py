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

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
PDF_MAGIC_BYTES = b"%PDF-"

# Datalab project root constant
DATALAB_ROOT = Path(os.environ.get("DATALAB_ROOT", "/LAB/@thesis/datalab"))


# =============================
# File Validation
# =============================

def is_valid_pdf(file_path: Path) -> bool:
    """
    Validate that a file is a valid PDF by checking:
    1. File exists
    2. File has .pdf extension
    3. File starts with PDF magic bytes (%PDF-)

    Args:
        file_path: Path to the file to validate

    Returns:
        True if file is a valid PDF, False otherwise
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return False

    if file_path.suffix.lower() != '.pdf':
        return False

    try:
        with file_path.open("rb") as f:
            header = f.read(4)
            return header == b'%PDF'
    except Exception:
        return False


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
        raise ValueError(f"File too large: {size_mb:.1f}MB exceeds maximum {max_size_mb}MB")

    if file_size == 0:
        raise ValueError(f"File is empty: {file_path}")


# =============================
# Cryptographic Hashing
# =============================

def calculate_sha256_string(input_str: str) -> str:
    """
    Calculate SHA256 hash of a string.

    Args:
        input_str: String to hash

    Returns:
        Hexadecimal SHA-256 hash string
    """
    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()


def calculate_sha256_file(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Calculate SHA-256 hash of a file for deduplication.

    Args:
        file_path: Path to the file to hash
        chunk_size: Size of chunks to read (default: 1MB)

    Returns:
        Hexadecimal SHA-256 hash string

    Raises:
        IOError: If file cannot be read
    """
    file_path = Path(file_path)
    hash_sha256 = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Failed to hash {file_path}: {e}")
        raise IOError(f"Failed to calculate SHA-256 for {file_path}: {e}")


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
        error_msg = f"API key seems too short ({len(api_key)} chars), must be at least 10"
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
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', api_key):
        error_msg = "API key contains invalid characters"
        if raise_on_invalid:
            raise ValueError(error_msg)
        return False

    return True


# =============================
# Path Sanitization
# =============================

def sanitize_path_component(component: str) -> str:
    """
    Sanitize a string for safe use as a filename/path component.

    Removes or replaces characters that could be problematic in filenames:
    - Path traversal sequences (..)
    - Path separators (/ , \\)
    - Control characters
    - Special shell characters

    Args:
        component: The string to sanitize

    Returns:
        Sanitized string safe for use in filenames
    """
    if not isinstance(component, str):
        component = str(component)

    # CRITICAL: Remove path traversal sequences FIRST
    sanitized = component.replace('..', '').replace('...', '')

    # Replace path separators with underscore
    sanitized = sanitized.replace('/', '_').replace('\\', '_')

    # Remove control characters
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)

    # Replace other problematic characters with underscore
    # Keep: alphanumeric, space, hyphen, underscore, dot, parens
    sanitized = re.sub(r'[^\w\s\-\.\(\)]', '_', sanitized)

    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')

    # Limit length (filesystem limits)
    max_length = 255
    if len(sanitized) > max_length:
        # Preserve extension if present
        if '.' in sanitized:
            name, ext = sanitized.rsplit('.', 1)
            sanitized = name[:max_length - len(ext) - 1] + '.' + ext
        else:
            sanitized = sanitized[:max_length]

    # Fallback for empty result
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


# Export all utilities
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

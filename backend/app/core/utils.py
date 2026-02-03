import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_sha256_string(input_str: str) -> str:
    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()


def calculate_sha256_file(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
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


def sanitize_path_component(component: str) -> str:
    if not isinstance(component, str):
        component = str(component)

    sanitized = component.replace("..", "").replace("...", "")
    sanitized = sanitized.replace("/", "_").replace("\\", "_")
    sanitized = "".join(char for char in sanitized if ord(char) >= 32)
    sanitized = re.sub(r"[^\w\s\-\.\(\)]", "_", sanitized)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip(". ")

    max_length = 255
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    if not sanitized:
        raise ValueError("Path component became empty after sanitization")

    return sanitized


def is_valid_pdf(file_path: Path) -> bool:
    file_path = Path(file_path)

    if not file_path.exists():
        return False

    if file_path.suffix.lower() != ".pdf":
        return False

    try:
        with file_path.open("rb") as f:
            header = f.read(4)
            return header == b"%PDF"
    except Exception:
        return False

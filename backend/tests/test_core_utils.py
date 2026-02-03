import pytest
from pathlib import Path
import tempfile
from app.core.utils import (
    calculate_sha256_file,
    calculate_sha256_string,
    is_valid_pdf,
    sanitize_path_component,
)


def test_calculate_sha256_string():
    assert (
        calculate_sha256_string("test")
        == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    )
    assert len(calculate_sha256_string("anything")) == 64


def test_calculate_sha256_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        temp_path = Path(f.name)

    try:
        hash_result = calculate_sha256_file(temp_path)
        assert len(hash_result) == 64
        assert isinstance(hash_result, str)
    finally:
        temp_path.unlink()


def test_sanitize_path_component():
    assert sanitize_path_component("normal_name.pdf") == "normal_name.pdf"
    assert sanitize_path_component("path/with/slashes") == "path_with_slashes"
    assert sanitize_path_component("..danger..") == "danger"
    assert sanitize_path_component("file with spaces") == "file with spaces"

    with pytest.raises(ValueError, match="empty after sanitization"):
        sanitize_path_component("...")


def test_is_valid_pdf():
    assert is_valid_pdf(Path("nonexistent.pdf")) == False

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\nfake pdf")
        temp_path = Path(f.name)

    try:
        assert is_valid_pdf(temp_path) == True
    finally:
        temp_path.unlink()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"not a pdf")
        temp_path = Path(f.name)

    try:
        assert is_valid_pdf(temp_path) == False
    finally:
        temp_path.unlink()

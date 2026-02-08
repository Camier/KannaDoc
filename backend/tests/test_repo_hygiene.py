"""Repository hygiene checks to prevent drift-prone patterns.

These tests are intentionally lightweight and avoid hashing the PDF corpus.
They focus on preventing known breakages (hardcoded absolute paths) and
identifying pathological directory recursion.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.unit


def _repo_root() -> Path:
    # layra/backend/tests -> repo root
    return Path(__file__).resolve().parents[2]


def test_no_hardcoded_thesis_pdf_abs_path() -> None:
    """Hardcoded absolute paths will break on other machines and in CI."""
    root = _repo_root()
    # Construct dynamically so this test file doesn't contain the banned literal.
    banned = "/LAB/@thesis/layra" + "/data/pdfs"

    # Only scan tracked-ish source trees; avoid backend/data which is large and can
    # contain embedded paths from extraction output.
    scan_dirs = [
        root / "backend" / "app",
        root / "backend" / "scripts",
        root / "backend" / "tests",
        root / "frontend" / "src",
        root / "docs",
        root / "thesis",
        root / "AGENTS.md",
    ]

    hits: list[str] = []
    for p in scan_dirs:
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="ignore")
            if banned in content:
                hits.append(str(p.relative_to(root)))
            continue

        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file():
                continue
            # Skip this test file and the scanner itself (they will necessarily
            # embed the banned string in some form).
            if f.name in {"test_repo_hygiene.py", "repo_hygiene_scan.py"}:
                continue
            # Skip obvious binaries
            if f.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".ico", ".zip"}:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if banned in content:
                hits.append(str(f.relative_to(root)))

    assert not hits, f"Found hardcoded absolute path '{banned}' in: {hits}"


def test_no_recursive_migrations_previous_dir() -> None:
    """Recursive migrations_previous folders are almost always accidental."""
    root = _repo_root()
    mp = root / "backend" / "migrations" / "migrations_previous"
    if not mp.exists():
        pytest.skip("migrations_previous not present")

    nested = mp / "migrations_previous"
    if not nested.exists():
        return

    # This directory is currently gitignored in this repo (.gitignore has `migrations/`).
    # Don't hard-fail CI over ignored local artifacts; surface via the local scanner instead.
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", str(nested.relative_to(root))],
            cwd=str(root),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            pytest.skip("Recursive migrations_previous exists but is gitignored (local hygiene issue)")
    except Exception:
        # If git isn't available for some reason, fall back to skipping rather than failing.
        pytest.skip("Unable to determine ignore status for migrations_previous")

    assert False, (
        "Found recursive directory backend/migrations/migrations_previous/migrations_previous/ "
        "and it is not ignored. This increases drift risk and confuses tools."
    )

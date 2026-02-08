#!/usr/bin/env python3
"""Repository hygiene scanner for drift-prone duplication patterns.

This is intentionally a lightweight local tool: it detects the common sources
of repo drift and confusing duplication without trying to "fix" anything
automatically.

Checks (best-effort):
- Hardcoded absolute corpus paths (e.g. /LAB/@thesis/layra + /data/pdfs)
- Recursive junk directories like migrations_previous/migrations_previous/...
- PDF corpus mirrors (backend/data/pdfs vs backend/literature/corpus) presence
  and basic set equality by filename (optional: content hash with --hash-pdfs)
- Extraction raw output duplication (attempt1_final_result.json vs result.json)
  with optional content hashing

Exit status:
- 0: no errors (warnings may still be emitted)
- 2: errors found
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path


CHUNK = 1024 * 1024  # 1 MiB


@dataclass(frozen=True)
class Finding:
    level: str  # "ERROR" | "WARN" | "INFO"
    message: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _iter_files(root: Path, exclude_dirs: set[str] | None = None) -> list[Path]:
    exclude_dirs = exclude_dirs or set()
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                if p.is_symlink():
                    continue
            except OSError:
                continue
            out.append(p)
    return out


def check_no_hardcoded_abs_paths(repo_root: Path) -> list[Finding]:
    """Detect hardcoded absolute paths that will break on other machines."""
    # Build these dynamically so this file doesn't contain the literal banned
    # path string; otherwise any naive scanner will flag the scanner itself.
    repo_abs = "/LAB/@thesis/layra"
    bad_strings = {
        repo_abs + "/data/pdfs",
        repo_abs + "/backend/literature/corpus",
    }

    findings: list[Finding] = []
    # Keep this cheap: scan small text files only, skip big binary trees.
    exclude_dirs = {
        ".git",
        "node_modules",
        ".next",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "backend/data",
        "backend/literature",
    }

    files = _iter_files(repo_root, exclude_dirs=exclude_dirs)
    for p in files:
        # Only scan likely text files. (This is a heuristic.)
        if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".ico", ".zip"}:
            continue
        try:
            b = p.read_bytes()
        except Exception:
            continue
        if len(b) > 2_000_000:
            continue
        try:
            s = b.decode("utf-8", errors="ignore")
        except Exception:
            continue
        for bad in bad_strings:
            if bad in s:
                findings.append(
                    Finding(
                        level="ERROR",
                        message=f"Hardcoded absolute path '{bad}' found in {p.relative_to(repo_root)}",
                    )
                )
    return findings


def check_recursive_migrations_previous(repo_root: Path) -> list[Finding]:
    """Detect '.../migrations_previous/migrations_previous/...' recursion."""
    findings: list[Finding] = []
    root = repo_root / "backend" / "migrations" / "migrations_previous"
    if not root.exists():
        return findings

    # If the directory contains itself as a subdirectory, it's already suspicious.
    nested = root / "migrations_previous"
    if nested.exists() and nested.is_dir():
        findings.append(
            Finding(
                level="ERROR",
                message=(
                    "Recursive directory detected: backend/migrations/migrations_previous/"
                    "migrations_previous/. This is usually accidental and increases drift risk."
                ),
            )
        )

    # Also flag any path that repeats 'migrations_previous' multiple times.
    for dp, dns, fns in os.walk(root):
        rel = Path(dp).relative_to(repo_root)
        repeated = sum(1 for part in rel.parts if part == "migrations_previous")
        if repeated >= 2:
            findings.append(
                Finding(
                    level="WARN",
                    message=f"Deep recursion under {rel} (migrations_previous repeated {repeated}x)",
                )
            )
            break
    return findings


def check_pdf_mirror(repo_root: Path, hash_pdfs: bool) -> list[Finding]:
    """Check mirror between backend/data/pdfs and backend/literature/corpus."""
    findings: list[Finding] = []
    a = repo_root / "backend" / "data" / "pdfs"
    b = repo_root / "backend" / "literature" / "corpus"

    if not a.exists() and not b.exists():
        return findings

    # If the legacy path is a symlink to the canonical directory, treat it as healthy.
    if b.exists() and b.is_symlink():
        try:
            target = b.resolve()
        except Exception as e:
            findings.append(
                Finding(level="WARN", message=f"PDF corpus symlink exists but failed to resolve: {b} ({e})")
            )
            return findings

        if a.exists() and a.resolve() == target:
            findings.append(
                Finding(
                    level="INFO",
                    message="PDF corpus canonicalized: backend/literature/corpus is a symlink to backend/data/pdfs.",
                )
            )
            return findings
        findings.append(
            Finding(
                level="WARN",
                message=f"PDF corpus symlink points somewhere unexpected: {b} -> {target}",
            )
        )
        return findings

    if a.exists() and not b.exists():
        findings.append(Finding(level="INFO", message="PDF corpus present only at backend/data/pdfs"))
        return findings
    if b.exists() and not a.exists():
        findings.append(Finding(level="WARN", message="PDF corpus present only at backend/literature/corpus"))
        return findings

    a_files = sorted([p for p in a.glob("*.pdf") if p.is_file()])
    b_files = sorted([p for p in b.glob("*.pdf") if p.is_file()])
    a_names = {p.name for p in a_files}
    b_names = {p.name for p in b_files}

    only_a = sorted(a_names - b_names)
    only_b = sorted(b_names - a_names)
    if only_a or only_b:
        msg = []
        if only_a:
            msg.append(f"Only in backend/data/pdfs: {only_a[:10]}")
        if only_b:
            msg.append(f"Only in backend/literature/corpus: {only_b[:10]}")
        findings.append(Finding(level="ERROR", message="PDF mirror filename drift: " + " | ".join(msg)))
        return findings

    if not hash_pdfs:
        findings.append(
            Finding(
                level="INFO",
                message=(
                    "PDF mirror looks aligned by filename (content not hashed). "
                    "Use --hash-pdfs for a deep content check."
                ),
            )
        )
        return findings

    # Deep content check
    name_to_hash_a = {p.name: _sha256_file(p) for p in a_files}
    name_to_hash_b = {p.name: _sha256_file(p) for p in b_files}
    drift = [name for name in a_names if name_to_hash_a[name] != name_to_hash_b[name]]
    if drift:
        findings.append(
            Finding(
                level="ERROR",
                message=f"PDF mirror content drift detected (sha256 mismatch), examples: {drift[:10]}",
            )
        )
    else:
        findings.append(Finding(level="INFO", message="PDF mirror content hashes match (sha256)."))
    return findings


def check_raw_result_mirror(repo_root: Path, hash_raw: bool) -> list[Finding]:
    """Check attempt1_final_result.json vs result.json under extractions/*/raw/."""
    findings: list[Finding] = []
    base = repo_root / "backend" / "data" / "extractions"
    if not base.exists():
        return findings

    same = 0
    diff = 0
    both = 0
    canonical_links = 0
    for dp, dns, fns in os.walk(base):
        if "raw" not in Path(dp).parts:
            continue
        p = Path(dp)
        a = p / "attempt1_final_result.json"
        r = p / "result.json"
        if not a.exists() and not r.exists():
            continue
        if a.exists() and r.exists():
            if a.is_symlink():
                try:
                    if a.resolve() == r.resolve():
                        canonical_links += 1
                        continue
                except Exception:
                    # Fall through and treat as "both exist" to get surfaced to the user.
                    pass
            both += 1
            if not hash_raw:
                # If we aren't hashing, just flag that both exist as a drift risk.
                continue
            try:
                if _sha256_file(a) == _sha256_file(r):
                    same += 1
                else:
                    diff += 1
            except Exception as e:
                findings.append(Finding(level="WARN", message=f"Failed hashing raw results under {p}: {e}"))

    if both == 0:
        if canonical_links > 0:
            findings.append(
                Finding(
                    level="INFO",
                    message=(
                        f"Raw results canonicalized: {canonical_links} raw dirs use "
                        "attempt1_final_result.json as a symlink to result.json."
                    ),
                )
            )
        return findings

    if not hash_raw:
        findings.append(
            Finding(
                level="WARN",
                message=(
                    f"Found {both} extraction raw directories containing both "
                    "attempt1_final_result.json and result.json. This is a drift risk. "
                    "Use --hash-raw to check whether they're identical."
                ),
            )
        )
        return findings

    if diff > 0:
        findings.append(
            Finding(
                level="INFO",
                message=f"Raw results: {both} dirs with both files; {diff} differ, {same} identical.",
            )
        )
    else:
        findings.append(
            Finding(
                level="WARN",
                message=(
                    f"Raw results: {both} dirs with both files and all are identical ({same}). "
                    "You are storing duplicate raw outputs; consider retaining only one canonical filename."
                ),
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repo for drift-prone duplication/hygiene issues.")
    parser.add_argument("--repo-root", type=str, default=".", help="Repo root directory (default: .)")
    parser.add_argument(
        "--hash-pdfs",
        action="store_true",
        help="Deep-check PDF mirrors by sha256 (expensive).",
    )
    parser.add_argument(
        "--hash-raw",
        action="store_true",
        help="Deep-check raw result duplicates by sha256 (can be expensive).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    findings: list[Finding] = []

    findings.extend(check_no_hardcoded_abs_paths(repo_root))
    findings.extend(check_recursive_migrations_previous(repo_root))
    findings.extend(check_pdf_mirror(repo_root, hash_pdfs=bool(args.hash_pdfs)))
    findings.extend(check_raw_result_mirror(repo_root, hash_raw=bool(args.hash_raw)))

    # Report
    for f in findings:
        print(f"{f.level}: {f.message}")

    has_error = any(f.level == "ERROR" for f in findings)
    return 2 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())

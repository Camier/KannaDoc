#!/usr/bin/env python3
"""
Deep cleanup and organization script for DataLab data directory.
Creates a clean, organized structure and archives clutter.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

ROOT = Path("/LAB/@thesis/datalab")
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "_archive"


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def archive_file(src: Path, archive_subdir: str) -> None:
    """Move a file to archive."""
    dest_dir = ensure_dir(ARCHIVE_DIR / "by_type" / archive_subdir)
    dest = dest_dir / src.name
    if dest.exists():
        dest = (
            dest_dir
            / f"{src.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{src.suffix}"
        )
    shutil.move(str(src), str(dest))
    print(f"  [ARCHIVED] {src.name} -> {archive_subdir}/")


def archive_directory(src: Path, archive_subdir: str) -> None:
    """Move a directory to archive."""
    dest_dir = ensure_dir(ARCHIVE_DIR / "by_type" / archive_subdir)
    dest = dest_dir / src.name
    if dest.exists():
        dest = dest_dir / f"{src.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.move(str(src), str(dest))
    print(f"  [ARCHIVED] {src.name}/ -> {archive_subdir}/")


def move_to(src: Path, dest_dir: Path) -> None:
    """Move file to destination directory."""
    ensure_dir(dest_dir)
    dest = dest_dir / src.name
    if dest.exists():
        print(f"  [SKIP] Destination exists: {src.name}")
        return
    shutil.move(str(src), str(dest))
    print(f"  [MOVED] {src.name} -> {dest_dir.name}/")


def get_dir_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def format_size(size: int) -> str:
    """Format size in human readable format."""
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024
    return f"{size_float:.1f} TB"


def main():
    print("=" * 70)
    print("DataLab Deep Cleanup & Organization")
    print("=" * 70)

    # Track changes
    actions = []

    # 1. Create organized directory structure
    print("\n[1] Creating organized directory structure...")
    dirs = {
        "config": DATA_DIR / "config",
        "extractions": DATA_DIR / "extractions",
        "vectors": DATA_DIR / "vectors",
        "cache": DATA_DIR / "cache",
    }
    for name, path in dirs.items():
        ensure_dir(path)
        print(f"  [DIR] {name}/")

    # 2. Organize top-level JSON config files
    print("\n[2] Organizing configuration files...")
    config_files = [
        "catalog.json",
        "catalog.yaml",
        "bench_index_params.json",
        "domain_classifications_v2.json",
        "discovered_assets.json",
    ]
    for filename in config_files:
        src = DATA_DIR / filename
        if src.exists():
            move_to(src, dirs["config"])
            actions.append(f"config/{filename}")

    # 3. Archive old domain_classifications v1
    print("\n[3] Archiving old versioned files...")
    old_versions = [
        "domain_classifications.json",  # v1, keep v2
    ]
    for filename in old_versions:
        src = DATA_DIR / filename
        if src.exists():
            archive_file(src, "old_versions")
            actions.append(f"archived: {filename}")

    # 4. Clean up datextract - check for empty or failed extractions
    print("\n[4] Cleaning datextract directory...")
    datextract = DATA_DIR / "datextract"
    if datextract.exists():
        for item in datextract.iterdir():
            if item.is_dir():
                # Check if it's a valid extraction (has raw/result.json)
                raw_result = item / "raw" / "result.json"
                if not raw_result.exists():
                    # Archive incomplete extractions
                    archive_directory(item, "incomplete_extractions")
                    actions.append(f"archived incomplete: {item.name}")
                else:
                    # Check size - if very small, probably failed
                    size = get_dir_size(item)
                    if size < 1000:  # Less than 1KB
                        archive_directory(item, "failed_extractions")
                        actions.append(f"archived failed: {item.name}")

    # 5. Consolidate extraction outputs
    print("\n[5] Consolidating extraction outputs...")

    # Move PROD_EXTRACTION_V2 to extractions/production/
    prod_v2 = DATA_DIR / "PROD_EXTRACTION_V2"
    if prod_v2.exists() and any(prod_v2.iterdir()):
        prod_dest = ensure_dir(dirs["extractions"] / "production")
        for item in prod_v2.iterdir():
            if item.is_dir():
                move_to(item, prod_dest)
                actions.append(f"extraction/production/{item.name}")
        # Remove empty PROD_EXTRACTION_V2 if empty
        if not any(prod_v2.iterdir()):
            prod_v2.rmdir()
            print(f"  [REMOVED] Empty PROD_EXTRACTION_V2/")

    # Move datextract valid extractions to extractions/staging/
    if datextract.exists():
        staging_dest = ensure_dir(dirs["extractions"] / "staging")
        for item in list(datextract.iterdir()):
            if item.is_dir() and (item / "raw" / "result.json").exists():
                move_to(item, staging_dest)
                actions.append(f"extraction/staging/{item.name}")
        # Remove empty datextract if empty
        if not any(datextract.iterdir()):
            datextract.rmdir()
            print(f"  [REMOVED] Empty datextract/")

    # 6. Organize vector/index data
    print("\n[6] Organizing vector and index data...")

    # Move indices to vectors/indices/
    indices_src = DATA_DIR / "indices"
    if indices_src.exists():
        indices_dest = ensure_dir(dirs["vectors"] / "indices")
        for item in indices_src.iterdir():
            if item.is_dir():
                move_to(item, indices_dest)
                actions.append(f"vectors/indices/{item.name}")
        if not any(indices_src.iterdir()):
            indices_src.rmdir()
            print(f"  [REMOVED] Empty indices/")

    # Move rag to vectors/rag/
    rag_src = DATA_DIR / "rag"
    if rag_src.exists():
        rag_dest = ensure_dir(dirs["vectors"] / "rag")
        for item in rag_src.iterdir():
            move_to(item, rag_dest)
            actions.append(f"vectors/rag/{item.name}")
        if not any(rag_src.iterdir()):
            rag_src.rmdir()
            print(f"  [REMOVED] Empty rag/")

    # 7. Organize metadata and auxiliary data
    print("\n[7] Organizing metadata and auxiliary data...")

    # Move metadata to cache/metadata/
    metadata_src = DATA_DIR / "metadata"
    if metadata_src.exists():
        metadata_dest = ensure_dir(dirs["cache"] / "metadata")
        for item in metadata_src.iterdir():
            move_to(item, metadata_dest)
            actions.append(f"cache/metadata/{item.name}")
        if not any(metadata_src.iterdir()):
            metadata_src.rmdir()
            print(f"  [REMOVED] Empty metadata/")

    # Move manifests to cache/manifests/
    manifests_src = DATA_DIR / "manifests"
    if manifests_src.exists():
        manifests_dest = ensure_dir(dirs["cache"] / "manifests")
        for item in manifests_src.iterdir():
            move_to(item, manifests_dest)
            actions.append(f"cache/manifests/{item.name}")
        if not any(manifests_src.iterdir()):
            manifests_src.rmdir()
            print(f"  [REMOVED] Empty manifests/")

    # 8. Clean up documentation files
    print("\n[8] Organizing documentation...")
    docs = DATA_DIR / "docs"
    ensure_dir(docs)

    doc_files = [
        "README.md",
        "SECURITY_FIXES_SUMMARY.md",
    ]
    for filename in doc_files:
        src = DATA_DIR / filename
        if src.exists():
            move_to(src, docs)
            actions.append(f"docs/{filename}")

    # Move notes to docs/notes/
    notes_src = DATA_DIR / "notes"
    if notes_src.exists():
        notes_dest = ensure_dir(docs / "notes")
        for item in notes_src.iterdir():
            move_to(item, notes_dest)
            actions.append(f"docs/notes/{item.name}")
        if not any(notes_src.iterdir()):
            notes_src.rmdir()
            print(f"  [REMOVED] Empty notes/")

    # 9. Move datalab_doc to docs/api/
    datalab_doc_src = DATA_DIR / "datalab_doc"
    if datalab_doc_src.exists():
        datalab_doc_dest = ensure_dir(docs / "api")
        for item in datalab_doc_src.iterdir():
            move_to(item, datalab_doc_dest)
            actions.append(f"docs/api/{item.name}")
        if not any(datalab_doc_src.iterdir()):
            datalab_doc_src.rmdir()
            print(f"  [REMOVED] Empty datalab_doc/")

    # 10. Clean up analysis directory
    print("\n[9] Cleaning up analysis directory...")
    analysis = DATA_DIR / "analysis"
    if analysis.exists():
        # Check if it has content, if so move to cache/analysis/
        if any(analysis.iterdir()):
            analysis_dest = ensure_dir(dirs["cache"] / "analysis")
            for item in list(analysis.iterdir()):
                move_to(item, analysis_dest)
                actions.append(f"cache/analysis/{item.name}")
        if not any(analysis.iterdir()):
            analysis.rmdir()
            print(f"  [REMOVED] Empty analysis/")

    # Summary
    print("\n" + "=" * 70)
    print("Cleanup Summary")
    print("=" * 70)
    print(f"\nActions taken: {len(actions)}")
    print(f"\nNew structure:")

    # Show new directory tree
    for root, dirs, files in os.walk(DATA_DIR):
        level = root.replace(str(DATA_DIR), "").count(os.sep)
        indent = "  " * level
        relpath = Path(root).relative_to(DATA_DIR)
        if str(relpath) == ".":
            print(f"data/")
        else:
            # Skip _archive in display
            if "_archive" in str(relpath):
                continue
            print(f"{indent}{relpath.name}/")

        if level >= 2:  # Limit depth
            continue

        subindent = "  " * (level + 1)
        for file in sorted(files)[:5]:  # Limit files shown
            size = format_size((Path(root) / file).stat().st_size)
            print(f"{subindent}{file} ({size})")
        if len(files) > 5:
            print(f"{subindent}... and {len(files) - 5} more files")

    print(f"\nArchive location: {ARCHIVE_DIR}/")
    archive_size = get_dir_size(ARCHIVE_DIR)
    print(f"Archive size: {format_size(archive_size)}")


if __name__ == "__main__":
    main()

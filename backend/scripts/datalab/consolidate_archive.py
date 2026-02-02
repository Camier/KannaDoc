#!/usr/bin/env python3
"""
Archive consolidation script for DataLab extraction pipeline.
Moves old extractions, test data, and bloated outputs to structured archive.
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

ROOT = Path("/LAB/@thesis/datalab")
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "_archive"


def calculate_sha256_file(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_manifest(name: str, source: Path, dest: Path) -> Dict[str, Any]:
    """Create manifest for archived data."""
    manifest = {
        "name": name,
        "source_path": str(source),
        "archive_path": str(dest),
        "archived_at": datetime.utcnow().isoformat() + "Z",
        "items": [],
    }

    if source.is_dir():
        total_size = 0
        file_count = 0

        for item in source.rglob("*"):
            if item.is_file():
                size = item.stat().st_size
                total_size += size
                file_count += 1

                # Only hash smaller files (< 10MB)
                if size < 10 * 1024 * 1024:
                    sha256 = calculate_sha256_file(item)
                else:
                    sha256 = "<large_file>"

                manifest["items"].append(
                    {
                        "path": str(item.relative_to(source)),
                        "size": size,
                        "sha256": sha256,
                    }
                )

        manifest["total_size_bytes"] = total_size
        manifest["file_count"] = file_count

    return manifest


def archive_directory(name: str, source: Path, dest: Path) -> Optional[Dict[str, Any]]:
    """Archive a directory with manifest."""
    print(f"[ARCHIVE] {name}")
    print(f"  Source: {source}")
    print(f"  Destination: {dest}")

    if not source.exists():
        print(f"  [SKIP] Source does not exist")
        return None

    # Create destination
    dest.mkdir(parents=True, exist_ok=True)

    # Create manifest before moving
    manifest = create_manifest(name, source, dest)

    # Move contents
    if source.is_dir():
        for item in source.iterdir():
            dest_item = dest / item.name
            if dest_item.exists():
                print(f"  [WARN] Destination exists, skipping: {item.name}")
                continue
            shutil.move(str(item), str(dest_item))
            print(f"  [MOVED] {item.name}")

    # Write manifest
    manifest_path = (
        ARCHIVE_DIR
        / "manifests"
        / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  [MANIFEST] {manifest_path}")
    print(
        f"  [STATS] {manifest.get('file_count', 0)} files, {manifest.get('total_size_bytes', 0) / (1024**2):.1f} MB"
    )

    return manifest


def main():
    print("=" * 70)
    print("DataLab Deep Consolidation - Archive Phase")
    print("=" * 70)

    results = {}

    # Archive 1: TEST EXTRACT (1.1G of test data)
    test_extract = DATA_DIR / "TEST EXTRACT"
    if test_extract.exists():
        results["test_extract"] = archive_directory(
            "test_extract_20260131",
            test_extract,
            ARCHIVE_DIR / "by_type" / "test_extractions" / "20260131_test_extract",
        )
        # Remove empty source directory
        if test_extract.exists() and not any(test_extract.iterdir()):
            test_extract.rmdir()
            print(f"  [REMOVED] Empty source directory")

    print()

    # Archive 2: Partial extractions from datextract
    datextract = DATA_DIR / "datextract"
    if datextract.exists():
        # Keep only the most recent 3 extractions, archive the rest
        if datextract.is_dir():
            items = sorted(
                datextract.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
            )
            recent = items[:3]
            old = items[3:]

            if old:
                old_dir = (
                    ARCHIVE_DIR / "by_type" / "partial_extractions" / "datextract_old"
                )
                old_dir.mkdir(parents=True, exist_ok=True)

                for item in old:
                    dest_item = old_dir / item.name
                    if dest_item.exists():
                        print(f"  [SKIP] Already archived: {item.name}")
                        continue
                    shutil.move(str(item), str(dest_item))
                    print(f"  [MOVED] {item.name}")

    print()
    print("=" * 70)
    print("Consolidation Complete")
    print("=" * 70)

    # Print summary
    total_archived = sum(
        r.get("total_size_bytes", 0) for r in results.values() if r
    ) / (1024**3)

    print(f"\nTotal archived: {total_archived:.2f} GB")
    print(f"Archive location: {ARCHIVE_DIR}")
    print(f"\nManifests stored in: {ARCHIVE_DIR / 'manifests'}")


if __name__ == "__main__":
    main()

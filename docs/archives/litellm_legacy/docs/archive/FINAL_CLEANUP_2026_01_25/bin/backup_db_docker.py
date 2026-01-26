#!/usr/bin/env python3
"""
LiteLLM Database Backup Script (Docker)

Performs automated backups of Docker-deployed LiteLLM:
- PostgreSQL database (via docker exec)
- Configuration files
- Manifest with checksums

Retention Policy:
- 7 daily backups
- 4 weekly backups (Sunday)
- 3 monthly backups (1st of month)

Usage:
    python bin/backup_db_docker.py [--dry-run]
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path("/LAB/@litellm")
BACKUP_ROOT = PROJECT_ROOT / "state" / "archive" / "backups"
DB_CONTAINER = "litellm-postgres"
DB_USER = "litellm"
DB_NAME = "litellm"

CONFIG_FILES = [
    "config.yaml",
    "docker-compose.yml",
    ".env",
    "schema.prisma",
]

# Retention settings
DAILY_RETENTION = 7
WEEKLY_RETENTION = 4
MONTHLY_RETENTION = 3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def run_command(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)."""
    logger.debug(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )
    return result.returncode, result.stdout, result.stderr


def backup_database(backup_path: Path, dry_run: bool = False) -> bool:
    """Backup PostgreSQL database via docker exec."""
    logger.info(f"Backing up database to {backup_path}")

    if dry_run:
        logger.info("[DRY-RUN] Would backup database")
        return True

    # Ensure container is running
    code, _, err = run_command(["docker", "inspect", "-f", "{{.State.Running}}", DB_CONTAINER])
    if code != 0 or "true" not in _:
        logger.error(f"Container {DB_CONTAINER} is not running")
        return False

    # Run pg_dump via docker exec
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "pg_dump", "-U", DB_USER, "-d", DB_NAME, "--no-owner", "--no-acl"
    ]

    code, stdout, err = run_command(cmd, check=False)
    if code != 0:
        logger.error(f"Database backup failed: {err}")
        return False

    backup_path.write_text(stdout)
    logger.info(f"Database backup complete: {backup_path.stat().st_size} bytes")
    return True


def backup_configs(backup_dir: Path, dry_run: bool = False) -> bool:
    """Backup configuration files."""
    logger.info("Backing up configuration files")

    for filename in CONFIG_FILES:
        src = PROJECT_ROOT / filename
        if not src.exists():
            logger.warning(f"Config file not found: {filename}")
            continue

        if dry_run:
            logger.info(f"[DRY-RUN] Would copy {filename}")
            continue

        dst = backup_dir / filename
        dst.write_text(src.read_text())
        logger.info(f"Backed up: {filename}")

    return True


def create_manifest(backup_dir: Path, dry_run: bool = False) -> bool:
    """Create backup manifest with checksums."""
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "hostname": os.uname().nodename,
        "files": {}
    }

    for file in backup_dir.glob("*"):
        if file.name == "manifest.json":
            continue

        content = file.read_bytes()
        manifest["files"][file.name] = {
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        }

    if dry_run:
        logger.info(f"[DRY-RUN] Would create manifest")
        return True

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Created manifest: {manifest_path}")
    return True


def cleanup_old_backups(dry_run: bool = False) -> None:
    """Remove old backups based on retention policy."""
    if not BACKUP_ROOT.exists():
        return

    logger.info("Checking for old backups to clean up...")

    # List all backups by date
    backups = sorted(BACKUP_ROOT.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

    # Categorize by type
    daily_backups = [b for b in backups if not b.name.startswith(("weekly-", "monthly-"))]
    weekly_backups = sorted([b for b in backups if b.name.startswith("weekly-")], key=lambda p: p.stat().mtime, reverse=True)
    monthly_backups = sorted([b for b in backups if b.name.startswith("monthly-")], key=lambda p: p.stat().mtime, reverse=True)

    # Remove excess daily backups
    for old in daily_backups[DAILY_RETENTION:]:
        if dry_run:
            logger.info(f"[DRY-RUN] Would remove old daily backup: {old.name}")
        else:
            logger.info(f"Removing old daily backup: {old.name}")
            subprocess.run(["rm", "-rf", str(old)], check=False)

    # Remove excess weekly backups
    for old in weekly_backups[WEEKLY_RETENTION:]:
        if dry_run:
            logger.info(f"[DRY-RUN] Would remove old weekly backup: {old.name}")
        else:
            logger.info(f"Removing old weekly backup: {old.name}")
            subprocess.run(["rm", "-rf", str(old)], check=False)

    # Remove excess monthly backups
    for old in monthly_backups[MONTHLY_RETENTION:]:
        if dry_run:
            logger.info(f"[DRY-RUN] Would remove old monthly backup: {old.name}")
        else:
            logger.info(f"Removing old monthly backup: {old.name}")
            subprocess.run(["rm", "-rf", str(old)], check=False)


def main():
    parser = argparse.ArgumentParser(description="Backup LiteLLM Docker database and configs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")

    # Create backup directory
    now = datetime.now()
    backup_type = "monthly" if now.day == 1 else ("weekly" if now.weekday() == 6 else "daily")
    backup_name = f"{backup_type}-{now.strftime('%Y%m%d-%H%M%S')}"
    backup_dir = BACKUP_ROOT / backup_name

    if args.dry_run:
        logger.info(f"[DRY-RUN] Would create backup directory: {backup_dir}")
    else:
        backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created backup directory: {backup_dir}")

    # Backup database
    db_backup = backup_dir / "database.sql"
    if not backup_database(db_backup, args.dry_run):
        logger.error("Database backup failed")
        return 1

    # Backup configs
    if not backup_configs(backup_dir, args.dry_run):
        logger.warning("Config backup had issues")

    # Create manifest
    if not create_manifest(backup_dir, args.dry_run):
        logger.warning("Manifest creation failed")

    # Cleanup old backups
    cleanup_old_backups(args.dry_run)

    if args.dry_run:
        logger.info("=== DRY RUN COMPLETE - No changes made ===")
    else:
        logger.info(f"Backup complete: {backup_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

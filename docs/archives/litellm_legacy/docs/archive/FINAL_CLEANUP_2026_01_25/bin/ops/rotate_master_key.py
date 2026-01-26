#!/usr/bin/env python3
"""
LiteLLM Master Key Rotation Script

This script performs a secure rotation of the LiteLLM master key:
1. Generates a new secure master key
2. Updates ~/.007 with the new key
3. Updates the LiteLLM_VerificationToken table in PostgreSQL
4. Provides restart commands for the service

IMPORTANT: Keep the NEW master key secure! Do not commit to version control.
"""

import secrets
import subprocess
import sys
from pathlib import Path
from typing import Tuple

# Configuration
DOT_007_PATH = Path.home() / ".007"
ENV_LITELLM_PATH = Path("/LAB/@litellm/env.litellm")
DATABASE_URL = "<DATABASE_URL>"  # Must be configured via environment or command line
OLD_MASTER_KEY = "<OLD_MASTER_KEY>"  # Must be configured before running

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_step(step: int, text: str) -> None:
    """Print a step indicator."""
    print(f"{GREEN}[{step}]{RESET} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}WARNING: {text}{RESET}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{RED}ERROR: {text}{RESET}")


def generate_master_key() -> str:
    """Generate a new secure master key using secrets module."""
    token = secrets.token_urlsafe(32)
    return f"sk-{token}"


def check_db_connection() -> bool:
    """Check if PostgreSQL database is accessible."""
    try:
        result = subprocess.run(
            ["psql", DATABASE_URL, "-c", "SELECT 1"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_current_master_keys() -> list[str]:
    """Get current master keys from the database."""
    query = """
    SELECT token
    FROM "LiteLLM_VerificationToken"
    WHERE token LIKE 'sk-%'
    ORDER BY created_at DESC;
    """
    try:
        result = subprocess.run(
            ["psql", DATABASE_URL, "-t", "-c", query],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            keys = [line.strip() for line in result.stdout.split("\n") if line.strip()]
            return keys
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def update_007_file(new_key: str, new_salt: str) -> bool:
    """
    Update ~/.007 file with new master key and salt.

    Returns True if successful, False otherwise.
    """
    print_step(2, f"Updating {DOT_007_PATH} with new master key")

    if not DOT_007_PATH.exists():
        print_error(f"File not found: {DOT_007_PATH}")
        return False

    # Read current content
    content = DOT_007_PATH.read_text()
    lines = content.split("\n")

    # Update or add keys
    updated_lines = []
    master_key_updated = False
    salt_key_updated = False

    for line in lines:
        if line.startswith("export LITELLM_MASTER_KEY="):
            updated_lines.append(f'export LITELLM_MASTER_KEY="{new_key}"')
            master_key_updated = True
        elif line.startswith("export LITELLM_SALT_KEY="):
            updated_lines.append(f'export LITELLM_SALT_KEY="{new_salt}"')
            salt_key_updated = True
        elif line.startswith("export LITELLM_SMOKE_TEST_KEY="):
            updated_lines.append(f'export LITELLM_SMOKE_TEST_KEY="{new_key}"')
        elif line.startswith("export LITELLM_HEALTH_API_KEY="):
            updated_lines.append(f'export LITELLM_HEALTH_API_KEY="{new_key}"')
        elif line.startswith("export LITELLM_PROXY_API_KEY="):
            updated_lines.append(f'export LITELLM_PROXY_API_KEY="{new_key}"')
        else:
            updated_lines.append(line)

    # Add keys if not present
    if not master_key_updated:
        updated_lines.append(f'export LITELLM_MASTER_KEY="{new_key}"')
    if not salt_key_updated:
        updated_lines.append(f'export LITELLM_SALT_KEY="{new_salt}"')

    # Write back
    new_content = "\n".join(updated_lines)
    DOT_007_PATH.write_text(new_content)

    print(f"  {GREEN}✓{RESET} Updated {DOT_007_PATH}")
    return True


def update_database_keys(old_key: str, new_key: str) -> bool:
    """
    Update the LiteLLM_VerificationToken table with the new master key.

    This preserves all existing key configurations while updating the token value.
    """
    print_step(3, "Updating LiteLLM database with new master key")

    # Check if the old key exists
    check_query = f"""
    SELECT token, key_name, key_alias
    FROM "LiteLLM_VerificationToken"
    WHERE token = '{old_key}';
    """

    try:
        result = subprocess.run(
            ["psql", DATABASE_URL, "-t", "-c", check_query],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if old_key not in result.stdout:
            print_warning(f"Old master key '{old_key}' not found in database")
            print("  Skipping database update (key may have already been rotated)")
            return True

        # Update the master key
        update_query = f"""
        UPDATE "LiteLLM_VerificationToken"
        SET token = '{new_key}',
            updated_at = NOW(),
            rotation_count = COALESCE(rotation_count, 0) + 1,
            last_rotation_at = NOW()
        WHERE token = '{old_key}';
        """

        result = subprocess.run(
            ["psql", DATABASE_URL, "-c", update_query],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print(f"  {GREEN}✓{RESET} Database updated successfully")
            return True
        else:
            print_error(f"Database update failed: {result.stderr}")
            return False

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print_error(f"Database command failed: {e}")
        return False


def print_migration_summary(new_key: str, new_salt: str) -> None:
    """Print a summary of the migration and next steps."""
    print_header("MIGRATION SUMMARY")

    print(f"{GREEN}NEW MASTER KEY:{RESET} {new_key}")
    print(f"{GREEN}NEW SALT KEY:{RESET}  {new_salt}")
    print()
    print_warning("Keep these keys secure! Do not share or commit to version control.")
    print()

    print_header("NEXT STEPS")

    print_step(1, "Restart the LiteLLM service to load the new keys:")
    print()
    print("  sudo systemctl restart litellm.service")
    print()

    print_step(2, "Verify the service is running:")
    print()
    print("  sudo systemctl status litellm.service")
    print("  curl -H 'Authorization: Bearer <NEW_KEY>' http://127.0.0.1:4000/healthz")
    print()

    print_step(3, "Check logs for any issues:")
    print()
    print("  sudo journalctl -u litellm.service -f")
    print()

    print_warning("If you have any applications using the old master key, update them now!")
    print()


def main() -> int:
    """Main entry point for the key rotation script."""
    print_header("LiteLLM Master Key Rotation")

    # Step 1: Generate new keys
    print_step(1, "Generating new secure master key and salt")
    new_master_key = generate_master_key()
    new_salt_key = generate_master_key()
    print(f"  {GREEN}✓{RESET} New master key generated")
    print(f"  {GREEN}✓{RESET} New salt key generated")

    # Step 2: Check database connection
    if not check_db_connection():
        print_error("Cannot connect to PostgreSQL database")
        print(f"  Ensure DATABASE_URL is correct: {DATABASE_URL}")
        return 1

    print(f"  {GREEN}✓{RESET} Database connection verified")

    # Step 3: Show current keys in database
    current_keys = get_current_master_keys()
    if current_keys:
        print(f"\n  Found {len(current_keys)} key(s) in database:")
        for key in current_keys[:5]:  # Show first 5
            masked = key[:8] + "*" * (len(key) - 12) + key[-4:]
            print(f"    - {masked}")

    # Step 4: Update ~/.007
    if not update_007_file(new_master_key, new_salt_key):
        print_error("Failed to update ~/.007 file")
        return 1

    # Step 5: Update database
    if not update_database_keys(OLD_MASTER_KEY, new_master_key):
        print_error("Failed to update database")
        print_warning("You may need to manually update the database")
        print(f"  Old key: {OLD_MASTER_KEY}")
        print(f"  New key: {new_master_key}")
        return 1

    # Step 6: Print summary
    print_migration_summary(new_master_key, new_salt_key)

    return 0


if __name__ == "__main__":
    sys.exit(main())

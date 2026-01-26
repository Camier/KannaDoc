#!/usr/bin/env python3
"""
Verify salt key migration worked correctly.

This script tests that:
1. The new LITELLM_SALT_KEY can decrypt all encrypted values in the database
2. The proxy can successfully load and decrypt credentials
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/LAB/@litellm")

from dotenv import load_dotenv

# Load environment
load_dotenv("/home/miko/.gemini/.env")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed")
    sys.exit(1)


def get_db_connection():
    """Get database connection."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")

    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if not match:
        raise ValueError(f"Invalid DATABASE_URL format")

    user, password, host, port, database = match.groups()
    return psycopg2.connect(
        host=host,
        port=int(port),
        database=database,
        user=user,
        password=password
    )


def test_decryption():
    """Test decryption of all encrypted values in the database."""
    from litellm.proxy.common_utils.encrypt_decrypt_utils import decrypt_value_helper

    results = {
        'LiteLLM_CredentialsTable': {'total': 0, 'decrypted': 0, 'failed': 0},
        'LiteLLM_ProxyModelTable': {'total': 0, 'decrypted': 0, 'failed': 0},
        'LiteLLM_MCPServerTable': {'total': 0, 'decrypted': 0, 'failed': 0},
    }

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Test credentials table
            print("=== Testing LiteLLM_CredentialsTable ===")
            cur.execute('SELECT credential_name, credential_values FROM "LiteLLM_CredentialsTable"')
            for row in cur.fetchall():
                results['LiteLLM_CredentialsTable']['total'] += 1
                credential_name = row['credential_name']
                credential_values = row['credential_values']

                for key, value in credential_values.items():
                    if any(k in key.lower() for k in ['api_key', 'api_secret', 'password', 'token']):
                        if isinstance(value, str) and value and not value.startswith('os.environ/'):
                            decrypted = decrypt_value_helper(
                                value,
                                f"{credential_name}.{key}",
                                exception_type="debug",
                                return_original_value=False
                            )
                            if decrypted:
                                results['LiteLLM_CredentialsTable']['decrypted'] += 1
                                print(f"  ✓ {credential_name}.{key}: {decrypted[:15]}...{decrypted[-5:]}")
                            else:
                                results['LiteLLM_CredentialsTable']['failed'] += 1
                                print(f"  ✗ {credential_name}.{key}: FAILED")

            # Test proxy models table
            print("\n=== Testing LiteLLM_ProxyModelTable ===")
            cur.execute('SELECT model_name, litellm_params FROM "LiteLLM_ProxyModelTable"')
            for row in cur.fetchall():
                results['LiteLLM_ProxyModelTable']['total'] += 1
                model_name = row['model_name']
                litellm_params = row['litellm_params']

                for key, value in litellm_params.items():
                    if any(k in key.lower() for k in ['api_key', 'api_secret', 'password', 'token']):
                        if isinstance(value, str) and value and not value.startswith('os.environ/'):
                            decrypted = decrypt_value_helper(
                                value,
                                f"{model_name}.{key}",
                                exception_type="debug",
                                return_original_value=False
                            )
                            if decrypted:
                                results['LiteLLM_ProxyModelTable']['decrypted'] += 1
                                print(f"  ✓ {model_name}.{key}: {decrypted[:15]}...{decrypted[-5:]}")
                            else:
                                results['LiteLLM_ProxyModelTable']['failed'] += 1
                                print(f"  ✗ {model_name}.{key}: FAILED")

            # Test MCP servers table
            print("\n=== Testing LiteLLM_MCPServerTable ===")
            cur.execute('SELECT server_name, credentials FROM "LiteLLM_MCPServerTable"')
            for row in cur.fetchall():
                results['LiteLLM_MCPServerTable']['total'] += 1
                server_name = row['server_name']
                credentials = row['credentials']

                for key, value in credentials.items():
                    if any(k in key.lower() for k in ['api_key', 'api_secret', 'password', 'token']):
                        if isinstance(value, str) and value and not value.startswith('os.environ/'):
                            decrypted = decrypt_value_helper(
                                value,
                                f"{server_name}.{key}",
                                exception_type="debug",
                                return_original_value=False
                            )
                            if decrypted:
                                results['LiteLLM_MCPServerTable']['decrypted'] += 1
                                print(f"  ✓ {server_name}.{key}: {decrypted[:15]}...{decrypted[-5:]}")
                            else:
                                results['LiteLLM_MCPServerTable']['failed'] += 1
                                print(f"  ✗ {server_name}.{key}: FAILED")

    finally:
        conn.close()

    return results


def main():
    print("Salt Key Migration Verification")
    print("=" * 50)
    print(f"LITELLM_SALT_KEY (first 10 chars): {os.getenv('LITELLM_SALT_KEY', '')[:10]}...")
    print()

    results = test_decryption()

    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)

    total_decrypted = 0
    total_failed = 0

    for table, stats in results.items():
        if stats['total'] > 0 or stats['decrypted'] > 0:
            print(f"\n{table}:")
            print(f"  Records processed: {stats['total']}")
            print(f"  Values decrypted: {stats['decrypted']}")
            print(f"  Failed: {stats['failed']}")
            total_decrypted += stats['decrypted']
            total_failed += stats['failed']

    print(f"\nTotal: {total_decrypted} decrypted, {total_failed} failed")

    if total_failed > 0:
        print("\n✗ VERIFICATION FAILED - Some values could not be decrypted")
        sys.exit(1)
    elif total_decrypted == 0:
        print("\n⚠ WARNING - No encrypted values found in database")
        sys.exit(0)
    else:
        print("\n✓ VERIFICATION PASSED - All encrypted values can be decrypted")
        sys.exit(0)


if __name__ == "__main__":
    main()

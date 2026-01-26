#!/usr/bin/env python3
"""
LiteLLM Salt Key Migration Script

This script handles rotation of LITELLM_SALT_KEY by:
1. Using the OLD key to decrypt all encrypted values
2. Re-encrypting all values with the NEW key
3. Updating the database in a safe transaction

Security: This script requires both OLD and NEW salt keys to be set in environment.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import nacl.secret
import nacl.utils
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, "/LAB/@litellm")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)


def get_32_byte_key(signing_key: str) -> bytes:
    """Convert signing key to 32-byte hash for NaCl SecretBox."""
    hash_object = hashlib.sha256(signing_key.encode())
    return hash_object.digest()


def encrypt_value(value: str, signing_key: str) -> str:
    """Encrypt a string value using NaCl SecretBox."""
    if not value:
        return value

    hash_bytes = get_32_byte_key(signing_key)
    box = nacl.secret.SecretBox(hash_bytes)
    value_bytes = value.encode("utf-8")
    encrypted = box.encrypt(value_bytes)
    # URL-safe base64 encoding
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_value(value: str, signing_key: str) -> Optional[str]:
    """Decrypt a string value using NaCl SecretBox."""
    if not value:
        return value

    try:
        hash_bytes = get_32_byte_key(signing_key)
        box = nacl.secret.SecretBox(hash_bytes)

        # Try URL-safe base64 decoding first (new format)
        try:
            decoded_b64 = base64.urlsafe_b64decode(value)
        except Exception:
            # Fall back to standard base64 decoding for backwards compatibility
            decoded_b64 = base64.b64decode(value)

        plaintext = box.decrypt(decoded_b64)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


def reencrypt_jsonb_value(
    data: Dict[str, Any],
    old_key: str,
    new_key: str,
    encrypted_keys: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Re-encrypt encrypted values within a JSONB object.

    Args:
        data: The JSONB object as a dict
        old_key: Old salt key for decryption
        new_key: New salt key for encryption
        encrypted_keys: List of keys known to be encrypted (e.g., ['api_key'])

    Returns:
        Tuple of (updated_dict, count_of_reencrypted_values)
    """
    if encrypted_keys is None:
        encrypted_keys = ['api_key', 'api_secret', 'password', 'token']

    updated_data = {}
    reencrypted_count = 0

    for key, value in data.items():
        # Check if this key should be re-encrypted
        should_encrypt = any(encrypted_key in key.lower() for encrypted_key in encrypted_keys)

        if should_encrypt and isinstance(value, str):
            try:
                # Try to decrypt with old key and re-encrypt with new key
                decrypted = decrypt_value(value, old_key)
                if decrypted is not None:
                    updated_data[key] = encrypt_value(decrypted, new_key)
                    reencrypted_count += 1
                else:
                    # Keep original if decryption returns None
                    updated_data[key] = value
            except Exception:
                # If decryption fails, it might not be encrypted - keep as is
                updated_data[key] = value
        else:
            updated_data[key] = value

    return updated_data, reencrypted_count


def get_db_connection() -> Any:
    """Get database connection from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set in environment")

    # Parse PostgreSQL connection string
    # Format: postgresql://user:password@host:port/database
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if not match:
        raise ValueError(f"Invalid DATABASE_URL format: {database_url}")

    user, password, host, port, database = match.groups()

    return psycopg2.connect(
        host=host,
        port=int(port),
        database=database,
        user=user,
        password=password
    )


def migrate_credentials_table(conn: Any, old_key: str, new_key: str) -> Dict[str, Any]:
    """Migrate all credentials in LiteLLM_CredentialsTable."""
    results = {
        'table': 'LiteLLM_CredentialsTable',
        'total_records': 0,
        'reencrypted': 0,
        'errors': []
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get all credentials
        cur.execute('SELECT credential_id, credential_values FROM "LiteLLM_CredentialsTable"')
        records = cur.fetchall()
        results['total_records'] = len(records)

        for record in records:
            try:
                credential_id = record['credential_id']
                credential_values = record['credential_values']

                if credential_values:
                    # Re-encrypt the credential values
                    updated_values, count = reencrypt_jsonb_value(
                        credential_values, old_key, new_key
                    )
                    results['reencrypted'] += count

                    # Update the record
                    cur.execute(
                        'UPDATE "LiteLLM_CredentialsTable" SET credential_values = %s WHERE credential_id = %s',
                        (json.dumps(updated_values), credential_id)
                    )

            except Exception as e:
                results['errors'].append({
                    'credential_id': record.get('credential_id'),
                    'error': str(e)
                })

    return results


def migrate_proxy_models_table(conn: Any, old_key: str, new_key: str) -> Dict[str, Any]:
    """Migrate all model params in LiteLLM_ProxyModelTable."""
    results = {
        'table': 'LiteLLM_ProxyModelTable',
        'total_records': 0,
        'reencrypted': 0,
        'errors': []
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get all models
        cur.execute('SELECT model_id, model_name, litellm_params FROM "LiteLLM_ProxyModelTable"')
        records = cur.fetchall()
        results['total_records'] = len(records)

        for record in records:
            try:
                model_id = record['model_id']
                model_name = record['model_name']
                litellm_params = record['litellm_params']

                if litellm_params:
                    # Re-encrypt the litellm_params
                    updated_params, count = reencrypt_jsonb_value(
                        litellm_params, old_key, new_key
                    )
                    results['reencrypted'] += count

                    # Update the record
                    cur.execute(
                        'UPDATE "LiteLLM_ProxyModelTable" SET litellm_params = %s WHERE model_id = %s',
                        (json.dumps(updated_params), model_id)
                    )

            except Exception as e:
                results['errors'].append({
                    'model_id': record.get('model_id'),
                    'model_name': record.get('model_name'),
                    'error': str(e)
                })

    return results


def migrate_mcp_servers_table(conn: Any, old_key: str, new_key: str) -> Dict[str, Any]:
    """Migrate all MCP server credentials."""
    results = {
        'table': 'LiteLLM_MCPServerTable',
        'total_records': 0,
        'reencrypted': 0,
        'errors': []
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get all MCP servers
        cur.execute('SELECT server_id, server_name, credentials FROM "LiteLLM_MCPServerTable"')
        records = cur.fetchall()
        results['total_records'] = len(records)

        for record in records:
            try:
                server_id = record['server_id']
                server_name = record['server_name']
                credentials = record['credentials']

                if credentials:
                    # Re-encrypt the credentials
                    updated_credentials, count = reencrypt_jsonb_value(
                        credentials, old_key, new_key
                    )
                    results['reencrypted'] += count

                    # Update the record
                    cur.execute(
                        'UPDATE "LiteLLM_MCPServerTable" SET credentials = %s WHERE server_id = %s',
                        (json.dumps(updated_credentials), server_id)
                    )

            except Exception as e:
                results['errors'].append({
                    'server_id': record.get('server_id'),
                    'server_name': record.get('server_name'),
                    'error': str(e)
                })

    return results


def main():
    """Main migration function."""
    # Load environment
    load_dotenv("/LAB/@litellm/env.litellm")

    # Get old and new salt keys
    old_key = os.getenv("LITELLM_SALT_KEY_OLD")
    new_key = os.getenv("LITELLM_SALT_KEY")

    if not old_key:
        print("ERROR: LITELLM_SALT_KEY_OLD not set in environment")
        print("Usage: LITELLM_SALT_KEY_OLD='<old_key>' LITELLM_SALT_KEY='<new_key>' python3 migrate_salt_key.py")
        sys.exit(1)

    if not new_key:
        print("ERROR: LITELLM_SALT_KEY not set in environment")
        sys.exit(1)

    if old_key == new_key:
        print("ERROR: Old and new keys are identical. No migration needed.")
        sys.exit(1)

    print(f"Starting salt key migration...")
    print(f"Old key (first 10 chars): {old_key[:10]}...")
    print(f"New key (first 10 chars): {new_key[:10]}...")

    # Test encryption/decryption before proceeding
    test_value = "test_api_key_12345"
    try:
        encrypted = encrypt_value(test_value, old_key)
        decrypted = decrypt_value(encrypted, old_key)
        assert decrypted == test_value
        print(f"✓ Encryption/decryption test with OLD key passed")

        # Test new key
        encrypted_new = encrypt_value(test_value, new_key)
        decrypted_new = decrypt_value(encrypted_new, new_key)
        assert decrypted_new == test_value
        print(f"✓ Encryption/decryption test with NEW key passed")

        # Test re-encryption
        reencrypted = encrypt_value(decrypted, new_key)
        redecrypted = decrypt_value(reencrypted, new_key)
        assert redecrypted == test_value
        print(f"✓ Re-encryption test (OLD->NEW) passed")

    except Exception as e:
        print(f"ERROR: Encryption test failed: {e}")
        sys.exit(1)

    # Connect to database
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transactions
        print(f"✓ Connected to database")
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        sys.exit(1)

    # Run migrations
    all_results = []

    try:
        with conn:
            # Migrate credentials table
            print("\n--- Migrating LiteLLM_CredentialsTable ---")
            results = migrate_credentials_table(conn, old_key, new_key)
            all_results.append(results)
            print(f"  Total records: {results['total_records']}")
            print(f"  Re-encrypted values: {results['reencrypted']}")
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")

            # Migrate proxy models table
            print("\n--- Migrating LiteLLM_ProxyModelTable ---")
            results = migrate_proxy_models_table(conn, old_key, new_key)
            all_results.append(results)
            print(f"  Total records: {results['total_records']}")
            print(f"  Re-encrypted values: {results['reencrypted']}")
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")

            # Migrate MCP servers table
            print("\n--- Migrating LiteLLM_MCPServerTable ---")
            results = migrate_mcp_servers_table(conn, old_key, new_key)
            all_results.append(results)
            print(f"  Total records: {results['total_records']}")
            print(f"  Re-encrypted values: {results['reencrypted']}")
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")

            # Commit transaction
            conn.commit()
            print("\n✓ Migration completed successfully - transaction committed")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed - transaction rolled back")
        print(f"Error: {e}")
        sys.exit(1)

    # Print summary
    print("\n" + "=" * 50)
    print("MIGRATION SUMMARY")
    print("=" * 50)
    total_reencrypted = sum(r['reencrypted'] for r in all_results)
    total_errors = sum(len(r['errors']) for r in all_results)

    for result in all_results:
        print(f"\n{result['table']}:")
        print(f"  Records: {result['total_records']}")
        print(f"  Re-encrypted: {result['reencrypted']}")

    print(f"\nTotal values re-encrypted: {total_reencrypted}")
    print(f"Total errors: {total_errors}")

    if total_errors > 0:
        print("\nErrors encountered:")
        for result in all_results:
            if result['errors']:
                print(f"\n{result['table']}:")
                for error in result['errors']:
                    print(f"  - {error}")

    print("\n✓ Salt key migration complete!")
    print(f"  Please update your LITELLM_SALT_KEY to: {new_key[:20]}...")


if __name__ == "__main__":
    main()

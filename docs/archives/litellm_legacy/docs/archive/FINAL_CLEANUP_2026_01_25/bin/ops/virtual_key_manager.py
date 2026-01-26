#!/usr/bin/env python3
"""
Virtual Key Manager for LiteLLM
Usage: python3 bin/ops/virtual_key_manager.py [create|list|delete] [args]
"""

import os
import sys
import requests
import json
import argparse
from tabulate import tabulate  # Requires pip install tabulate, usually in container

BASE_URL = "http://127.0.0.1:4000"
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY")

if not MASTER_KEY:
    print("❌ Error: LITELLM_MASTER_KEY not found in environment.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {MASTER_KEY}",
    "Content-Type": "application/json"
}

def create_key(alias, budget=None, models=None):
    url = f"{BASE_URL}/key/generate"
    payload = {
        "key_alias": alias,
        "duration": "inf"  # Infinite duration by default
    }
    if budget:
        payload["max_budget"] = float(budget)
    if models:
        payload["models"] = models.split(",")

    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"\n✅ Key Created Successfully!")
        print(f"Alias: {data.get('key_alias')}")
        print(f"Key:   {data.get('key')}")  # This is the only time you see the full key
        print(f"Info:  Save this key securely. It maps to your Master Key privileges unless restricted.\n")
    except Exception as e:
        print(f"❌ Error creating key: {e}")
        if hasattr(e, 'response'):
            print(e.response.text)

def list_keys():
    url = f"{BASE_URL}/key/list"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        # Prepare table
        table = []
        for key in data.get("keys", []):
            table.append([
                key.get("key_alias", "N/A"),
                key.get("token", "")[:10] + "...",
                key.get("spend", 0.0),
                key.get("max_budget", "None")
            ])
        
        print("\n🔑 Active Virtual Keys")
        print(tabulate(table, headers=["Alias", "Prefix", "Spend ($)", "Budget"], tablefmt="simple"))
        print()
        
    except Exception as e:
        print(f"❌ Error listing keys: {e}")

def main():
    parser = argparse.ArgumentParser(description="LiteLLM Key Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create
    create_parser = subparsers.add_parser("create", help="Create a new key")
    create_parser.add_argument("alias", help="Human readable name (e.g. 'vscode')")
    create_parser.add_argument("--budget", help="Max budget in USD (optional)")
    create_parser.add_argument("--models", help="Comma-separated list of allowed models (optional)")

    # List
    subparsers.add_parser("list", help="List all keys")

    args = parser.parse_args()

    if args.command == "create":
        create_key(args.alias, args.budget, args.models)
    elif args.command == "list":
        list_keys()

if __name__ == "__main__":
    main()

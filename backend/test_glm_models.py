#!/usr/bin/env python3
"""Test GLM models against ZhipuAI API"""

import json
import requests
from datetime import datetime
import hashlib
import hmac
import base64
import time
import sys

API_KEY = "7c9a64caea6848d9b2a78cb452b8c564.eTEJlpK6BaCbFCfa"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

def generate_zhipu_jwt(api_key: str) -> str:
    """Generate JWT token for ZhipuAI API authentication"""
    if '.' not in api_key:
        return api_key

    api_id, api_secret = api_key.split('.', 1)

    # JWT Header
    header = {"alg": "HS256", "sign_type": "SIGN"}

    # JWT Payload
    timestamp = int(time.time())
    payload = {
        "api_key": api_id,
        "exp": timestamp + 3600,
        "timestamp": timestamp
    }

    # Encode
    header_encoded = base64.urlsafe_b64encode(
        json.dumps(header, separators=(',', ':')).encode()
    ).rstrip(b'=').decode()

    payload_encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(',', ':')).encode()
    ).rstrip(b'=').decode()

    # Sign
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()

    signature_encoded = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

    return f"{message}.{signature_encoded}"


def test_model(model_name):
    """Test a single model"""
    # Generate JWT token
    token = generate_zhipu_jwt(API_KEY)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
    }

    try:
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=10)
        return response.status_code, response.json() if response.text else {}
    except Exception as e:
        return None, {"error": str(e)}


def main():
    print("=" * 60)
    print("Testing GLM models against ZhipuAI API")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
    print("=" * 60)
    print()

    # Models to test
    MODELS = [
        "glm-4",
        "glm-4-plus",
        "glm-4-flash",
        "glm-4-air",
        "glm-4-0520",
        "glm-4-turbo",
        "glm-4.7",
        "chatglm4",
        "glm-4v",
        "glm-4-alltools",
        "glm-3-turbo",
        "glm-4-long",
    ]

    results = {
        "exists": [],
        "not_found": [],
        "errors": []
    }

    for model in MODELS:
        print(f"Testing {model:25} ... ", end="", flush=True)

        status_code, response = test_model(model)

        if status_code == 200:
            print("✅ EXISTS")
            results["exists"].append(model)
        elif status_code in [400, 404]:
            print("❌ NOT FOUND")
            results["not_found"].append(model)
            error = response.get("error", {})
            if isinstance(error, dict):
                message = error.get("message", error.get("type", "Unknown error"))
                print(f"   Error: {message}")
        elif status_code == 401:
            print("⚠️  AUTH ERROR")
            results["errors"].append((model, "Authentication failed"))
            print(f"   Response: {response}")
        elif status_code is None:
            print("⚠️  CONNECTION ERROR")
            results["errors"].append((model, response.get("error", "Connection failed")))
        else:
            print(f"⚠️  HTTP {status_code}")
            results["errors"].append((model, f"HTTP {status_code}"))
            if response:
                print(f"   Response: {json.dumps(response, indent=2)[:200]}")
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Existing models ({len(results['exists'])}):")
    for model in results["exists"]:
        print(f"   - {model}")
    print()

    print(f"❌ Not found ({len(results['not_found'])}):")
    for model in results["not_found"]:
        print(f"   - {model}")
    print()

    if results["errors"]:
        print(f"⚠️  Errors ({len(results['errors'])}):")
        for model, error in results["errors"]:
            print(f"   - {model}: {error}")
    print()

    print("=" * 60)
    print("Official GLM Model Documentation:")
    print("=" * 60)
    print("According to ZhipuAI docs, available models include:")
    print("  - glm-4 (latest flagship)")
    print("  - glm-4-plus")
    print("  - glm-4-air")
    print("  - glm-4-flash (fastest)")
    print("  - glm-4-long (long context)")
    print("  - glm-4v (vision)")
    print("  - glm-4-alltools (function calling)")
    print("=" * 60)


if __name__ == "__main__":
    main()

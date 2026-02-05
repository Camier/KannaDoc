#!/usr/bin/env python3
"""
Configure all available LLM providers for RAG chat.

This script adds model configurations for users "miko" and "thesis"
using all available providers with API keys.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongo import mongodb
from app.db.repositories.model_config import ModelConfigRepository
from app.core.logging import logger


# Model configurations for all available providers
# Based on provider_client.py PROVIDERS configuration
MODELS_TO_ADD = [
    # OpenAI Models
    {
        "model_name": "gpt-4o",
        "model_url": "https://api.openai.com/v1",
        "provider": "openai",
        "description": "OpenAI GPT-4o (Omni)"
    },
    {
        "model_name": "gpt-4o-mini",
        "model_url": "https://api.openai.com/v1",
        "provider": "openai",
        "description": "OpenAI GPT-4o Mini (Fast)"
    },
    {
        "model_name": "gpt-3.5-turbo",
        "model_url": "https://api.openai.com/v1",
        "provider": "openai",
        "description": "OpenAI GPT-3.5 Turbo"
    },

    # DeepSeek Models
    {
        "model_name": "deepseek-v3.2",
        "model_url": "https://api.deepseek.com/v1",
        "provider": "deepseek",
        "description": "DeepSeek V3.2 (Latest)"
    },
    {
        "model_name": "deepseek-chat",
        "model_url": "https://api.deepseek.com/v1",
        "provider": "deepseek",
        "description": "DeepSeek Chat"
    },
    {
        "model_name": "deepseek-r1",
        "model_url": "https://api.deepseek.com/v1",
        "provider": "deepseek",
        "description": "DeepSeek R1 (Reasoning)"
    },

    # Z.ai GLM Models
    {
        "model_name": "glm-4.7",
        "model_url": "",
        "provider": "zai",
        "description": "Z.ai GLM-4.7"
    },
    {
        "model_name": "glm-4-plus",
        "model_url": "",
        "provider": "zai",
        "description": "Z.ai GLM-4 Plus"
    },
    {
        "model_name": "glm-4-flash",
        "model_url": "",
        "provider": "zai",
        "description": "Z.ai GLM-4 Flash (Fast)"
    },

    # Moonshot Models
    {
        "model_name": "kimi-k2-thinking",
        "model_url": "https://api.moonshot.cn/v1",
        "provider": "moonshot",
        "description": "Moonshot Kimi K2 Thinking"
    },
    {
        "model_name": "moonshot-v1-128k",
        "model_url": "https://api.moonshot.cn/v1",
        "provider": "moonshot",
        "description": "Moonshot V1 128K Context"
    },

    # MiniMax Models
    {
        "model_name": "abab6.5s-chat",
        "model_url": "https://api.minimax.chat/v1",
        "provider": "minimax",
        "description": "MiniMax abab6.5s Chat"
    },
    {
        "model_name": "abab6.5g-chat",
        "model_url": "https://api.minimax.chat/v1",
        "provider": "minimax",
        "description": "MiniMax abab6.5g Chat"
    },

    # Cohere Models
    {
        "model_name": "command-r-plus",
        "model_url": "https://api.cohere.ai/v1",
        "provider": "cohere",
        "description": "Cohere Command R+"
    },
    {
        "model_name": "command-r",
        "model_url": "https://api.cohere.ai/v1",
        "provider": "cohere",
        "description": "Cohere Command R"
    },
]

# Default parameters for all models
DEFAULT_PARAMS = {
    "temperature": 0.7,
    "max_length": 4096,
    "top_P": 0.9,
    "top_K": 3,
    "score_threshold": 10,
    "base_used": [],
    "system_prompt": "You are a helpful AI assistant."
}

# API key environment variable mapping
PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "zai": "ZAI_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "cohere": "COHERE_API_KEY",
}


async def configure_users():
    """Configure model configs for users miko and thesis"""

    # Connect to MongoDB
    await mongodb.connect()
    db = mongodb.db

    # Create repository
    repo = ModelConfigRepository(db)

    users = ["miko", "thesis"]
    results = {
        "users": {},
        "total_added": 0,
        "errors": []
    }

    for username in users:
        print(f"\n{'='*60}")
        print(f"Configuring models for user: {username}")
        print(f"{'='*60}")

        results["users"][username] = {
            "added": [],
            "skipped": [],
            "errors": []
        }

        # Check if user config exists
        existing = await db.model_config.find_one({"username": username})

        if not existing:
            print(f"Creating new model config for user: {username}")
            # Create with first model as default selected
            first_model = MODELS_TO_ADD[0]
            provider = first_model["provider"]
            api_key = os.getenv(PROVIDER_KEYS[provider])

            if not api_key:
                print(f"  ERROR: API key for {provider} not found!")
                continue

            import uuid
            model_id = f"{username}_{uuid.uuid4()}"

            result = await repo.create_model_config(
                username=username,
                selected_model=model_id,
                model_id=model_id,
                model_name=first_model["model_name"],
                model_url=first_model["model_url"],
                api_key=api_key,
                provider=provider,
                **DEFAULT_PARAMS
            )

            if result["status"] == "success":
                print(f"  Created base config with {first_model['model_name']}")
                results["users"][username]["added"].append(first_model["model_name"])
                results["total_added"] += 1
            else:
                print(f"  ERROR: {result.get('message')}")
                results["users"][username]["errors"].append(result.get("message"))
                continue

        # Add remaining models
        start_idx = 1 if not existing else 0

        for model_info in MODELS_TO_ADD[start_idx:]:
            provider = model_info["provider"]
            model_name = model_info["model_name"]
            model_url = model_info["model_url"]

            # Check if API key exists
            api_key = os.getenv(PROVIDER_KEYS[provider])
            if not api_key:
                msg = f"API key for {provider} not found, skipping {model_name}"
                print(f"  WARNING: {msg}")
                results["users"][username]["skipped"].append(model_name)
                continue

            # Check if model already exists
            existing_model = await db.model_config.find_one({
                "username": username,
                "models.model_name": model_name
            })

            if existing_model:
                print(f"  Skipping {model_name} (already exists)")
                results["users"][username]["skipped"].append(model_name)
                continue

            # Add model configuration
            result = await repo.add_model_config(
                username=username,
                model_id=f"{username}_{model_name.replace('-', '_')}",
                model_name=model_name,
                model_url=model_url,
                api_key=api_key,
                provider=provider,
                **DEFAULT_PARAMS
            )

            if result["status"] == "success":
                print(f"  Added: {model_name} ({model_info['description']})")
                results["users"][username]["added"].append(model_name)
                results["total_added"] += 1
            else:
                msg = f"Failed to add {model_name}: {result.get('message')}"
                print(f"  ERROR: {msg}")
                results["users"][username]["errors"].append(msg)
                results["errors"].append(msg)

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for username in users:
        user_results = results["users"][username]
        print(f"\n{username}:")
        print(f"  Added: {len(user_results['added'])} models")
        print(f"  Skipped: {len(user_results['skipped'])} models")
        print(f"  Errors: {len(user_results['errors'])}")

        if user_results['added']:
            print(f"  Added models:")
            for m in user_results['added']:
                print(f"    - {m}")

    print(f"\nTotal models added: {results['total_added']}")

    if results['errors']:
        print(f"\nErrors encountered: {len(results['errors'])}")
        for err in results['errors'][:5]:  # Show first 5 errors
            print(f"  - {err}")

    # Verify final configuration
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    for username in users:
        config = await repo.get_all_models_config(username)
        if config["status"] == "success":
            models = config.get("models", [])
            selected = config.get("selected_model", "")
            print(f"\n{username}:")
            print(f"  Total models: {len(models)}")
            print(f"  Selected model: {selected}")
            print(f"  Available models:")
            for m in models:
                selected_mark = " <-- SELECTED" if m.get("model_id") == selected else ""
                print(f"    - {m.get('model_name')}{selected_mark}")

    # Close connection
    await mongodb.close()

    return results


if __name__ == "__main__":
    print("LLM Provider Configuration Script")
    print("=" * 60)
    print("Checking for API keys...")

    missing_keys = []
    for provider, env_var in PROVIDER_KEYS.items():
        if os.getenv(env_var):
            print(f"  Found {provider}: {env_var}")
        else:
            print(f"  Missing {provider}: {env_var}")
            missing_keys.append(provider)

    if missing_keys:
        print(f"\nWARNING: Missing API keys for: {', '.join(missing_keys)}")
        print("Those providers will be skipped.")

    print("\nStarting configuration...")
    asyncio.run(configure_users())

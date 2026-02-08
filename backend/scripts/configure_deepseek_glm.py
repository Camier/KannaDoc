#!/usr/bin/env python3
"""
Configure DeepSeek and GLM models for Layra users.

This script configures the latest DeepSeek and GLM model configurations
for specified users in MongoDB.

Models configured:
- DeepSeek: deepseek-chat, deepseek-reasoner
- GLM: glm-4.7
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

# Database configuration
MONGODB_URL = os.getenv("MONGODB_URL", "localhost:27017")
MONGODB_USERNAME = os.getenv("MONGODB_ROOT_USERNAME", "thesis")
MONGODB_PASSWORD = os.getenv(
    "MONGODB_ROOT_PASSWORD", "thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac"
)
MONGODB_DB = os.getenv("MONGODB_DB", "chat_mongodb")

# API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")

# Users to configure
USERS = ["miko", "thesis"]

# Model configurations - Using CORRECT API model names
MODELS = {
    "deepseek-chat": {
        "model_name": "deepseek-chat",
        "model_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "provider": "deepseek",
        "description": "DeepSeek Chat (Standard)",
        "default_params": {
            "temperature": 0.7,
            "max_length": 4096,
            "top_P": 0.9,
            "top_K": 50,
            "score_threshold": 0.7,
        },
    },
    "deepseek-reasoner": {
        "model_name": "deepseek-reasoner",
        "model_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "provider": "deepseek",
        "description": "DeepSeek Reasoner (R1)",
        "default_params": {
            "temperature": 0.7,
            "max_length": 8192,
            "top_P": 0.9,
            "top_K": 50,
            "score_threshold": 0.7,
        },
    },
    "glm-4.7": {
        "model_name": "glm-4.7",
        "model_url": "https://api.z.ai/api/paas/v4",
        "api_key_env": "ZAI_API_KEY",
        "provider": "zai",
        "description": "Z.ai GLM-4.7",
        "default_params": {
            "temperature": 0.7,
            "max_length": 8192,
            "top_P": 0.9,
            "top_K": 50,
            "score_threshold": 0.7,
        },
    },
}

# Default model to set as selected
DEFAULT_MODEL = "deepseek-chat"


def log(message: str, level: str = "INFO"):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


async def configure_models_for_user(db, username: str) -> dict:
    """
    Configure all models for a specific user.

    Args:
        db: MongoDB database connection
        username: Username to configure models for

    Returns:
        dict: Configuration results
    """
    results = {
        "username": username,
        "models_added": [],
        "models_updated": [],
        "errors": [],
    }

    # Check if user config exists
    user_config = await db.model_config.find_one({"username": username})

    if not user_config:
        log(f"Creating new model config for user: {username}")
        # Create new user config with all models
        models_list = []
        for model_key, model_config in MODELS.items():
            api_key = os.getenv(model_config["api_key_env"], "")
            if not api_key:
                results["errors"].append(f"{model_key}: Missing API key")
                continue

            model_dict = {
                "model_id": f"{username}_{model_key}",
                "model_name": model_config["model_name"],
                "model_url": model_config["model_url"],
                "api_key": api_key,
                "provider": model_config["provider"],
                "base_used": ["chat", "workflow"],
                "system_prompt": "",
                **model_config["default_params"],
            }
            models_list.append(model_dict)
            results["models_added"].append(model_key)

        # Determine default model
        default_model_id = f"{username}_{DEFAULT_MODEL}"

        new_config = {
            "username": username,
            "selected_model": default_model_id,
            "models": models_list,
        }

        try:
            await db.model_config.insert_one(new_config)
            log(f"Created config for {username} with {len(models_list)} models")
        except Exception as e:
            error_msg = f"Failed to create config: {str(e)}"
            log(error_msg, "ERROR")
            results["errors"].append(error_msg)
    else:
        log(f"Updating existing model config for user: {username}")
        existing_models = {m.get("model_id"): m for m in user_config.get("models", [])}

        for model_key, model_config in MODELS.items():
            api_key = os.getenv(model_config["api_key_env"], "")
            if not api_key:
                results["errors"].append(f"{model_key}: Missing API key")
                continue

            model_id = f"{username}_{model_key}"

            if model_id in existing_models:
                # Update existing model
                update_data = {
                    "models.$.model_name": model_config["model_name"],
                    "models.$.model_url": model_config["model_url"],
                    "models.$.api_key": api_key,
                    "models.$.provider": model_config["provider"],
                }

                for param_key, param_value in model_config["default_params"].items():
                    update_data[f"models.$.{param_key}"] = param_value

                try:
                    await db.model_config.update_one(
                        {"username": username, "models.model_id": model_id},
                        {"$set": update_data},
                    )
                    results["models_updated"].append(model_key)
                    log(f"Updated model: {model_key} for {username}")
                except Exception as e:
                    error_msg = f"Failed to update {model_key}: {str(e)}"
                    log(error_msg, "ERROR")
                    results["errors"].append(error_msg)
            else:
                # Add new model
                model_dict = {
                    "model_id": model_id,
                    "model_name": model_config["model_name"],
                    "model_url": model_config["model_url"],
                    "api_key": api_key,
                    "provider": model_config["provider"],
                    "base_used": ["chat", "workflow"],
                    "system_prompt": "",
                    **model_config["default_params"],
                }

                try:
                    await db.model_config.update_one(
                        {"username": username}, {"$push": {"models": model_dict}}
                    )
                    results["models_added"].append(model_key)
                    log(f"Added model: {model_key} for {username}")
                except Exception as e:
                    error_msg = f"Failed to add {model_key}: {str(e)}"
                    log(error_msg, "ERROR")
                    results["errors"].append(error_msg)

        # Set default model
        default_model_id = f"{username}_{DEFAULT_MODEL}"
        try:
            await db.model_config.update_one(
                {"username": username}, {"$set": {"selected_model": default_model_id}}
            )
            log(f"Set default model to {DEFAULT_MODEL} for {username}")
        except Exception as e:
            error_msg = f"Failed to set default model: {str(e)}"
            log(error_msg, "ERROR")
            results["errors"].append(error_msg)

    return results


async def verify_api_keys() -> dict:
    """Verify that all required API keys are present."""
    log("Verifying API keys...")
    verification = {"deepseek": bool(DEEPSEEK_API_KEY), "zai": bool(ZAI_API_KEY)}

    for provider, status in verification.items():
        if status:
            log(f"  {provider.upper()}: API key found")
        else:
            log(f"  {provider.upper()}: API key MISSING", "ERROR")

    return verification


async def main():
    """Main execution function."""
    log("=" * 80)
    log("DeepSeek and GLM Model Configuration Script")
    log("=" * 80)

    # Verify API keys
    key_verification = await verify_api_keys()
    if not all(key_verification.values()):
        log("\nERROR: Missing required API keys. Please set:", "ERROR")
        if not key_verification["deepseek"]:
            log("  - DEEPSEEK_API_KEY", "ERROR")
        if not key_verification["zai"]:
            log("  - ZAI_API_KEY", "ERROR")
        sys.exit(1)

    # Connect to MongoDB
    log(f"\nConnecting to MongoDB at {MONGODB_URL}...")
    try:
        client = AsyncIOMotorClient(
            f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URL}",
            serverSelectionTimeoutMS=5000,
        )
        db = client[MONGODB_DB]

        # Test connection
        await db.command("ping")
        log("MongoDB connection successful")
    except Exception as e:
        log(f"Failed to connect to MongoDB: {str(e)}", "ERROR")
        sys.exit(1)

    # Configure models for each user
    log(f"\nConfiguring models for users: {', '.join(USERS)}")
    log("-" * 80)

    all_results = []
    for user in USERS:
        log(f"\nProcessing user: {user}")
        result = await configure_models_for_user(db, user)
        all_results.append(result)

        # Print summary for user
        log(f"  Summary for {user}:")
        log(f"    Models added: {len(result['models_added'])}")
        log(f"    Models updated: {len(result['models_updated'])}")
        log(f"    Errors: {len(result['errors'])}")

        if result["models_added"]:
            log(f"    Added: {', '.join(result['models_added'])}")
        if result["models_updated"]:
            log(f"    Updated: {', '.join(result['models_updated'])}")
        if result["errors"]:
            log(f"    Errors: {', '.join(result['errors'])}", "WARNING")

    # Final summary
    log("\n" + "=" * 80)
    log("Configuration Complete")
    log("=" * 80)

    total_added = sum(len(r["models_added"]) for r in all_results)
    total_updated = sum(len(r["models_updated"]) for r in all_results)
    total_errors = sum(len(r["errors"]) for r in all_results)

    log(f"\nTotal models added: {total_added}")
    log(f"Total models updated: {total_updated}")
    log(f"Total errors: {total_errors}")

    if total_errors > 0:
        log("\nWARNING: Some configurations had errors. Review logs above.", "WARNING")
        sys.exit(1)
    else:
        log("\nAll models configured successfully!")
        log(f"Default model: {DEFAULT_MODEL}")

    # Close connection
    client.close()
    log("\nMongoDB connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n\nScript interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"\n\nUnexpected error: {str(e)}", "ERROR")
        import traceback

        traceback.print_exc()
        sys.exit(1)

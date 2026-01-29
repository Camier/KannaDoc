#!/usr/bin/env python3
"""
Complete model configuration refresh for LAYRA system.
Replaces the entire 'models' array with 5 properly configured non-OpenAI models.
"""

import asyncio
import os
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Model configurations - all non-OpenAI models
MODEL_CONFIGS = [
    {
        "model_id": "thesis_deepseek_v3_2_3_user",
        "model_name": "deepseek-v3.2",
        "model_url": None,
        "api_key": None,
        "base_used": [
            {
                "name": "Thesis Corpus",
                "baseId": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
            }
        ],
        "system_prompt": "All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": -1,
        "score_threshold": 10,
    },
    {
        "model_id": "thesis_deepseek_r1_4_user",
        "model_name": "deepseek-r1",
        "model_url": None,
        "api_key": None,
        "base_used": [
            {
                "name": "Thesis Corpus",
                "baseId": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
            }
        ],
        "system_prompt": "All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": -1,
        "score_threshold": 10,
    },
    {
        "model_id": "thesis_kimi_k2_thinking_5_user",
        "model_name": "kimi-k2-thinking",
        "model_url": None,
        "api_key": None,
        "base_used": [
            {
                "name": "Thesis Corpus",
                "baseId": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
            }
        ],
        "system_prompt": "All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": -1,
        "score_threshold": 10,
    },
    {
        "model_id": "thesis_glm_4_7_6_user",
        "model_name": "glm-4.7",
        "model_url": None,
        "api_key": None,
        "base_used": [
            {
                "name": "Thesis Corpus",
                "baseId": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
            }
        ],
        "system_prompt": "All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": -1,
        "score_threshold": 10,
    },
    {
        "model_id": "thesis_glm_4_7_flash_7_user",
        "model_name": "glm-4.7-flash",
        "model_url": None,
        "api_key": None,
        "base_used": [
            {
                "name": "Thesis Corpus",
                "baseId": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
            }
        ],
        "system_prompt": "All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": -1,
        "score_threshold": 10,
    },
]


async def update_models():
    """Update MongoDB with new model configurations"""

    # Get MongoDB connection details from environment
    mongo_url = os.getenv("MONGODB_URL", "mongodb:27017")
    mongo_user = os.getenv("MONGODB_ROOT_USERNAME", "thesis")
    mongo_pass = os.getenv(
        "MONGODB_ROOT_PASSWORD", "thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac"
    )
    mongo_db = os.getenv("MONGODB_DB", "chat_mongodb")

    print(f"Connecting to MongoDB: {mongo_url}")
    print(f"Database: {mongo_db}")
    print(f"User: {mongo_user}")

    # Connect to MongoDB
    client = AsyncIOMotorClient(
        f"mongodb://{mongo_user}:{mongo_pass}@{mongo_url}/{mongo_db}?authSource=admin"
    )

    db = client[mongo_db]
    collection = db["model_config"]

    print("\n📋 Current configuration:")
    existing = await collection.find_one({"username": "thesis"})
    if existing:
        print(f"  Found user: {existing.get('username')}")
        print(f"  Current models: {len(existing.get('models', []))}")
        for model in existing.get("models", []):
            print(f"    - {model.get('model_name')} (ID: {model.get('model_id')})")
        print(f"  Selected model: {existing.get('selected_model')}")

    print("\n✨ New configuration:")
    for model in MODEL_CONFIGS:
        print(f"  - {model['model_name']} (ID: {model['model_id']})")

    # Prepare update document
    update_doc = {
        "$set": {
            "models": MODEL_CONFIGS,
            "selected_model": "thesis_glm_4_7_6_user",  # Default to glm-4.7
            "updated_at": datetime.utcnow().isoformat(),
        }
    }

    print(f"\n🔄 Updating database...")
    result = await collection.update_one({"username": "thesis"}, update_doc)

    if result.matched_count > 0:
        print(f"✅ Successfully updated configuration")
        print(f"   Matched: {result.matched_count} document(s)")
        print(f"   Modified: {result.modified_count} document(s)")
        print(f"   Default model: glm-4.7 (thesis_glm_4_7_6_user)")
    else:
        print(f"❌ No document matched for username 'thesis'")

    # Verify the update
    print("\n🔍 Verification:")
    updated = await collection.find_one({"username": "thesis"})
    if updated:
        print(f"  Total models: {len(updated.get('models', []))}")
        print(f"  Selected model: {updated.get('selected_model')}")

        model_names = [
            m.get("model_name", "Unknown") for m in updated.get("models", [])
        ]
        print(f"  Available models: {', '.join(model_names)}")

        # Check for null values in API keys and URLs
        for model in updated.get("models", []):
            if model.get("api_key") is not None:
                print(
                    f"  ⚠️  Warning: {model['model_name']} has API key in database (should be null)"
                )
            if model.get("model_url") is not None:
                print(
                    f"  ⚠️  Warning: {model['model_name']} has model_url in database (should be null)"
                )

    client.close()
    print("\n✅ Update complete!")


async def main():
    """Main entry point"""
    print("=" * 70)
    print("LAYRA Model Configuration Refresh")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Replace the entire 'models' array with 5 new configurations")
    print("  2. Set default model to 'glm-4.7'")
    print("  3. Use environment variables for API keys (not stored in DB)")
    print("  4. Preserve knowledge base selections")
    print("\nModels to be configured:")
    print("  • deepseek-v3.2 (DeepSeek provider)")
    print("  • deepseek-r1 (DeepSeek provider)")
    print("  • kimi-k2-thinking (Moonshot provider)")
    print("  • glm-4.7 (Zhipu provider)")
    print("  • glm-4.7-flash (Zhipu provider)")
    print("=" * 70)

    # Ask for confirmation (in production, would check CLI args)
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        confirm = True
    else:
        response = input("\nProceed with update? (yes/no): ").strip().lower()
        confirm = response in ["yes", "y"]

    if confirm:
        await update_models()
    else:
        print("\nUpdate cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

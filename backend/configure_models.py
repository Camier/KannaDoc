"""
DEPRECATED: This script uses the OLD model_config schema.

Use scripts/configure_deepseek_glm.py instead, which:
- Uses the new schema with embedded 'models' array
- Supports glm-4.7, glm-4.7-flash, deepseek-chat, deepseek-r1
- Handles existing config updates (upsert)

This file is kept for reference only.
"""

import asyncio
import os
import sys
import warnings

warnings.warn(
    "configure_models.py is DEPRECATED. Use scripts/configure_deepseek_glm.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

sys.path.insert(0, "/app")

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def configure_models():
    """
    DEPRECATED: Configure models using OLD schema.

    This creates individual documents per model, which is NOT the current schema.
    The current schema uses a single document per user with embedded 'models' array.

    See: scripts/configure_deepseek_glm.py for the correct approach.
    """
    print("WARNING: This script is DEPRECATED!")
    print("Use: python scripts/configure_deepseek_glm.py")
    print("")

    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client.chat_mongodb

    await db.model_config.delete_many({})

    # Updated model names for 2026
    models = [
        {
            "username": "miko",
            "chat_model": "miko_deepseek_chat",
            "model_name": "deepseek-chat",
            "llm_provider": "deepseek",
            "embedding_model": "local_colqwen",
            "is_selected": True,
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        },
        {
            "username": "miko",
            "chat_model": "miko_deepseek_r1",
            "model_name": "deepseek-r1",
            "llm_provider": "deepseek",
            "embedding_model": "local_colqwen",
            "is_selected": False,
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        },
        {
            "username": "miko",
            "chat_model": "miko_glm47",
            "model_name": "glm-4.7",  # Updated from glm-4
            "llm_provider": "zhipu",
            "embedding_model": "local_colqwen",
            "is_selected": False,
            "api_key": os.getenv("ZHIPUAI_API_KEY", ""),
        },
        {
            "username": "miko",
            "chat_model": "miko_glm4_plus",
            "model_name": "glm-4-plus",
            "llm_provider": "zhipu",
            "embedding_model": "local_colqwen",
            "is_selected": False,
            "api_key": os.getenv("ZHIPUAI_API_KEY", ""),
        },
        {
            "username": "miko",
            "chat_model": "miko_glm47_flash",
            "model_name": "glm-4.7-flash",  # Updated from glm-4-flash
            "llm_provider": "zhipu",
            "embedding_model": "local_colqwen",
            "is_selected": False,
            "api_key": os.getenv("ZHIPUAI_API_KEY", ""),
        },
    ]

    result = await db.model_config.insert_many(models)
    print(f"Inserted {len(result.inserted_ids)} model configurations for miko")

    for m in models:
        sel = " [SELECTED]" if m.get("is_selected") else ""
        chat_model = m["chat_model"]
        model_name = m["model_name"]
        provider = m["llm_provider"]
        print(f"  {chat_model}: {model_name} ({provider}){sel}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(configure_models())

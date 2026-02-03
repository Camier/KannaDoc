import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# Configuration
MONGO_URL = os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise ValueError("MONGODB_URL environment variable is not set.")
USERNAME = "thesis"

# Models Data (From ~/.007)
MODELS = [
    {
        "name": "GPT-4o (OpenAI)",
        "model_name": "gpt-4o",
        "url": "https://api.openai.com/v1",
        "key": os.getenv("OPENAI_API_KEY", ""),
    },
    {
        "name": "DeepSeek Chat",
        "model_name": "deepseek-chat",
        "url": "https://api.deepseek.com/v1",
        "key": os.getenv("DEEPSEEK_API_KEY", ""),
    },
    {
        "name": "Kimi (Moonshot)",
        "model_name": "moonshot-v1-8k",
        "url": "https://api.moonshot.ai/v1",
        "key": os.getenv("KIMI_API_KEY", ""),
    },
    {
        "name": "MiniMax",
        "model_name": "abab6.5-chat",
        "url": "https://api.minimax.io/v1",
        "key": os.getenv("MINIMAX_API_KEY", ""),
    },
    {
        "name": "LiteLLM Proxy",
        "model_name": "gpt-4o",
        "url": os.getenv("LITELLM_URL", "http://172.17.0.1:4000/v1"),
        "key": os.getenv("LITELLM_KEY", ""),
    },
]


async def main():
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.chat_mongodb

    print(f"Configuring models for user: {USERNAME}")

    model_entries = []

    for m in MODELS:
        model_id = f"{USERNAME}_{uuid.uuid4()}"
        entry = {
            "model_id": model_id,
            "model_name": m["model_name"],
            "model_url": m["url"],
            "api_key": m["key"],
            "base_used": [],
            "system_prompt": "You are a helpful assistant.",
            "temperature": 0.7,
            "max_length": 4096,
            "top_P": 1.0,
            "top_K": 50,
            "score_threshold": 0.5,
        }
        model_entries.append(entry)
        print(f"Prepared: {m['name']}")

    # Select the first one (GPT-4o) as default
    default_id = model_entries[0]["model_id"]

    await db.model_config.update_one(
        {"username": USERNAME},
        {"$set": {"models": model_entries, "selected_model": default_id}},
        upsert=True,
    )

    print("✅ Model configuration updated!")


if __name__ == "__main__":
    asyncio.run(main())

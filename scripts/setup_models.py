
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# Configuration
MONGO_URL = "mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@mongodb:27017"
USERNAME = "thesis"

# Models Data (From ~/.007)
MODELS = [
    {
        "name": "GPT-4o (OpenAI)",
        "model_name": "gpt-4o",
        "url": "https://api.openai.com/v1",
        "key": "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"
    },
    {
        "name": "DeepSeek Chat",
        "model_name": "deepseek-chat",
        "url": "https://api.deepseek.com/v1",
        "key": "sk-29537d2ba74445f0894e53e48ca1d9ef"
    },
    {
        "name": "Kimi (Moonshot)",
        "model_name": "moonshot-v1-8k",
        "url": "https://api.moonshot.ai/v1",
        "key": "sk-kimi-JJ5U2tXQ8Butav4NSUiCiOpzCf1ppJsOWFZ71VXKHbgbJ8FppwdHOFgiSmNNSluL"
    },
    {
        "name": "MiniMax",
        "model_name": "abab6.5-chat",
        "url": "https://api.minimax.io/v1",
        "key": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiIiLCJVc2VyTmFtZSI6IlVuaXZlcnNpdMOpIGRlIEJvcmRlYXV4IiwiQWNjb3VudCI6IiIsIlN1YmplY3RJRCI6IjE5ODk0MTgzMDgzODE3MDgzMDMiLCJQaG9uZSI6IiIsIkdyb3VwSUQiOiIxOTg5NDE4MzA4MzczMzIzNzkxIiwiUGFnZU5hbWUiOiIiLCJNYWlsIjoibWlja2FlbC5zb3VlZGFuQGhvdG1haWwuZnIiLCJDcmVhdGVUaW1lIjoiMjAyNS0xMi0wNyAwMDo1NjoxNyIsIlRva2VuVHlwZSI6NCwiaXNzIjoibWluaW1heCJ9.QOF8Uu_x1egKlCkKB2GizKvh4KYWhW3G2rCNXO5izeFYMrWkJLWlAldZ7mgY8GZKqGrpQt5u9mqah_gCevgn0TaiJT9j9c1TC9sEjMwidoqfygOYlsXckK5de2JgiivfY9VvUiqcJU9mTOKoFbztwPEX7TXQUlJlVFArEuNKOxJdJLeaxyo2zOz-gAbZypII2Wsyz7L25zJ0k2cMetT_em40YW2AH6Hvql7mdDzjTgeRiF-Ve-fZMc8yYeVjBD9eWjUMvWWW1-xkZU_p3Lihk3JTJIG-7Qm941K7oE5MpvmD9QAGPZs4g_vvMi1xrxMQ8FLijqHnmebn98nuUcVfuQ"
    },
    {
        "name": "LiteLLM Proxy",
        "model_name": "gpt-4o", 
        "url": "http://172.17.0.1:4000/v1", # Try docker host gateway
        "key": "sk-safKz-RaebX20rwBBgPuIa7Xln2BTRm-FmMP5jtggAo"
    }
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
            "score_threshold": 0.5
        }
        model_entries.append(entry)
        print(f"Prepared: {m['name']}")

    # Select the first one (GPT-4o) as default
    default_id = model_entries[0]["model_id"]
    
    await db.model_config.update_one(
        {"username": USERNAME},
        {"$set": {
            "models": model_entries,
            "selected_model": default_id
        }},
        upsert=True
    )
    
    print("✅ Model configuration updated!")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def update_deepseek_reasoner():
    # Configuration
    mongo_user = os.environ.get("MONGODB_ROOT_USERNAME", "root")
    mongo_pass = os.environ.get("MONGODB_ROOT_PASSWORD", "root_password")
    mongo_host = os.environ.get("MONGODB_HOST", "mongodb")
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:27017"
    db_name = os.environ.get("MONGODB_DB", "chat_mongodb")
    
    username = "thesis"
    target_kb_id = "miko_e6643365-8b03_4bea-a69b_7a1df00ec653"
    
    # Correct DeepSeek Reasoner Config
    new_model = {
        "model_id": "deepseek-reasoner",
        "model_name": "DeepSeek Reasoner (R1)",
        "model_url": "https://api.deepseek.com/v1",  # Added /v1
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "base_used": [
            {
                "name": "Thesis Corpus",
                "baseId": target_kb_id
            }
        ],
        "system_prompt": "You are a helpful assistant.",
        "temperature": 1.0,
        "max_length": 8192,
        "top_P": 1.0,
        "top_K": 5,
        "score_threshold": 10 # Set a default threshold for RAG
    }

    print(f"Connecting to {mongo_url}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Update or insert
    result = await db.model_config.update_one(
        {"username": username, "models.model_id": "deepseek-reasoner"},
        {"$set": {"models.$": new_model}}
    )
    
    if result.matched_count == 0:
        print("Model not found in existing list, pushing new entry...")
        await db.model_config.update_one(
            {"username": username},
            {"$push": {"models": new_model}}
        )
    else:
        print("Updated existing DeepSeek Reasoner config.")
            
    print("Done! DeepSeek Reasoner parameters and API key verified.")

if __name__ == "__main__":
    asyncio.run(update_deepseek_reasoner())

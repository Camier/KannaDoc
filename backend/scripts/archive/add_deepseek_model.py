import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def add_deepseek_reasoner():
    # Configuration
    mongo_user = os.environ.get("MONGODB_ROOT_USERNAME", "root")
    mongo_pass = os.environ.get("MONGODB_ROOT_PASSWORD", "root_password")
    mongo_host = os.environ.get("MONGODB_HOST", "mongodb")
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:27017"
    db_name = os.environ.get("MONGODB_DB", "chat_mongodb")
    
    username = "thesis"
    
    # DeepSeek Reasoner Config
    new_model = {
        "model_id": "deepseek-reasoner",
        "model_name": "DeepSeek Reasoner (R1)",
        "model_url": "https://api.deepseek.com",  # Standard DeepSeek API URL
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "base_used": [],
        "system_prompt": "You are a helpful assistant.",
        "temperature": 0.0, # Reasoner models ignore this usually, but good to have default
        "max_length": 8192,
        "top_P": 1.0,
        "top_K": 5,
        "score_threshold": 0
    }

    print(f"Connecting to {mongo_url}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check if user exists
    user_config = await db.model_config.find_one({"username": username})
    
    if not user_config:
        print(f"User {username} not found in model_config. Creating...")
        await db.model_config.insert_one({
            "username": username,
            "selected_model": "deepseek-reasoner",
            "models": [new_model]
        })
    else:
        # Debug: Print first model keys
        if user_config.get("models"):
            print(f"Existing model keys: {list(user_config['models'][0].keys())}")

        # Check if model already exists (safely)
        exists = any(m.get("model_id") == "deepseek-reasoner" for m in user_config.get("models", []))
        if exists:
            print("DeepSeek Reasoner already exists. Updating...")
            await db.model_config.update_one(
                {"username": username, "models.model_id": "deepseek-reasoner"},
                {"$set": {"models.$": new_model}}
            )
        else:
            print("Adding DeepSeek Reasoner to existing list...")
            await db.model_config.update_one(
                {"username": username},
                {"$push": {"models": new_model}}
            )
            
    print("Done! DeepSeek Reasoner configured.")

if __name__ == "__main__":
    asyncio.run(add_deepseek_reasoner())

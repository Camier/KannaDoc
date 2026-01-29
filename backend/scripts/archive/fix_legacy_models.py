import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid

async def migrate_legacy_models():
    # Configuration
    mongo_user = os.environ.get("MONGODB_ROOT_USERNAME", "root")
    mongo_pass = os.environ.get("MONGODB_ROOT_PASSWORD", "root_password")
    mongo_host = os.environ.get("MONGODB_HOST", "mongodb")
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:27017"
    db_name = os.environ.get("MONGODB_DB", "chat_mongodb")
    
    username = "thesis"
    
    print(f"Connecting to {mongo_url}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    user_config = await db.model_config.find_one({"username": username})
    
    if not user_config:
        print("User not found.")
        return

    models = user_config.get("models", [])
    updated = False
    
    for i, model in enumerate(models):
        if "model_id" not in model:
            print(f"Fixing model: {model.get('model_name')}")
            # Generate a deterministic but unique-ish ID for legacy models
            # or just a random UUID prefixed with user
            new_id = f"{username}_{uuid.uuid4()}"
            model["model_id"] = new_id
            
            # Also fill in missing required fields with defaults to prevent UI errors
            if "model_url" not in model: model["model_url"] = ""
            if "api_key" not in model: model["api_key"] = ""
            if "base_used" not in model: model["base_used"] = []
            if "system_prompt" not in model: model["system_prompt"] = ""
            if "temperature" not in model: model["temperature"] = -1
            if "max_length" not in model: model["max_length"] = -1
            if "top_P" not in model: model["top_P"] = -1
            if "top_K" not in model: model["top_K"] = -1
            if "score_threshold" not in model: model["score_threshold"] = -1
            
            updated = True

    if updated:
        await db.model_config.update_one(
            {"username": username},
            {"$set": {"models": models}}
        )
        print("Successfully migrated legacy models.")
    else:
        print("No legacy models found needing migration.")

if __name__ == "__main__":
    asyncio.run(migrate_legacy_models())

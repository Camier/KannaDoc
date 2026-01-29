
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = "mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@mongodb:27017"
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"

async def main():
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.chat_mongodb
    
    print(f"Syncing files for KB: {KB_ID}")
    
    # Get all files for this KB
    files = await db.files.find({"knowledge_db_id": KB_ID}).to_list(None)
    print(f"Found {len(files)} files in collection")
    
    for f in files:
        file_entry = {
            "file_id": f["file_id"],
            "filename": f["file_name"],
            "minio_filename": f["file_name"], 
            "minio_url": f["minio_url"],
            "created_at": f["created_at"]
        }
        # Add to KB array if not present
        await db.knowledge_bases.update_one(
            {"knowledge_base_id": KB_ID},
            {"$addToSet": {"files": file_entry}}
        )
    
    # Also ensure used_chat and other arrays exist
    await db.knowledge_bases.update_one(
        {"knowledge_base_id": KB_ID},
        {"$set": {"is_delete": False}, "$setOnInsert": {"used_chat": []}},
        upsert=True
    )
    
    print("✅ Sync complete!")

if __name__ == "__main__":
    asyncio.run(main())

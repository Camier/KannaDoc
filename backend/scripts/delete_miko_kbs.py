import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymilvus import connections, utility

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB = os.getenv("MONGODB_DB", "chat_mongodb")
MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")

TARGET_USERNAME = "miko"

async def main():
    mongo_user = os.getenv("MONGODB_ROOT_USERNAME", "testuser")
    mongo_pass = os.getenv("MONGODB_ROOT_PASSWORD", "testpassword")
    mongo_host = "mongodb"
    mongo_port = "27017"
    import urllib.parse
    mongo_user = urllib.parse.quote_plus(mongo_user)
    mongo_pass = urllib.parse.quote_plus(mongo_pass)
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{MONGODB_DB}?authSource=admin"
    
    mongo_client = AsyncIOMotorClient(mongo_url)
    db = mongo_client[MONGODB_DB]
    connections.connect(uri=MILVUS_URI)
    
    print(f"Deleting KBs for {TARGET_USERNAME}...")
    async for kb in db.knowledge_bases.find({"username": TARGET_USERNAME}):
        kb_id = kb.get("knowledge_base_id")
        print(f"Deleting {kb_id}...")
        
        # Delete from knowledge_bases
        await db.knowledge_bases.delete_one({"knowledge_base_id": kb_id})
        
        # Delete from files
        await db.files.delete_many({"knowledge_base_id": kb_id})
        
        # Drop Milvus collection
        col_name = "colqwen" + kb_id.replace("-", "_")
        if utility.has_collection(col_name):
            utility.drop_collection(col_name)
            print(f"  Dropped collection {col_name}")

    print("Cleanup done.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_DB = os.getenv("MONGODB_DB", "chat_mongodb")

async def main():
    mongo_user = os.getenv("MONGODB_ROOT_USERNAME")
    mongo_pass = os.getenv("MONGODB_ROOT_PASSWORD")
    mongo_host = "mongodb"
    mongo_port = "27017"
    
    import urllib.parse
    mongo_user = urllib.parse.quote_plus(mongo_user)
    mongo_pass = urllib.parse.quote_plus(mongo_pass)
    
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{MONGODB_DB}?authSource=admin"
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[MONGODB_DB]
    
    print("--- Workflow Sample ---")
    doc = await db.workflows.find_one({})
    print(doc.keys() if doc else "None")
    
    print("\n--- Chatflow Sample ---")
    doc = await db.chatflows.find_one({})
    print(doc.keys() if doc else "None")

if __name__ == "__main__":
    asyncio.run(main())


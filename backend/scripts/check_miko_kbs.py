import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymilvus import connections, utility, Collection

# Config
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB = os.getenv("MONGODB_DB", "chat_mongodb")
MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")

TARGET_USERNAME = "testuser"


async def main():
    # Construct URL manually
    mongo_user = os.getenv("MONGODB_ROOT_USERNAME")
    if not mongo_user:
        raise ValueError("MONGODB_ROOT_USERNAME environment variable is required")
    mongo_pass = os.getenv("MONGODB_ROOT_PASSWORD")
    if not mongo_pass:
        raise ValueError("MONGODB_ROOT_PASSWORD environment variable is required")
    mongo_host = "mongodb"
    mongo_port = "27017"

    import urllib.parse

    mongo_user = urllib.parse.quote_plus(mongo_user)
    mongo_pass = urllib.parse.quote_plus(mongo_pass)

    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{MONGODB_DB}?authSource=admin"

    print(f"Connecting to MongoDB...")
    mongo_client = AsyncIOMotorClient(mongo_url)
    db = mongo_client[MONGODB_DB]

    print(f"Connecting to Milvus...")
    connections.connect(uri=MILVUS_URI)

    print(f"Knowledge Bases for user '{TARGET_USERNAME}':")
    async for kb in db.knowledge_bases.find({"username": TARGET_USERNAME}):
        kb_id = kb.get("knowledge_base_id")
        kb_name = kb.get("knowledge_base_name")
        files_count = len(kb.get("files", []))

        # Check 'files' collection
        files_col_count = await db.files.count_documents({"knowledge_base_id": kb_id})

        # Check Milvus
        col_name = "colqwen" + kb_id.replace("-", "_")
        milvus_count = "N/A"
        if utility.has_collection(col_name):
            col = Collection(col_name)
            # col.num_entities might be cached/delayed, flush helps
            # col.flush() # flush might be slow/timeout if busy
            milvus_count = col.num_entities

        print(f" - [{kb_name}] ID: {kb_id}")
        print(f"   Files in KB Array: {files_count}")
        print(f"   Files in Files Collection: {files_col_count}")
        print(f"   Vectors in Milvus: {milvus_count}")
        print("-" * 30)


if __name__ == "__main__":
    asyncio.run(main())

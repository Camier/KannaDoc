import asyncio
import urllib.parse
import os
import sys

# Ensure app path is in sys.path
sys.path.append(os.getcwd())

from motor.motor_asyncio import AsyncIOMotorClient
from app.rag.utils import process_file
from app.db.redis import redis
from app.db.vector_db import vector_db_client

# Credentials
MONGO_PASS = urllib.parse.quote_plus("thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac")
MONGO_URL = f"mongodb://thesis:{MONGO_PASS}@mongodb:27017/chat_mongodb?authSource=admin"

# KB ID and User
KB_ID = "miko_e6643365-8b03_4bea-a69b_7a1df00ec653"
USERNAME = "miko"

# The 5 Missing File IDs we identified
MISSING_FILE_IDS = [
    "miko_93156f81-98d7-4a63-bdac-feeb6070e9b2", # 2023 - Yates
    "miko_ff227796-ce4f-4760-b085-fd3ac93a0f77", # 2025 - Cuomo
    "miko_794e0adc-3b6c-4821-ab17-c171ef6a923d", # 2025 - Lepule
    "miko_d32cad43-8260-44cb-bf05-9ca62a9c6f15", # 2024 - Pickrell1
    "miko_2e2134ca-b4f9-4632-8b87-207552ef07bd"  # 2025 - Kaschula
]

async def restore_missing():
    print("🚀 Starting TARGETED restoration for 5 missing files...", flush=True)
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["chat_mongodb"]
    
    # 2. Ensure Milvus collection exists (it should, but safety first)
    collection_name = f"colqwen{KB_ID.replace('-', '_')}"
    if not vector_db_client.check_collection(collection_name):
        print(f"⚠️ Collection {collection_name} missing! Creating...")
        vector_db_client.create_collection(collection_name)

    redis_conn = await redis.get_task_connection()

    for file_id in MISSING_FILE_IDS:
        # Get current record to find path
        file_record = await db.files.find_one({"file_id": file_id})
        
        if not file_record:
            print(f"❌ Record for {file_id} not found in DB! Skipping.")
            continue

        filename = file_record.get("filename") or file_record.get("original_filename")
        minio_url = file_record.get("minio_url")
        record_username = file_record.get("username", USERNAME)
        
        # Path correction logic (same as before)
        object_name = minio_url
        
        print(f"\n🔄 Processing: {filename} ({file_id})")
        
        task_id = f"restore_{file_id}"
        
        # Initialize task in Redis
        await redis_conn.hset(f"task:{task_id}", mapping={
            "status": "processing",
            "total": 1,
            "processed": 0,
            "message": f"Restoring {filename}..."
        })
        
        file_meta = {
            "file_id": file_id,
            "original_filename": filename,
            "minio_filename": object_name,
            "minio_url": minio_url 
        }
        
        print(f"   🗑️  Cleaning up old metadata for {file_id}...")
        await db.files.delete_many({"file_id": file_id})
        await db.images.delete_many({"file_id": file_id})
        await db.knowledge_bases.update_one(
            {"knowledge_base_id": KB_ID},
            {"$pull": {"files": {"file_id": file_id}}}
        )
        
        print(f"   🚀 Triggering ingestion for {filename}...")
        try:
            await process_file(
                redis=redis_conn,
                task_id=task_id,
                username=record_username,
                knowledge_db_id=KB_ID,
                file_meta=file_meta
            )
            print(f"   ✅ Restoration complete for {filename}")
        except Exception as e:
            print(f"   ❌ Failed to restore {filename}: {e}")

    print("\n🎉 Targeted restoration complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(restore_missing())

import asyncio
import uuid
import urllib.parse
import io
from motor.motor_asyncio import AsyncIOMotorClient
from app.rag.utils import process_file, update_task_progress
from app.db.redis import redis

# Credentials
MONGO_PASS = urllib.parse.quote_plus("thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac")
MONGO_URL = f"mongodb://thesis:{MONGO_PASS}@mongodb:27017/chat_mongodb?authSource=admin"

# File details
USERNAME = "miko"
KB_ID = "miko_e6643365-8b03-4bea-a69b-7a1df00ec653"
FILE_NAME = "2025 - ed. - The Indigenous World.pdf"
MINIO_URL = "http://minio:9000/minio-file/thesis/2025 - ed. - The Indigenous World.pdf"
MINIO_FILENAME = "thesis/2025 - ed. - The Indigenous World.pdf"

async def process():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["chat_mongodb"]
    
    # Generate a fresh unique file_id to avoid any "ID already exists" loops
    FILE_ID = f"miko_indigenous_{int(uuid.uuid4().hex[:8], 16)}"
    
    print(f"--- Starting Clean Ingestion ---")
    print(f"File: {FILE_NAME}")
    print(f"Target ID: {FILE_ID}")
    print(f"Knowledge Base: {KB_ID}")
    
    file_meta = {
        "file_id": FILE_ID,
        "original_filename": FILE_NAME,
        "minio_filename": MINIO_FILENAME,
        "minio_url": MINIO_URL,
    }
    
    task_id = f"task_{FILE_ID}"
    print(f"Task ID: {task_id}")
    
    redis_conn = await redis.get_task_connection()
    # Initialize task in redis
    await redis_conn.hset(f"task:{task_id}", mapping={
        "status": "processing", 
        "message": "Starting manual remediation...",
        "total": 1,
        "processed": 0
    })
    
    print("Calling process_file (this will convert PDF to images and generate embeddings)...")
    try:
        result = await process_file(
            redis=redis_conn,
            task_id=task_id,
            username=USERNAME,
            knowledge_db_id=KB_ID,
            file_meta=file_meta,
        )
        print(f"Processing complete! Result: {result}")
        
        # Final status update in Mongo (process_file creates the record, we just update status)
        await db["files"].update_one(
            {"file_id": FILE_ID},
            {"$set": {"status": "parsed", "task_id": task_id}}
        )
        print("Database record marked as 'parsed'.")
        
    except Exception as e:
        print(f"FATAL ERROR during processing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(process())
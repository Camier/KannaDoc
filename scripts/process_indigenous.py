import asyncio
import uuid
import urllib.parse
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
MINIO_URL = "http://minio:9000/layra/thesis/2025 - ed. - The Indigenous World.pdf"
MINIO_FILENAME = "thesis/2025 - ed. - The Indigenous World.pdf"

async def process():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["chat_mongodb"]
    
    file_record = await db["files"].find_one({"username": USERNAME, "file_name": FILE_NAME})
    if not file_record:
        print("File not found")
        return
    
    FILE_ID = file_record["file_id"]
    print(f"Processing: {FILE_NAME}")
    print(f"  file_id: {FILE_ID}")
    print(f"  KB: {KB_ID}")
    
    file_meta = {
        "file_id": FILE_ID,
        "original_filename": FILE_NAME,
        "minio_filename": MINIO_FILENAME,
        "minio_url": MINIO_URL,
    }
    
    task_id = str(uuid.uuid4())
    
    redis_conn = await redis.get_task_connection()
    await update_task_progress(redis_conn, task_id, "processing", f"Processing {FILE_NAME}...")
    
    result = await process_file(
        redis=redis_conn,
        task_id=task_id,
        username=USERNAME,
        knowledge_db_id=KB_ID,
        file_meta=file_meta,
    )
    
    print(f"Processing complete: {result}")
    
    await db["files"].update_one(
        {"file_id": FILE_ID},
        {"$set": {"status": "parsed", "task_id": task_id}}
    )
    
    print("File status updated to 'parsed'")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(process())

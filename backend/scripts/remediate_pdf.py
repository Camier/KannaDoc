import asyncio
import os
import uuid
from app.db.mongo import get_mongo
from app.db.vector_db import vector_db_client
from app.db.miniodb import async_minio_manager
from app.rag.utils import process_file
from app.core.config import settings
from app.core.logging import logger

# Mock Redis for process_file
class MockRedis:
    async def hset(self, name, key=None, value=None, mapping=None):
        logger.info(f"[MockRedis] hset {name} {mapping}")
        return 1
    
    async def hincrby(self, name, key, amount=1):
        logger.info(f"[MockRedis] hincrby {name} {key} {amount}")
        return 1
        
    async def hget(self, name, key):
        # process_file checks current == total. Return 1 for both to simulate completion.
        return "1"

async def main():
    print("🚀 Starting Remediation Script")
    
    # 1. Initialize MongoDB
    db = await get_mongo()
    
    # 2. Find the corrupt file record
    target_filename = "2025 - ed. - The Indigenous World.pdf"
    print(f"🔍 Searching for file: {target_filename}")
    
    # Check in files collection
    # Note: Filename might be in a sub-field or just 'filename'
    file_doc = await db.db.files.find_one({"filename": target_filename})
    
    if not file_doc:
        print(f"❌ File not found in MongoDB: {target_filename}")
        # Try regex search?
        cursor = db.db.files.find({"filename": {"$regex": "Indigenous World"}})
        found = await cursor.to_list(length=5)
        if found:
            print("Did you mean one of these?")
            for f in found:
                print(f" - {f['filename']} (ID: {f['file_id']})")
        return

    file_id = file_doc["file_id"]
    knowledge_db_id = file_doc["knowledge_db_id"]
    username = file_doc["username"]
    minio_filename = file_doc["minio_filename"]
    minio_url = file_doc["minio_url"]
    
    print(f"✅ Found File Record:")
    print(f"  - File ID: {file_id}")
    print(f"  - KB ID: {knowledge_db_id}")
    print(f"  - MinIO Path: {minio_filename}")
    
    # 3. Purge Corrupt Data
    print("\n🗑️  Purging Corrupt Data...")
    
    # 3a. Clean Milvus
    collection_name = f"colqwen{knowledge_db_id.replace('-', '_')}"
    print(f"  - Cleaning Milvus Collection: {collection_name}")
    try:
        vector_db_client.delete_files(collection_name, [file_id])
        print("    ✓ Milvus cleanup initiated")
    except Exception as e:
        print(f"    ⚠️ Milvus cleanup error (might be empty): {e}")

    # 3b. Clean MongoDB and MinIO (via helper)
    # This deletes the file record AND the MinIO object
    print(f"  - Deleting from Knowledge Base (Mongo + MinIO)...")
    res = await db.delete_file_from_knowledge_base(knowledge_db_id, file_id)
    print(f"    ✓ Result: {res}")

    # 4. Restore Valid File
    print("\n♻️  Restoring Valid File...")
    valid_pdf_path = "/app/valid_restoration.pdf"
    
    if not os.path.exists(valid_pdf_path):
        print(f"❌ Error: Valid PDF not found at {valid_pdf_path}")
        return

    # Upload valid file to MinIO manually
    print(f"  - Uploading valid PDF to MinIO: {minio_filename}")
    with open(valid_pdf_path, "rb") as f:
        data = f.read()
        # We use the internal boto3 session from manager
        async with async_minio_manager.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            await client.put_object(
                Bucket=settings.minio_bucket_name,
                Key=minio_filename,
                Body=data,
                ContentType="application/pdf"
            )
    print("    ✓ Upload complete")

    # 5. Re-process (RAG Pipeline)
    print("\n⚙️  Triggering RAG Processing...")
    
    task_id = str(uuid.uuid4())
    mock_redis = MockRedis()
    
    file_meta = {
        "file_id": file_id, # Reuse the same ID for consistency/simplicity
        "original_filename": target_filename,
        "minio_filename": minio_filename,
        "minio_url": minio_url
    }
    
    try:
        await process_file(
            redis=mock_redis,
            task_id=task_id,
            username=username,
            knowledge_db_id=knowledge_db_id,
            file_meta=file_meta
        )
        print("\n✅ Remediation Complete! File processed successfully.")
    except Exception as e:
        print(f"\n❌ Processing Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

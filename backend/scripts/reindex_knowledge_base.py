import asyncio
from app.db.mongo import get_mongo
from app.utils.kafka_producer import kafka_producer_manager
from app.core.config import settings
from app.models.user import User
import uuid
import os

# Mock settings if needed, but running in container should have them
# We need to manually initialize things that main.py usually does

async def reindex_all():
    print("Initializing services...")
    db = await get_mongo()
    await kafka_producer_manager.start()
    
    print("Fetching all knowledge bases...")
    # Get all KBs directly from DB to avoid user context issues
    kbs = await db.db.knowledge_bases.find({"is_delete": False}).to_list(length=None)
    
    total_files = 0
    triggered_files = 0
    
    for kb in kbs:
        kb_id = kb["knowledge_base_id"]
        username = kb["username"]
        files = kb.get("files", [])
        
        print(f"Processing KB: {kb.get('knowledge_base_name')} ({kb_id}) - {len(files)} files")
        
        if not files:
            continue
            
        # Create a reindex task ID
        task_id = f"{username}_reindex_{uuid.uuid4()}"
        
        # We process file by file
        for file_info in files:
            file_id = file_info["file_id"]
            minio_filename = file_info["minio_filename"]
            original_filename = file_info.get("filename", "unknown")
            minio_url = file_info.get("minio_url", "")
            
            # Construct the file_meta object expected by the consumer
            # content of file_meta_list in base.py:
            # {
            #     "file_id": file_id,
            #     "minio_filename": minio_filename,
            #     "original_filename": file.filename,
            #     "minio_url": minio_url,
            # }
            
            file_meta = {
                "file_id": file_id,
                "minio_filename": minio_filename,
                "original_filename": original_filename,
                "minio_url": minio_url
            }
            
            print(f"  -> Queueing file: {original_filename} ({file_id})")
            
            await kafka_producer_manager.send_embedding_task(
                task_id=task_id,
                username=username,
                knowledge_db_id=kb_id,
                file_meta=file_meta,
                priority=1
            )
            triggered_files += 1
            total_files += 1
            
    print(f"\nRe-indexing initiated for {triggered_files} files across {len(kbs)} knowledge bases.")
    await kafka_producer_manager.stop()

if __name__ == "__main__":
    # Ensure env vars are loaded
    asyncio.run(reindex_all())

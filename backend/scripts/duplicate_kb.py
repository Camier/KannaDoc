import asyncio
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
import aioboto3
from pymilvus import (
    Collection,
    connections,
    utility,
)

# Configuration from Environment
DB_URL = os.getenv("DB_URL")
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB = os.getenv("MONGODB_DB", "chat_mongodb")
MINIO_URL = os.getenv("MINIO_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "minio-file")
MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")

# Constants
SOURCE_USERNAME = "testuser"
TARGET_USERNAME = "miko"
TARGET_PASSWORD = "miko_password"
TARGET_EMAIL = "miko@example.com"
SOURCE_KB_NAME = "Thesis Corpus"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def get_or_create_user(engine):
    print(f"Checking user {TARGET_USERNAME}...")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": TARGET_USERNAME}
        )
        user = result.fetchone()
        if user:
            print(f"User {TARGET_USERNAME} already exists.")
            return
        
        print(f"Creating user {TARGET_USERNAME}...")
        hashed_pw = get_password_hash(TARGET_PASSWORD)
        # Schema matched to actual DB: id, username, email, hashed_password, password_migration_required
        await session.execute(
            text("""
                INSERT INTO users (username, email, hashed_password, password_migration_required)
                VALUES (:username, :email, :password, FALSE)
            """),
            {"username": TARGET_USERNAME, "email": TARGET_EMAIL, "password": hashed_pw}
        )
        await session.commit()
        print(f"User {TARGET_USERNAME} created.")





async def main():
    engine = create_async_engine(DB_URL)
    # await get_or_create_user(engine)
    await engine.dispose()

    # Construct URL manually to avoid parsing issues and ensure authSource
    mongo_user = os.getenv("MONGODB_ROOT_USERNAME", "testuser")
    mongo_pass = os.getenv("MONGODB_ROOT_PASSWORD", "testpassword")
    mongo_host = "mongodb" # Service name in docker-compose
    mongo_port = "27017"
    
    # URL encode user and pass
    import urllib.parse
    mongo_user = urllib.parse.quote_plus(mongo_user)
    mongo_pass = urllib.parse.quote_plus(mongo_pass)
    
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/{MONGODB_DB}?authSource=admin"
    
    print(f"Connecting to MongoDB: mongodb://{mongo_user}:****@{mongo_host}:{mongo_port}/{MONGODB_DB}?authSource=admin")

    mongo_client = AsyncIOMotorClient(mongo_url)
    db = mongo_client[MONGODB_DB]
    
    source_kb = await db.knowledge_bases.find_one({
        "username": SOURCE_USERNAME,
        "knowledge_base_name": SOURCE_KB_NAME
    })
    
    if not source_kb:
        print(f"Source KB '{SOURCE_KB_NAME}' not found for user '{SOURCE_USERNAME}'")
        return

    source_kb_id = source_kb["knowledge_base_id"]
    target_kb_id = f"{TARGET_USERNAME}_{uuid.uuid4()}"
    
    print(f"Source KB ID: {source_kb_id}")
    print(f"Target KB ID: {target_kb_id}")

    target_kb = source_kb.copy()
    target_kb.pop("_id")
    target_kb["username"] = TARGET_USERNAME
    target_kb["knowledge_base_id"] = target_kb_id
    target_kb["knowledge_base_name"] = f"{SOURCE_KB_NAME} (Copy)"
    target_kb["created_at"] = datetime.utcnow()
    target_kb["updated_at"] = datetime.utcnow()
    
    # 4. Copy Files (MinIO + DB objects)
    print("Fetching files from 'files' collection...")
    cursor = db.files.find({"knowledge_base_id": source_kb_id})
    files_to_copy = await cursor.to_list(length=None)
    
    file_id_map = {} # old_id -> new_id
    
    if files_to_copy:
        print(f"Found {len(files_to_copy)} files to copy.")
        
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=MINIO_URL,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
        ) as s3:
            for file_doc in files_to_copy:
                old_file_id = file_doc["file_id"]
                old_key = file_doc.get("minio_url") or file_doc.get("minio_filename")
                
                if not old_key:
                    print(f"Skipping file {old_file_id} - no minio_url")
                    continue
                
                # Generate new file_id
                new_file_id = f"{TARGET_USERNAME}_{uuid.uuid4()}"
                file_id_map[old_file_id] = new_file_id
                
                # New MinIO Key
                # Pattern: {username}/{file_id}/{filename}
                filename = file_doc.get("file_name") or os.path.basename(old_key)
                new_key = f"{TARGET_USERNAME}/{new_file_id}/{filename}"
                
                print(f"  Copying {old_key} -> {new_key}")
                try:
                    copy_source = {'Bucket': MINIO_BUCKET_NAME, 'Key': old_key}
                    await s3.copy_object(
                        CopySource=copy_source,
                        Bucket=MINIO_BUCKET_NAME,
                        Key=new_key
                    )
                    
                    # Insert new DB doc
                    target_file_doc = file_doc.copy()
                    target_file_doc.pop("_id")
                    target_file_doc["file_id"] = new_file_id
                    target_file_doc["username"] = TARGET_USERNAME
                    target_file_doc["knowledge_base_id"] = target_kb_id
                    target_file_doc["minio_url"] = new_key # Standardize on minio_url
                    
                    await db.files.insert_one(target_file_doc)
                    
                except Exception as e:
                    print(f"  Error copying {old_key}: {e}")

    else:
        print("No files found in 'files' collection.")
    
    await db.knowledge_bases.insert_one(target_kb)
    print(f"Created new KB document: {target_kb_id}")
    
    await copy_milvus_collection(source_kb_id, target_kb_id, file_id_map)
    
    print("Process Complete.")

# Update copy_milvus_collection signature to accept map
async def copy_milvus_collection(source_kb_id: str, target_kb_id: str, file_id_map: Dict[str, str]):
    print("Copying Milvus collection...")
    # ... (connection)
    connections.connect(uri=MILVUS_URI)
    
    source_col_name = "colqwen" + source_kb_id.replace("-", "_")
    target_col_name = "colqwen" + target_kb_id.replace("-", "_")
    
    # ... (rest of loading/creating)
    if not utility.has_collection(source_col_name):
        print(f"Source collection {source_col_name} not found!")
        return

    if utility.has_collection(target_col_name):
        print(f"Target collection {target_col_name} already exists. Dropping...")
        utility.drop_collection(target_col_name)

    print(f"  Loading source {source_col_name}...")
    source_col = Collection(source_col_name)
    source_col.load()

    schema = source_col.schema
    
    print(f"  Creating target {target_col_name}...")
    target_col = Collection(target_col_name, schema=schema)

    print("  Migrating vectors (using PK iteration)...")
    count = source_col.num_entities
    print(f"  Total entities: {count}")
    
    if count > 0:
        batch_size = 10000
        last_pk = -1 
        
        while True:
            res = source_col.query(
                expr=f"pk > {last_pk}",
                output_fields=["*"],
                limit=batch_size,
            )
            if not res:
                break
            
            insert_data = []
            current_max_pk = last_pk
            
            for item in res:
                item_pk = item.get("pk")
                if item_pk is not None and item_pk > current_max_pk:
                    current_max_pk = item_pk

                if schema.auto_id:
                    item.pop("pk", None)
                
                # Update file_id using map
                old_fid = item.get("file_id")
                if old_fid and old_fid in file_id_map:
                    item["file_id"] = file_id_map[old_fid]
                
                insert_data.append(item)
            
            if insert_data:
                target_col.insert(insert_data)
                print(f"    Copied batch {len(insert_data)} entities (Last PK: {current_max_pk})")
            
            if len(res) < batch_size:
                break
                
            last_pk = current_max_pk

    # ... (index creation)
    print("  Creating index...")
    for index in source_col.indexes:
        # ... (same logic)
        field_name = index.field_name
        default_index_params = {
            "metric_type": "IP",
            "index_type": "HNSW",
            "params": {"M": 32, "efConstruction": 500}
        }
        try:
            target_col.create_index(field_name, default_index_params)
        except Exception as e:
            print(f"    Error creating index: {e}")

    target_col.flush()
    print("Milvus copy done.")

if __name__ == "__main__":
    asyncio.run(main())
import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from pymilvus import MilvusClient, DataType
from motor.motor_asyncio import AsyncIOMotorClient
import aioboto3

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config - must be set via environment variables
MONGO_URL = os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise ValueError("MONGODB_URI environment variable is required")

MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")
MINIO_URL = os.getenv("MINIO_URL", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
if not MINIO_ACCESS_KEY:
    raise ValueError("MINIO_ACCESS_KEY environment variable is required")

MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
if not MINIO_SECRET_KEY:
    raise ValueError("MINIO_SECRET_KEY environment variable is required")

MINIO_BUCKET = os.getenv("MINIO_BUCKET_NAME", "minio-file")

# Paths (Inside Container)
EMBEDDINGS_DIR = "/app/embeddings_output"
CORPUS_DIR = "/app/literature/corpus"

# Thesis Data
USERNAME = "thesis"
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
KB_NAME = "Thesis Corpus"
COLLECTION_NAME = "colqwen" + KB_ID.replace("-", "_")


async def init_minio(session):
    async with session.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    ) as s3:
        try:
            await s3.create_bucket(Bucket=MINIO_BUCKET)
        except Exception:
            pass  # Bucket likely exists


async def upload_to_minio(session, file_path, object_name):
    async with session.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    ) as s3:
        await s3.upload_file(file_path, MINIO_BUCKET, object_name)
        # Construct URL (internal for now, but backend will sign it)
        return f"{MINIO_BUCKET}/{object_name}"  # Internal ref


import math


def sanitize_vector(vec):
    """Ensure vector contains no NaN or Inf values by replacing them with 0.0"""
    return [0.0 if not math.isfinite(x) else x for x in vec]


async def main():
    logger.info("🚀 Starting Ingestion Pipeline (Sanitized Mode)")

    # 1. Connect Mongo
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.chat_mongodb

    # --- CLEAN START ---
    logger.info("🧹 Clearing existing metadata...")
    await db.knowledge_bases.delete_many({"knowledge_base_id": KB_ID})
    await db.files.delete_many({"knowledge_db_id": KB_ID})
    # -------------------

    # 2. Init KB
    kb = await db.knowledge_bases.find_one({"knowledge_base_id": KB_ID})
    if not kb:
        logger.info(f"Creating Knowledge Base: {KB_ID}")
        await db.knowledge_bases.insert_one(
            {
                "username": USERNAME,
                "knowledge_base_name": KB_NAME,
                "knowledge_base_id": KB_ID,
                "is_temp": False,
                "created_at": datetime.now(),
                "last_modify_at": datetime.now(),
            }
        )

    # 3. Connect Milvus & Init Collection
    milvus = MilvusClient(uri=MILVUS_URI)
    if milvus.has_collection(COLLECTION_NAME):
        logger.info(f"🧹 Dropping existing Milvus collection: {COLLECTION_NAME}")
        milvus.drop_collection(COLLECTION_NAME)

    if not milvus.has_collection(COLLECTION_NAME):
        logger.info(f"Creating Milvus Collection: {COLLECTION_NAME}")
        schema = milvus.create_schema(auto_id=True, enable_dynamic_fields=True)
        schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=128)
        schema.add_field(
            field_name="image_id", datatype=DataType.VARCHAR, max_length=65535
        )
        schema.add_field(field_name="page_number", datatype=DataType.INT64)
        schema.add_field(
            field_name="file_id", datatype=DataType.VARCHAR, max_length=65535
        )

        milvus.create_collection(collection_name=COLLECTION_NAME, schema=schema)

        idx_params = milvus.prepare_index_params()
        idx_params.add_index(
            field_name="vector",
            index_name="vector_index",
            index_type="HNSW",
            metric_type="IP",
            params={"M": 32, "efConstruction": 500},
        )
        milvus.create_index(collection_name=COLLECTION_NAME, index_params=idx_params)
        milvus.load_collection(COLLECTION_NAME)
    else:
        logger.info(f"Milvus Collection exists: {COLLECTION_NAME}")

    # 4. Init MinIO Session
    minio_session = aioboto3.Session()
    await init_minio(minio_session)

    # 5. Process Files
    json_files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.endswith(".json")]
    logger.info(f"Found {len(json_files)} embedding files to process")

    processed_count = 0

    for jf in json_files:
        json_path = os.path.join(EMBEDDINGS_DIR, jf)
        pdf_filename = jf.replace(".json", "")  # simplistic
        pdf_path = os.path.join(CORPUS_DIR, pdf_filename)

        # Look for PDF recursively if not flat
        if not os.path.exists(pdf_path):
            # Try to find it
            for root, dirs, files in os.walk(CORPUS_DIR):
                if pdf_filename in files:
                    pdf_path = os.path.join(root, pdf_filename)
                    break

        if not os.path.exists(pdf_path):
            logger.warning(
                f"⚠️ PDF not found for {jf}, skipping MinIO upload but ingesting vectors."
            )
            # We continue to ingest vectors so search works, but viewing file will fail

        # file_id generation
        file_id = f"{USERNAME}_{uuid.uuid4()}"
        minio_object_name = f"{USERNAME}/{file_id}/{pdf_filename}"

        # Upload to MinIO
        minio_url_path = ""
        if os.path.exists(pdf_path):
            logger.info(f"Uploading {pdf_filename} to MinIO...")
            await upload_to_minio(minio_session, pdf_path, minio_object_name)
            minio_url_path = (
                minio_object_name  # Store object key as url usually? Or full URL?
            )
            # App usually stores the minio key or url. Let's look at `save_file_to_minio` in app code.
            # It returns `minio_filename, minio_url`.
            # In Mongo `files` table, `minio_url` field is usually the Object Key or Signed URL?
            # `backend/app/api/endpoints/chat.py` stores `minio_url` in metadata.
            # But the `files` collection has `minio_url`? No, schema says `url`?
            # Let's assume storing Object Key is safest or relative path.
            # miniodb.py uses bucket+key.
            # We'll store the Object Key in `minio_filename` field if it exists, or `url`.

        # Load Embeddings
        with open(json_path, "r") as f:
            data = json.load(f)

        milvus_rows = []
        for page in data:
            pg_num = page["page_number"]
            image_id = f"{file_id}_{pg_num}"
            embeddings = page["embedding"]

            for vec in embeddings:
                sanitized_vec = sanitize_vector(vec)
                milvus_rows.append(
                    {
                        "vector": sanitized_vec,
                        "image_id": image_id,
                        "page_number": pg_num,
                        "file_id": file_id,
                    }
                )

        # Insert to Milvus in batches
        BATCH = 100
        for i in range(0, len(milvus_rows), BATCH):
            batch = milvus_rows[i : i + BATCH]
            milvus.insert(collection_name=COLLECTION_NAME, data=batch)

        # Save to Mongo
        await db.files.insert_one(
            {
                "file_id": file_id,
                "username": USERNAME,
                "file_name": pdf_filename,
                "knowledge_db_id": KB_ID,
                "status": "parsed",
                "minio_url": minio_object_name,  # Storing key here
                "file_size": os.path.getsize(pdf_path)
                if os.path.exists(pdf_path)
                else 0,
                "created_at": datetime.now(),
                "last_modify_at": datetime.now(),
            }
        )

        processed_count += 1

    logger.info(f"🎉 Ingestion Complete. Processed {processed_count} files.")


if __name__ == "__main__":
    asyncio.run(main())

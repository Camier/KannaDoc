#!/usr/bin/env python3
"""
Corrected ingestion script with proper authentication and data clearing.
"""

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from pymilvus import MilvusClient, DataType
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config with proper authentication
MILVUS_URI = "http://milvus-standalone:19530"
MONGO_URL = "mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@mongodb:27017/chat_mongodb?authSource=admin"
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
COLLECTION_NAME = "colqwen" + KB_ID.replace("-", "_")
USERNAME = "thesis"
EMBEDDINGS_DIR = "/app/embeddings_output"
BATCH_SIZE = 2000


async def clear_existing_data(milvus, mongo_db, clear_milvus=True, clear_mongo=True):
    """Clear existing data from both databases."""
    if clear_milvus:
        logger.info(f"Clearing Milvus collection: {COLLECTION_NAME}")
        if milvus.has_collection(COLLECTION_NAME):
            milvus.drop_collection(COLLECTION_NAME)
            logger.info("Milvus collection dropped")

    if clear_mongo:
        logger.info("Clearing MongoDB file metadata...")
        # Delete files in knowledge base
        result = await mongo_db.files.delete_many({"knowledge_db_id": KB_ID})
        logger.info(f"Deleted {result.deleted_count} files from MongoDB")

        # Delete knowledge base
        await mongo_db.knowledge_bases.delete_many({"knowledge_base_id": KB_ID})
        logger.info("Knowledge base deleted from MongoDB")


async def ensure_knowledge_base(db):
    """Ensure knowledge base exists."""
    kb = await db.knowledge_bases.find_one({"knowledge_base_id": KB_ID})
    if not kb:
        logger.info("Creating knowledge base")
        await db.knowledge_bases.insert_one(
            {
                "username": USERNAME,
                "knowledge_base_name": "Thesis Corpus",
                "knowledge_base_id": KB_ID,
                "is_temp": False,
                "created_at": datetime.now(),
                "last_modify_at": datetime.now(),
            }
        )


def create_milvus_collection(milvus):
    """Create Milvus collection with proper schema."""
    if milvus.has_collection(COLLECTION_NAME):
        logger.warning(f"Collection {COLLECTION_NAME} already exists, dropping...")
        milvus.drop_collection(COLLECTION_NAME)

    logger.info(f"Creating Milvus collection: {COLLECTION_NAME}")
    schema = milvus.create_schema(auto_id=True, enable_dynamic_fields=True)
    schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=128)
    schema.add_field(field_name="image_id", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(field_name="file_id", datatype=DataType.VARCHAR, max_length=65535)

    milvus.create_collection(collection_name=COLLECTION_NAME, schema=schema)

    # Create index
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
    logger.info("Milvus collection created and loaded")


async def process_file(milvus, db, json_file, file_counter, total_files):
    """Process a single JSON file."""
    try:
        logger.info(f"[{file_counter}/{total_files}] Processing {json_file}")

        # Load embeddings
        json_path = os.path.join(EMBEDDINGS_DIR, json_file)
        with open(json_path, "r") as f:
            data = json.load(f)

        pdf_filename = json_file.replace(".json", "")
        file_id = f"{USERNAME}_{uuid.uuid4()}"  # Unique per file

        # Insert vectors in batches
        batch_data = []
        total_file_vectors = 0

        for page in data:
            page_num = page["page_number"]
            image_id = f"{file_id}_{page_num}"

            for vec in page["embedding"]:
                # Sanitize vector
                sanitized = [
                    0.0 if not isinstance(x, (int, float)) or not abs(x) < 1e100 else x
                    for x in vec
                ]
                batch_data.append(
                    {
                        "vector": sanitized,
                        "image_id": image_id,
                        "page_number": page_num,
                        "file_id": file_id,
                    }
                )

                if len(batch_data) >= BATCH_SIZE:
                    milvus.insert(collection_name=COLLECTION_NAME, data=batch_data)
                    total_file_vectors += len(batch_data)
                    batch_data = []

        # Insert remaining
        if batch_data:
            milvus.insert(collection_name=COLLECTION_NAME, data=batch_data)
            total_file_vectors += len(batch_data)

        # Save metadata (skip MinIO for now)
        await db.files.insert_one(
            {
                "file_id": file_id,
                "username": USERNAME,
                "file_name": pdf_filename,
                "knowledge_db_id": KB_ID,
                "status": "parsed",
                "minio_url": "",  # Empty for now
                "file_size": 0,
                "created_at": datetime.now(),
                "last_modify_at": datetime.now(),
            }
        )

        logger.info(
            f"✓ Completed {json_file} ({len(data)} pages, {total_file_vectors} vectors)"
        )
        return total_file_vectors, True

    except Exception as e:
        logger.error(f"Failed to process {json_file}: {e}")
        return 0, False


async def main():
    """Main ingestion pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest thesis corpus with proper authentication"
    )
    parser.add_argument(
        "--clear", action="store_true", help="Clear existing data before ingestion"
    )
    args = parser.parse_args()

    logger.info("🚀 Starting corrected ingestion pipeline")
    if args.clear:
        logger.info("Clearing existing data enabled")

    # Connect to Milvus
    milvus = MilvusClient(uri=MILVUS_URI)

    # Connect to MongoDB with proper authentication
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.chat_mongodb

    try:
        # Clear existing data if requested
        if args.clear:
            await clear_existing_data(milvus, db, clear_milvus=True, clear_mongo=True)

        # Create Milvus collection (fresh)
        create_milvus_collection(milvus)

        # Ensure knowledge base exists
        await ensure_knowledge_base(db)

        # Get all JSON files
        json_files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.endswith(".json")]
        total_files = len(json_files)
        logger.info(f"Found {total_files} embedding files to process")

        # Process files sequentially (for simplicity and debugging)
        total_vectors = 0
        successful_files = 0

        for i, json_file in enumerate(json_files, 1):
            vectors, success = await process_file(milvus, db, json_file, i, total_files)
            total_vectors += vectors
            if success:
                successful_files += 1

        logger.info("=" * 60)
        logger.info(f"🎉 INGESTION COMPLETE")
        logger.info(f"  Files processed: {successful_files}/{total_files}")
        logger.info(f"  Total vectors: {total_vectors:,}")
        logger.info(f"  Milvus collection: {COLLECTION_NAME}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Close connections
        milvus.close()
        mongo.close()


if __name__ == "__main__":
    asyncio.run(main())

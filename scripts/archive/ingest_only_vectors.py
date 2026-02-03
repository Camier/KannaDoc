#!/usr/bin/env python3
"""
Minimal ingestion script - just insert vectors and metadata, skip problematic parts.
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

# Config
MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")
MONGO_URL = os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise ValueError("MONGODB_URL environment variable is not set.")
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
COLLECTION_NAME = "colqwen" + KB_ID.replace("-", "_")
USERNAME = "thesis"
EMBEDDINGS_DIR = "/app/embeddings_output"
CORPUS_DIR = "/app/literature/corpus"
BATCH_SIZE = 2000


async def main():
    logger.info("Starting minimal ingestion")

    # Connect to Milvus
    milvus = MilvusClient(uri=MILVUS_URI)

    # Ensure collection exists
    if not milvus.has_collection(COLLECTION_NAME):
        logger.info(f"Creating collection {COLLECTION_NAME}")
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

    # Connect to MongoDB
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.chat_mongodb

    # Ensure knowledge base exists
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

    # Process files
    json_files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.endswith(".json")]
    logger.info(f"Found {len(json_files)} files to process")

    total_vectors = 0
    processed_files = 0

    for json_file in json_files:
        try:
            logger.info(f"Processing {json_file}")

            # Load embeddings
            json_path = os.path.join(EMBEDDINGS_DIR, json_file)
            with open(json_path, "r") as f:
                data = json.load(f)

            pdf_filename = json_file.replace(".json", "")
            file_id = f"{USERNAME}_{uuid.uuid4()}"

            # Insert vectors in batches
            batch_data = []
            for page in data:
                page_num = page["page_number"]
                image_id = f"{file_id}_{page_num}"

                for vec in page["embedding"]:
                    # Sanitize vector (replace NaN/Inf)
                    sanitized = [
                        0.0
                        if not isinstance(x, (int, float)) or not abs(x) < 1e100
                        else x
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
                        total_vectors += len(batch_data)
                        batch_data = []

            # Insert remaining
            if batch_data:
                milvus.insert(collection_name=COLLECTION_NAME, data=batch_data)
                total_vectors += len(batch_data)

            # Save metadata (skip MinIO URL for now)
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

            processed_files += 1
            logger.info(
                f"✓ Completed {json_file} ({len(data)} pages, {total_vectors} vectors total)"
            )

        except Exception as e:
            logger.error(f"Failed to process {json_file}: {e}")

    logger.info(
        f"🎉 Ingestion complete: {processed_files}/{len(json_files)} files, {total_vectors} vectors"
    )

    # Close connections
    milvus.close()
    mongo.close()


if __name__ == "__main__":
    asyncio.run(main())

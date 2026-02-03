#!/usr/bin/env python3
"""
Final ingestion script for thesis corpus with proper environment variables and error handling.
"""

import os
import sys
import json
import uuid
import asyncio
import logging
import math
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import signal

import numpy as np
from pymilvus import MilvusClient, DataType, MilvusException
from motor.motor_asyncio import AsyncIOMotorClient
import aioboto3
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


# ============= CONFIGURATION =============
@dataclass
class Config:
    """Configuration from environment variables."""

    # Database connections
    mongo_url: str = os.getenv("MONGODB_URL", "")
    milvus_uri: str = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")
    minio_url: str = os.getenv("MINIO_URL", "http://minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "thesis_minio")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_bucket: str = os.getenv("MINIO_BUCKET_NAME", "minio-file")

    # Paths (inside container)
    embeddings_dir: str = "/app/embeddings_output"
    corpus_dir: str = "/app/literature/corpus"

    # Thesis data
    username: str = "thesis"
    kb_id: str = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
    kb_name: str = "Thesis Corpus"

    # Performance tuning
    batch_size: int = 2000  # Optimal batch size for Milvus insertion
    max_concurrent_files: int = 2  # Conservative concurrency
    max_retries: int = 3  # Retry attempts
    vector_dimension: int = 128  # ColQwen embedding dimension

    # Collection name
    @property
    def collection_name(self) -> str:
        return "colqwen" + self.kb_id.replace("-", "_")

    # Checkpoint file
    checkpoint_file: str = "/app/ingestion_checkpoint.json"

    def validate(self):
        """Validate critical settings."""
        missing = []
        if not self.mongo_url:
            missing.append("MONGODB_URL")
        if not self.minio_secret_key:
            missing.append("MINIO_SECRET_KEY")
        if missing:
            raise ValueError(
                f"CRITICAL SECURITY ERROR: Missing required environment variables: {', '.join(missing)}"
            )


config = Config()
config.validate()

# ============= LOGGING =============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/ingestion_final.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============= MAIN INGESTION CLASS =============
class ThesisIngestion:
    """Main ingestion class."""

    def __init__(self, clear_existing: bool = False):
        self.clear_existing = clear_existing
        self.milvus_client = None
        self.mongo_client = None
        self.minio_session = None
        self.processed_files = []
        self.failed_files = {}
        self.total_vectors = 0
        self.start_time = time.time()

    async def connect(self):
        """Connect to all databases."""
        logger.info("Connecting to databases...")

        # Milvus
        self.milvus_client = MilvusClient(uri=config.milvus_uri)
        logger.info(f"Connected to Milvus at {config.milvus_uri}")

        # MongoDB
        self.mongo_client = AsyncIOMotorClient(config.mongo_url)
        await self.mongo_client.admin.command("ping")
        logger.info(f"Connected to MongoDB at {config.mongo_url}")

        # MinIO session
        self.minio_session = aioboto3.Session()
        logger.info("MinIO session initialized")

    async def disconnect(self):
        """Disconnect from databases."""
        if self.milvus_client:
            self.milvus_client.close()
            logger.info("Milvus connection closed")

        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")

    async def ensure_minio_bucket(self):
        """Ensure MinIO bucket exists."""
        try:
            async with self.minio_session.client(
                "s3",
                endpoint_url=config.minio_url,
                aws_access_key_id=config.minio_access_key,
                aws_secret_access_key=config.minio_secret_key,
            ) as s3:
                await s3.create_bucket(Bucket=config.minio_bucket)
                logger.info(f"MinIO bucket '{config.minio_bucket}' created or exists")
        except Exception as e:
            logger.warning(f"MinIO bucket check failed (may already exist): {e}")

    async def upload_to_minio(self, file_path: str, object_name: str) -> Optional[str]:
        """Upload file to MinIO, return object name if successful."""
        try:
            async with self.minio_session.client(
                "s3",
                endpoint_url=config.minio_url,
                aws_access_key_id=config.minio_access_key,
                aws_secret_access_key=config.minio_secret_key,
            ) as s3:
                await s3.upload_file(file_path, config.minio_bucket, object_name)
                logger.info(f"Uploaded {file_path} to MinIO as {object_name}")
                return object_name
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to MinIO: {e}")
            return None

    async def setup_collection(self):
        """Setup Milvus collection, clear if requested."""
        collection_name = config.collection_name

        if self.clear_existing and self.milvus_client.has_collection(collection_name):
            logger.info(f"Clearing existing collection: {collection_name}")
            self.milvus_client.drop_collection(collection_name)

        if not self.milvus_client.has_collection(collection_name):
            logger.info(f"Creating Milvus collection: {collection_name}")
            schema = self.milvus_client.create_schema(
                auto_id=True, enable_dynamic_fields=True
            )
            schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
            schema.add_field(
                field_name="vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=config.vector_dimension,
            )
            schema.add_field(
                field_name="image_id", datatype=DataType.VARCHAR, max_length=65535
            )
            schema.add_field(field_name="page_number", datatype=DataType.INT64)
            schema.add_field(
                field_name="file_id", datatype=DataType.VARCHAR, max_length=65535
            )

            self.milvus_client.create_collection(
                collection_name=collection_name, schema=schema
            )

            # Create index
            idx_params = self.milvus_client.prepare_index_params()
            idx_params.add_index(
                field_name="vector",
                index_name="vector_index",
                index_type="HNSW",
                metric_type="IP",
                params={"M": 32, "efConstruction": 500},
            )
            self.milvus_client.create_index(
                collection_name=collection_name, index_params=idx_params
            )

        # Load collection
        self.milvus_client.load_collection(collection_name)
        logger.info(f"Collection {collection_name} is ready")

    async def ensure_knowledge_base(self):
        """Ensure knowledge base exists in MongoDB."""
        db = self.mongo_client.chat_mongodb

        # Clear existing files if clearing
        if self.clear_existing:
            logger.info("Clearing existing file metadata...")
            await db.files.delete_many({"knowledge_db_id": config.kb_id})
            await db.knowledge_bases.delete_many({"knowledge_base_id": config.kb_id})

        # Create knowledge base
        kb = await db.knowledge_bases.find_one({"knowledge_base_id": config.kb_id})
        if not kb:
            logger.info(f"Creating knowledge base: {config.kb_name}")
            await db.knowledge_bases.insert_one(
                {
                    "username": config.username,
                    "knowledge_base_name": config.kb_name,
                    "knowledge_base_id": config.kb_id,
                    "is_temp": False,
                    "created_at": datetime.now(),
                    "last_modify_at": datetime.now(),
                }
            )

    def sanitize_vector(self, vector: List[float]) -> List[float]:
        """Replace NaN/Inf with zeros."""
        return [0.0 if not math.isfinite(x) else x for x in vector]

    async def insert_file_embeddings(self, file_id: str, json_path: str) -> int:
        """Insert embeddings from a JSON file."""
        with open(json_path, "r") as f:
            data = json.load(f)

        total_vectors = 0
        batch_data = []

        for page in data:
            page_num = page["page_number"]
            image_id = f"{file_id}_{page_num}"
            embeddings = page["embedding"]

            for vec in embeddings:
                # Sanitize vector
                sanitized_vec = self.sanitize_vector(vec)

                batch_data.append(
                    {
                        "vector": sanitized_vec,
                        "image_id": image_id,
                        "page_number": page_num,
                        "file_id": file_id,
                    }
                )

                # Insert in batches
                if len(batch_data) >= config.batch_size:
                    try:
                        self.milvus_client.insert(
                            collection_name=config.collection_name, data=batch_data
                        )
                        total_vectors += len(batch_data)
                        batch_data = []
                    except Exception as e:
                        logger.error(f"Batch insertion failed: {e}")
                        # Retry with smaller batch
                        if config.batch_size > 500:
                            config.batch_size = 500
                        raise

        # Insert remaining
        if batch_data:
            self.milvus_client.insert(
                collection_name=config.collection_name, data=batch_data
            )
            total_vectors += len(batch_data)

        return total_vectors

    async def process_file(self, json_filename: str) -> bool:
        """Process a single file."""
        try:
            logger.info(f"Processing {json_filename}")

            json_path = os.path.join(config.embeddings_dir, json_filename)
            pdf_filename = json_filename.replace(".json", "")
            file_id = f"{config.username}_{uuid.uuid4()}"

            # Find PDF
            pdf_path = os.path.join(config.corpus_dir, pdf_filename)
            if not os.path.exists(pdf_path):
                for root, dirs, files in os.walk(config.corpus_dir):
                    if pdf_filename in files:
                        pdf_path = os.path.join(root, pdf_filename)
                        break

            # Upload to MinIO
            minio_url = ""
            if os.path.exists(pdf_path):
                object_name = f"{config.username}/{file_id}/{pdf_filename}"
                minio_url = await self.upload_to_minio(pdf_path, object_name)
                if not minio_url:
                    logger.warning(
                        f"MinIO upload failed for {pdf_filename}, continuing without"
                    )
            else:
                logger.warning(f"PDF not found: {pdf_filename}")

            # Insert embeddings
            vector_count = await self.insert_file_embeddings(file_id, json_path)
            logger.info(f"Inserted {vector_count} vectors for {pdf_filename}")

            # Save metadata to MongoDB
            db = self.mongo_client.chat_mongodb
            await db.files.insert_one(
                {
                    "file_id": file_id,
                    "username": config.username,
                    "file_name": pdf_filename,
                    "knowledge_db_id": config.kb_id,
                    "status": "parsed",
                    "minio_url": minio_url if minio_url else "",
                    "file_size": os.path.getsize(pdf_path)
                    if os.path.exists(pdf_path)
                    else 0,
                    "created_at": datetime.now(),
                    "last_modify_at": datetime.now(),
                }
            )

            self.processed_files.append(json_filename)
            self.total_vectors += vector_count

            logger.info(f"✓ Completed {json_filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to process {json_filename}: {e}")
            self.failed_files[json_filename] = str(e)
            return False

    async def run(self):
        """Run the full ingestion pipeline."""
        logger.info("🚀 Starting thesis corpus ingestion")
        logger.info(f"Clear existing: {self.clear_existing}")

        await self.connect()
        await self.ensure_minio_bucket()
        await self.setup_collection()
        await self.ensure_knowledge_base()

        # Get all JSON files
        all_files = [
            f for f in os.listdir(config.embeddings_dir) if f.endswith(".json")
        ]
        logger.info(f"Found {len(all_files)} embedding files")

        # Process files with limited concurrency
        semaphore = asyncio.Semaphore(config.max_concurrent_files)

        async def process_with_semaphore(filename):
            async with semaphore:
                return await self.process_file(filename)

        tasks = [process_with_semaphore(f) for f in all_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Summarize results
        success_count = sum(1 for r in results if r is True)
        fail_count = sum(1 for r in results if r is False)

        elapsed = time.time() - self.start_time
        logger.info("=" * 60)
        logger.info(f"🎉 INGESTION COMPLETE")
        logger.info(f"  Time elapsed: {elapsed:.1f}s")
        logger.info(f"  Total files: {len(all_files)}")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Failed: {fail_count}")
        logger.info(f"  Total vectors: {self.total_vectors}")
        logger.info("=" * 60)

        if self.failed_files:
            logger.warning("Failed files:")
            for f, e in self.failed_files.items():
                logger.warning(f"  {f}: {e}")

        await self.disconnect()


# ============= MAIN =============
async def main():
    parser = argparse.ArgumentParser(
        description="Ingest thesis corpus to Milvus and MongoDB"
    )
    parser.add_argument(
        "--clear", action="store_true", help="Clear existing data before ingestion"
    )
    args = parser.parse_args()

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        pipeline = ThesisIngestion(clear_existing=args.clear)
        await pipeline.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

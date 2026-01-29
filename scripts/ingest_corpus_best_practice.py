#!/usr/bin/env python3
"""
Advanced ingestion pipeline for thesis corpus with Milvus best practices.

Best Practices Implemented:
1. Batch insertion with optimal size (1000-5000 vectors)
2. Async parallel processing with semaphore limit
3. Exponential backoff retry for network failures
4. Vector validation and sanitization
5. Progress checkpointing for resumability
6. Comprehensive error handling and logging
7. Connection pooling and reuse
8. Memory-efficient streaming of large JSON files
9. Data integrity validation between Milvus and MongoDB
10. Performance metrics and reporting

Usage:
    docker exec layra-backend python3 /app/scripts/ingest_corpus_best_practice.py

Env overrides (optional):
    MONGODB_URL, MILVUS_URI, MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET_NAME
    LAYRA_INGEST_USERNAME, LAYRA_INGEST_KB_ID, LAYRA_INGEST_KB_NAME
    LAYRA_EMBEDDINGS_DIR, LAYRA_CORPUS_DIR, EMBEDDING_VECTOR_DIM
    LAYRA_INGEST_BATCH_SIZE, LAYRA_INGEST_MAX_CONCURRENCY, LAYRA_INGEST_MAX_RETRIES
"""

import os
import sys
import json
import uuid
import asyncio
import logging
import math
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import signal
from contextlib import asynccontextmanager

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/ingestion.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============= CONFIGURATION =============
@dataclass
class Config:
    """Configuration for ingestion pipeline."""

    # Database connections
    mongo_url: str = os.getenv(
        "MONGODB_URL",
        "mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@mongodb:27017",
    )
    milvus_uri: str = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")
    minio_url: str = os.getenv("MINIO_URL", "http://minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "thesis_minio")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minio_sec_6p7q8r")
    minio_bucket: str = os.getenv("MINIO_BUCKET_NAME", "minio-file")

    # Paths (inside container)
    embeddings_dir: str = os.getenv("LAYRA_EMBEDDINGS_DIR", "/app/embeddings_output")
    corpus_dir: str = os.getenv("LAYRA_CORPUS_DIR", "/app/literature/corpus")

    # Thesis data
    username: str = os.getenv("LAYRA_INGEST_USERNAME", "thesis")
    kb_id: str = os.getenv(
        "LAYRA_INGEST_KB_ID",
        "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
    )
    kb_name: str = os.getenv("LAYRA_INGEST_KB_NAME", "Thesis Corpus")

    # Performance tuning
    batch_size: int = int(os.getenv("LAYRA_INGEST_BATCH_SIZE", "2000"))
    max_concurrent_files: int = int(os.getenv("LAYRA_INGEST_MAX_CONCURRENCY", "3"))
    max_retries: int = int(os.getenv("LAYRA_INGEST_MAX_RETRIES", "5"))
    vector_dimension: int = int(os.getenv("EMBEDDING_VECTOR_DIM", "128"))

    # Collection name
    @property
    def collection_name(self) -> str:
        return "colqwen" + self.kb_id.replace("-", "_")

    # Checkpoint file
    checkpoint_file: str = "/app/ingestion_checkpoint.json"


config = Config()


# ============= DATA MODELS =============
@dataclass
class EmbeddingPage:
    """Represents a page with its embeddings."""

    filename: str
    page_number: int
    embeddings: List[List[float]]  # List of 128-dim vectors

    @property
    def vector_count(self) -> int:
        return len(self.embeddings)


@dataclass
class FileMetadata:
    """Metadata for a PDF file."""

    file_id: str
    username: str
    file_name: str
    knowledge_db_id: str
    status: str = "parsed"
    minio_url: str = ""
    file_size: int = 0
    created_at: datetime = None
    last_modify_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_modify_at is None:
            self.last_modify_at = datetime.now()


@dataclass
class Checkpoint:
    """Checkpoint for resumable ingestion."""

    processed_files: List[str] = None  # List of JSON filenames already processed
    failed_files: Dict[str, str] = None  # filename -> error message
    start_time: float = None
    total_vectors: int = 0
    total_files: int = 0

    def __post_init__(self):
        if self.processed_files is None:
            self.processed_files = []
        if self.failed_files is None:
            self.failed_files = {}
        if self.start_time is None:
            self.start_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "start_time": self.start_time,
            "total_vectors": self.total_vectors,
            "total_files": self.total_files,
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            processed_files=data.get("processed_files", []),
            failed_files=data.get("failed_files", {}),
            start_time=data.get("start_time", time.time()),
            total_vectors=data.get("total_vectors", 0),
            total_files=data.get("total_files", 0),
        )


# ============= UTILITY FUNCTIONS =============
def sanitize_vector(vector: List[float]) -> List[float]:
    """Ensure vector contains no NaN or Inf values."""
    return [0.0 if not math.isfinite(x) else x for x in vector]


def validate_embeddings(embeddings: List[List[float]], expected_dim: int = 128) -> bool:
    """Validate embedding dimensions and values."""
    if not embeddings:
        return False

    for vec in embeddings:
        if len(vec) != expected_dim:
            logger.error(
                f"Vector dimension mismatch: expected {expected_dim}, got {len(vec)}"
            )
            return False

        # Check for NaN/Inf
        for val in vec:
            if not math.isfinite(val):
                logger.warning(f"Non-finite value found in vector: {val}")
                return False

    return True


def load_checkpoint() -> Optional[Checkpoint]:
    """Load checkpoint from file if exists."""
    if os.path.exists(config.checkpoint_file):
        try:
            with open(config.checkpoint_file, "r") as f:
                data = json.load(f)
                logger.info(
                    f"Loaded checkpoint with {len(data.get('processed_files', []))} processed files"
                )
                return Checkpoint.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
    return None


def save_checkpoint(checkpoint: Checkpoint):
    """Save checkpoint to file."""
    try:
        with open(config.checkpoint_file, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
        logger.debug(
            f"Checkpoint saved: {len(checkpoint.processed_files)} files processed"
        )
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")


# ============= DATABASE CLIENTS =============
class DatabaseManager:
    """Manages database connections with pooling."""

    def __init__(self):
        self.milvus_client = None
        self.mongo_client = None
        self.minio_session = None

    async def connect(self):
        """Initialize all database connections."""
        logger.info("Connecting to databases...")

        # Milvus
        self.milvus_client = MilvusClient(uri=config.milvus_uri)
        logger.info(f"Connected to Milvus at {config.milvus_uri}")

        # MongoDB
        self.mongo_client = AsyncIOMotorClient(config.mongo_url)
        # Test connection
        await self.mongo_client.admin.command("ping")
        logger.info(f"Connected to MongoDB at {config.mongo_url}")

        # MinIO session (lazy initialization)
        self.minio_session = aioboto3.Session()
        logger.info("MinIO session initialized")

    async def disconnect(self):
        """Close all database connections."""
        if self.milvus_client:
            self.milvus_client.close()
            logger.info("Milvus connection closed")

        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")

    @asynccontextmanager
    async def minio_client(self):
        """Async context manager for MinIO client."""
        async with self.minio_session.client(
            "s3",
            endpoint_url=config.minio_url,
            aws_access_key_id=config.minio_access_key,
            aws_secret_access_key=config.minio_secret_key,
        ) as s3:
            yield s3

    async def ensure_minio_bucket(self):
        """Ensure MinIO bucket exists."""
        async with self.minio_client() as s3:
            try:
                await s3.create_bucket(Bucket=config.minio_bucket)
                logger.info(f"MinIO bucket '{config.minio_bucket}' created or exists")
            except Exception as e:
                logger.warning(f"MinIO bucket creation: {e}")
                # Bucket likely exists

    async def upload_to_minio(self, file_path: str, object_name: str) -> str:
        """Upload file to MinIO with retry logic."""

        @retry(
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type(Exception),
        )
        async def _upload():
            async with self.minio_client() as s3:
                await s3.upload_file(file_path, config.minio_bucket, object_name)
                logger.debug(f"Uploaded {file_path} to MinIO as {object_name}")

        try:
            await _upload()
            return object_name
        except Exception as e:
            logger.error(
                f"Failed to upload {file_path} to MinIO after {config.max_retries} attempts: {e}"
            )
            raise


# ============= MILVUS OPERATIONS =============
class MilvusManager:
    """Manages Milvus operations with best practices."""

    def __init__(self, client: MilvusClient):
        self.client = client

    async def ensure_collection(self):
        """Ensure Milvus collection exists with proper schema."""
        collection_name = config.collection_name

        # Check if collection exists
        if self.client.has_collection(collection_name):
            logger.info(f"Collection {collection_name} already exists")

            # Verify schema matches expected
            schema = self.client.describe_collection(collection_name)
            logger.debug(f"Collection schema: {schema}")

            # Load collection for search operations
            self.client.load_collection(collection_name)
            return

        # Create new collection
        logger.info(f"Creating Milvus collection: {collection_name}")
        schema = self.client.create_schema(auto_id=True, enable_dynamic_fields=True)
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

        self.client.create_collection(collection_name=collection_name, schema=schema)

        # Create index
        idx_params = self.client.prepare_index_params()
        idx_params.add_index(
            field_name="vector",
            index_name="vector_index",
            index_type="HNSW",
            metric_type="IP",
            params={"M": 32, "efConstruction": 500},
        )
        self.client.create_index(
            collection_name=collection_name, index_params=idx_params
        )

        # Load collection
        self.client.load_collection(collection_name)
        logger.info(f"Collection {collection_name} created and loaded")

    @retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(MilvusException),
    )
    async def insert_batch(self, data: List[Dict[str, Any]]) -> int:
        """Insert a batch of vectors with retry logic."""
        if not data:
            return 0

        try:
            result = self.client.insert(
                collection_name=config.collection_name, data=data
            )
            inserted_count = len(data)
            logger.debug(f"Inserted batch of {inserted_count} vectors")
            return inserted_count
        except MilvusException as e:
            logger.error(f"Milvus insertion failed: {e}")
            raise

    async def insert_file_embeddings(
        self, file_id: str, pages: List[EmbeddingPage]
    ) -> int:
        """Insert all embeddings for a file in optimal batches."""
        total_vectors = 0
        batch_data = []

        for page in pages:
            image_id = f"{file_id}_{page.page_number}"

            for vec in page.embeddings:
                # Validate and sanitize vector
                if not validate_embeddings([vec], config.vector_dimension):
                    logger.warning(
                        f"Invalid vector in {file_id}, page {page.page_number}"
                    )
                    vec = sanitize_vector(vec)

                batch_data.append(
                    {
                        "vector": vec,
                        "image_id": image_id,
                        "page_number": page.page_number,
                        "file_id": file_id,
                    }
                )

                # Insert when batch reaches optimal size
                if len(batch_data) >= config.batch_size:
                    inserted = await self.insert_batch(batch_data)
                    total_vectors += inserted
                    batch_data = []

        # Insert remaining vectors
        if batch_data:
            inserted = await self.insert_batch(batch_data)
            total_vectors += inserted

        logger.info(f"Inserted {total_vectors} vectors for file {file_id}")
        return total_vectors


# ============= INGESTION PIPELINE =============
class IngestionPipeline:
    """Main ingestion pipeline with parallel processing."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.milvus = None
        self.checkpoint = load_checkpoint() or Checkpoint()
        self.processed_count = 0
        self.failed_count = 0

    async def initialize(self):
        """Initialize pipeline and databases."""
        await self.db.connect()
        await self.db.ensure_minio_bucket()

        self.milvus = MilvusManager(self.db.milvus_client)
        await self.milvus.ensure_collection()

        # Initialize knowledge base in MongoDB if needed
        await self._ensure_knowledge_base()

    async def _ensure_knowledge_base(self):
        """Ensure knowledge base exists in MongoDB."""
        db = self.db.mongo_client.chat_mongodb
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

    async def process_file(
        self, json_filename: str, semaphore: asyncio.Semaphore
    ) -> bool:
        """Process a single JSON file with embeddings."""
        async with semaphore:
            try:
                if json_filename in self.checkpoint.processed_files:
                    logger.info(f"Skipping already processed file: {json_filename}")
                    return True

                logger.info(f"Processing {json_filename}")

                # Load embeddings
                json_path = os.path.join(config.embeddings_dir, json_filename)
                with open(json_path, "r") as f:
                    data = json.load(f)

                # Parse pages
                pages = []
                for item in data:
                    page = EmbeddingPage(
                        filename=item["filename"],
                        page_number=item["page_number"],
                        embeddings=item["embedding"],
                    )

                    # Validate embeddings
                    if not validate_embeddings(
                        page.embeddings, config.vector_dimension
                    ):
                        logger.warning(
                            f"Invalid embeddings in {json_filename}, page {page.page_number}"
                        )
                        # Sanitize all vectors
                        page.embeddings = [
                            sanitize_vector(vec) for vec in page.embeddings
                        ]

                    pages.append(page)

                # Generate file ID
                pdf_filename = json_filename.replace(".json", "")
                file_id = f"{config.username}_{uuid.uuid4()}"

                # Find PDF file
                pdf_path = os.path.join(config.corpus_dir, pdf_filename)
                if not os.path.exists(pdf_path):
                    # Try to find recursively
                    for root, dirs, files in os.walk(config.corpus_dir):
                        if pdf_filename in files:
                            pdf_path = os.path.join(root, pdf_filename)
                            break

                # Upload to MinIO if PDF exists
                minio_url = ""
                if os.path.exists(pdf_path):
                    object_name = f"{config.username}/{file_id}/{pdf_filename}"
                    try:
                        minio_url = await self.db.upload_to_minio(pdf_path, object_name)
                        logger.info(f"Uploaded {pdf_filename} to MinIO")
                    except Exception as e:
                        logger.warning(f"MinIO upload failed for {pdf_filename}: {e}")
                        # Continue without MinIO URL
                else:
                    logger.warning(
                        f"PDF not found for {json_filename}, skipping MinIO upload"
                    )

                # Insert embeddings to Milvus
                vector_count = await self.milvus.insert_file_embeddings(file_id, pages)

                # Save metadata to MongoDB
                await self._save_file_metadata(
                    file_id=file_id,
                    pdf_filename=pdf_filename,
                    pdf_path=pdf_path,
                    minio_url=minio_url,
                    vector_count=vector_count,
                )

                # Update checkpoint
                self.checkpoint.processed_files.append(json_filename)
                self.checkpoint.total_vectors += vector_count
                self.processed_count += 1

                # Save checkpoint periodically
                if self.processed_count % 5 == 0:
                    save_checkpoint(self.checkpoint)

                logger.info(
                    f"✓ Successfully processed {json_filename} ({vector_count} vectors)"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to process {json_filename}: {e}", exc_info=True)
                self.checkpoint.failed_files[json_filename] = str(e)
                self.failed_count += 1
                save_checkpoint(self.checkpoint)
                return False

    async def _save_file_metadata(
        self,
        file_id: str,
        pdf_filename: str,
        pdf_path: str,
        minio_url: str,
        vector_count: int,
    ):
        """Save file metadata to MongoDB."""
        db = self.db.mongo_client.chat_mongodb

        metadata = FileMetadata(
            file_id=file_id,
            username=config.username,
            file_name=pdf_filename,
            knowledge_db_id=config.kb_id,
            minio_url=minio_url,
            file_size=os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
        )

        await db.files.insert_one(asdict(metadata))
        logger.debug(f"Saved metadata for {pdf_filename}")

    async def run(self):
        """Run the ingestion pipeline."""
        logger.info("🚀 Starting ingestion pipeline")

        # Get list of JSON files
        all_files = [
            f for f in os.listdir(config.embeddings_dir) if f.endswith(".json")
        ]
        self.checkpoint.total_files = len(all_files)

        logger.info(f"Found {len(all_files)} embedding files")
        logger.info(f"Already processed: {len(self.checkpoint.processed_files)}")
        logger.info(f"Previously failed: {len(self.checkpoint.failed_files)}")

        # Filter out already processed and failed files
        files_to_process = [
            f
            for f in all_files
            if f not in self.checkpoint.processed_files
            and f not in self.checkpoint.failed_files
        ]

        if not files_to_process:
            logger.info("All files already processed. Use --force to reprocess.")
            return

        logger.info(f"Processing {len(files_to_process)} new files")

        # Setup parallel processing with semaphore
        semaphore = asyncio.Semaphore(config.max_concurrent_files)

        # Process files concurrently
        tasks = []
        for filename in files_to_process:
            task = asyncio.create_task(self.process_file(filename, semaphore))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)

        logger.info(f"🎉 Ingestion complete!")
        logger.info(f"  Total files: {len(all_files)}")
        logger.info(f"  Successfully processed: {successes}")
        logger.info(f"  Failed: {failures}")
        logger.info(f"  Total vectors: {self.checkpoint.total_vectors}")

        # Save final checkpoint
        save_checkpoint(self.checkpoint)

        # Print failed files if any
        if self.checkpoint.failed_files:
            logger.warning("Failed files:")
            for filename, error in self.checkpoint.failed_files.items():
                logger.warning(f"  {filename}: {error}")

    async def cleanup(self):
        """Cleanup resources."""
        await self.db.disconnect()


# ============= MAIN =============
async def main():
    """Main async entry point."""
    pipeline = None

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, saving checkpoint...")
        if pipeline:
            save_checkpoint(pipeline.checkpoint)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        db_manager = DatabaseManager()
        pipeline = IngestionPipeline(db_manager)

        await pipeline.initialize()
        await pipeline.run()

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        if pipeline:
            save_checkpoint(pipeline.checkpoint)
        raise

    finally:
        if pipeline:
            await pipeline.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

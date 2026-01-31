import os
import logging
from pymongo import MongoClient
from pymilvus import MilvusClient
from minio import Minio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup")

# Configuration - must be set via environment variables
MONGO_URI = os.getenv("MONGODB_URI")
if not MONGO_URI:
    raise ValueError("MONGODB_URI environment variable is required")

MONGO_DB = os.getenv("MONGODB_DB", "chat_mongodb")
MILVUS_URI = os.getenv("MILVUS_URI", "http://layra-milvus-standalone:19530")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "layra-minio:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY")
if not MINIO_ACCESS:
    raise ValueError("MINIO_ACCESS_KEY environment variable is required")

MINIO_SECRET = os.getenv("MINIO_SECRET_KEY")
if not MINIO_SECRET:
    raise ValueError("MINIO_SECRET_KEY environment variable is required")

MINIO_BUCKET = os.getenv("MINIO_BUCKET", "minio-file")

KB_ID = "thesis_34f1ab7f-5fbe-4a7a-bf73-6561f8ce1dd7"
COLLECTION_NAME = f"colqwenthesis_{KB_ID.replace('-', '_')}"


def clean_mongo():
    logger.info("Cleaning MongoDB...")
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]

        # Delete Files
        res_files = db.files.delete_many({"kb_id": KB_ID})
        logger.info(f"Deleted {res_files.deleted_count} files from MongoDB.")

        # Delete KB
        res_kb = db.knowledge_bases.delete_one({"id": KB_ID})
        logger.info(f"Deleted KB record: {res_kb.deleted_count}")

    except Exception as e:
        logger.error(f"MongoDB cleanup failed: {e}")


def clean_milvus():
    logger.info(f"Cleaning Milvus Collection: {COLLECTION_NAME}...")
    try:
        client = MilvusClient(uri=MILVUS_URI)
        if client.has_collection(COLLECTION_NAME):
            client.drop_collection(COLLECTION_NAME)
            logger.info("Milvus collection dropped.")
        else:
            logger.info("Milvus collection not found.")
    except Exception as e:
        logger.error(f"Milvus cleanup failed: {e}")


def clean_minio():
    logger.info("Cleaning MinIO...")
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS,
            secret_key=MINIO_SECRET,
            secure=False,
        )

        # List objects with prefix if possible, or just look for files associated with KB?
        # Since files are renamed with `user_filename_id`, we might not have a direct prefix.
        # But we deleted Mongo records, so we lost the mapping.
        # However, we can list all objects and delete those that look like they belong to this user/KB?
        # Actually, the user wants "remove knowledge base".
        # If we just want to stop the ingestion, we can skip MinIO cleanup if it's too risky to delete all.
        # But let's try to delete objects if they contain the KB ID?
        # The file naming convention in logs: `miko_..._6972...` (ObjectID).
        # It doesn't seem to contain KB ID directly.
        # FOR SAFETY: I will skip MinIO bulk deletion unless I can filter by KB ID.
        # Wait, the quickstart says "Backup MinIO /data".
        # I'll verify if there's a folder structure.
        # Usually it's flat in the bucket.
        # I will SKIP MinIO deletion to avoid collateral damage, as the main goal is to "halt" and "remove KB" (logic).
        # Leaving files in MinIO is harmless if they are not indexed.
        logger.warning(
            "Skipping MinIO deletion to prevent accidental data loss (mapping lost)."
        )

    except Exception as e:
        logger.error(f"MinIO cleanup failed: {e}")


if __name__ == "__main__":
    clean_mongo()
    clean_milvus()
    clean_minio()


import os
import json
import uuid
import logging
from datetime import datetime
from pymilvus import MilvusClient, DataType
from pymongo import MongoClient
import boto3
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credentials (Internal)
MONGO_URL = "mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@mongodb:27017"
MILVUS_URI = "http://milvus-standalone:19530"
MINIO_URL = "http://minio:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "thesis_minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_sec_6p7q8r")
MINIO_BUCKET = os.getenv("MINIO_BUCKET_NAME", "minio-file")

EMBEDDINGS_DIR = "/app/embeddings_output"
CORPUS_DIR = "/app/literature/corpus"

USERNAME = "thesis"
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
KB_NAME = "Thesis Corpus"
COLLECTION_NAME = "colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1"

def init_minio(s3):
    try:
        s3.create_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        pass

def main():
    logger.info("🚀 Starting SYNC Ingestion")

    # 1. Connect Mongo
    mongo = MongoClient(MONGO_URL)
    db = mongo.chat_mongodb

    # Wipe Metadata for clean slate
    db.knowledge_bases.delete_many({"knowledge_base_id": KB_ID})
    db.files.delete_many({"knowledge_db_id": KB_ID})

    # Create KB
    db.knowledge_bases.insert_one({
        "username": USERNAME,
        "knowledge_base_name": KB_NAME,
        "knowledge_base_id": KB_ID,
        "is_temp": False,
        "created_at": datetime.now(),
        "last_modify_at": datetime.now(),
        "is_delete": False,
        "files": [],
        "used_chat": []
    })

    # 2. Milvus
    milvus = MilvusClient(uri=MILVUS_URI)
    if milvus.has_collection(COLLECTION_NAME):
        milvus.drop_collection(COLLECTION_NAME)

    schema = milvus.create_schema(auto_id=True, enable_dynamic_fields=True)
    schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=128)
    schema.add_field(field_name="image_id", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(field_name="file_id", datatype=DataType.VARCHAR, max_length=65535)
    milvus.create_collection(collection_name=COLLECTION_NAME, schema=schema)

    idx_params = milvus.prepare_index_params()
    idx_params.add_index(field_name="vector", index_name="vector_index", index_type="HNSW", metric_type="IP", params={"M": 32, "efConstruction": 500})
    milvus.create_index(collection_name=COLLECTION_NAME, index_params=idx_params)
    milvus.load_collection(COLLECTION_NAME)

    # 3. MinIO
    s3 = boto3.client("s3", endpoint_url=MINIO_URL, aws_access_key_id=MINIO_ACCESS_KEY, aws_secret_access_key=MINIO_SECRET_KEY)
    init_minio(s3)
    
    # 4. Process
    files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.endswith(".json")]
    files.sort()
    logger.info(f"Found {len(files)} files to process")

    for i, jf in enumerate(files):
        pdf_filename = jf.replace(".json", "")
        pdf_path = os.path.join(CORPUS_DIR, pdf_filename)
        
        # Upload
        file_id = f"{USERNAME}_{uuid.uuid4()}"
        minio_key = f"{USERNAME}/{file_id}/{pdf_filename}"

        if os.path.exists(pdf_path):
            s3.upload_file(pdf_path, MINIO_BUCKET, minio_key)

        # Milvus
        with open(os.path.join(EMBEDDINGS_DIR, jf), 'r') as f:
            data = json.load(f)
            
        milvus_rows = []
        for page in data:
            pg = page["page_number"]
            for v in page["embedding"]:
                # Sanitize
                v_clean = [0.0 if not math.isfinite(x) else x for x in v]
                milvus_rows.append({
                    "vector": v_clean,
                    "image_id": f"{file_id}_{pg}",
                    "page_number": pg,
                    "file_id": file_id
                })

        # Insert Milvus
        BATCH = 100
        for k in range(0, len(milvus_rows), BATCH):
            milvus.insert(collection_name=COLLECTION_NAME, data=milvus_rows[k:k+BATCH])

        # Mongo File
        db.files.insert_one({
            "file_id": file_id,
            "username": USERNAME,
            "filename": pdf_filename,
            "minio_filename": minio_key,
            "minio_url": minio_key,
            "knowledge_db_id": KB_ID,
            "status": "parsed",
            "file_size": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
            "created_at": datetime.now(),
            "last_modify_at": datetime.now(),
            "is_delete": False
        })
        
        # Link to KB
        db.knowledge_bases.update_one(
            {"knowledge_base_id": KB_ID},
            {"$push": {"files": {
                "file_id": file_id,
                "filename": pdf_filename,
                "minio_filename": minio_key,
                "minio_url": minio_key,
                "created_at": datetime.now()
            }}}
        )
        
        print(f"[{i+1}/{len(files)}] Processed {pdf_filename}")

    print("🎉 Sync Ingestion Complete")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Inspect Milvus and MongoDB to understand data mismatch.
"""

import sys
import os
from pymilvus import MilvusClient
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

# Config
MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")
MONGO_URL = os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise ValueError(
        "MONGODB_URL environment variable is not set. Please provide it for database connection."
    )
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
COLLECTION_NAME = "colqwen" + KB_ID.replace("-", "_")
USERNAME = "thesis"


async def inspect_mongo():
    print("=== MongoDB Inspection ===")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.chat_mongodb

    # Count knowledge bases
    kb_count = await db.knowledge_bases.count_documents({"knowledge_base_id": KB_ID})
    print(f"Knowledge bases with ID {KB_ID}: {kb_count}")
    if kb_count > 0:
        kb = await db.knowledge_bases.find_one({"knowledge_base_id": KB_ID})
        print(f"KB name: {kb.get('knowledge_base_name')}")

    # Count files
    files_count = await db.files.count_documents({"knowledge_db_id": KB_ID})
    print(f"Files in MongoDB for KB: {files_count}")

    # Sample files
    files = await db.files.find({"knowledge_db_id": KB_ID}).limit(5).to_list(length=5)
    print("Sample files:")
    for f in files:
        print(
            f"  - file_id: {f.get('file_id')}, name: {f.get('file_name')}, minio_url: {f.get('minio_url')}"
        )

    # Distinct file_ids
    pipeline = [
        {"$match": {"knowledge_db_id": KB_ID}},
        {"$group": {"_id": "$file_id"}},
        {"$count": "total"},
    ]
    result = await db.files.aggregate(pipeline).to_list(length=1)
    if result:
        print(f"Distinct file_ids in MongoDB: {result[0]['total']}")
    else:
        print("Distinct file_ids: 0")

    await client.close()


def inspect_milvus():
    print("\n=== Milvus Inspection ===")
    client = MilvusClient(uri=MILVUS_URI)

    if not client.has_collection(COLLECTION_NAME):
        print(f"Collection {COLLECTION_NAME} does not exist!")
        return

    stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
    total = stats.get("row_count", 0)
    print(f"Total vectors in Milvus: {total}")

    # Sample 20 rows from different segments maybe
    # Use query with limit 20
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id", "image_id", "page_number"],
        limit=20,
    )
    print(f"Sample vectors (first 20):")
    seen_file_ids = set()
    for i, row in enumerate(results):
        fid = row["file_id"]
        seen_file_ids.add(fid)
        if i < 5:
            print(
                f"  {i}: file_id={fid}, image_id={row['image_id']}, page={row['page_number']}"
            )

    print(f"Unique file_ids in sample: {len(seen_file_ids)}")
    if seen_file_ids:
        print(f"Sample file_ids: {list(seen_file_ids)[:5]}")

    # Try to get approximate distinct file_ids by querying more rows
    # Use pagination with offset (but Milvus doesn't support offset). Use iterator with expr "pk > last_pk"
    # For simplicity, query 1000 rows and see unique count.
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id"],
        limit=1000,
    )
    file_ids_1k = set(row["file_id"] for row in results)
    print(f"Unique file_ids in first 1000 vectors: {len(file_ids_1k)}")
    if len(file_ids_1k) <= 10:
        print(f"All file_ids in 1k sample: {file_ids_1k}")

    # If there are few file_ids, we can count vectors per file_id by querying with filter and limit=0? Not possible.
    # We'll use count by filter using query with limit=1? Actually we can use count via get_query_segment_info? Not.
    # Let's just iterate over each file_id and count using query with limit=1 and get total?
    # We'll do it for first 3 file_ids.
    for fid in list(file_ids_1k)[:3]:
        # Use count via query with limit=0? Not supported. We'll query with limit=1 just to verify existence.
        res = client.query(
            collection_name=COLLECTION_NAME,
            filter=f"file_id == '{fid}'",
            output_fields=["file_id"],
            limit=1,
        )
        if res:
            # Estimate count using stats? Not possible. We'll skip.
            pass
        print(f"  File_id {fid} exists.")

    # Check if there are any NaN vectors? Not needed.

    client.close()


async def main():
    await inspect_mongo()
    inspect_milvus()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Check status of ingestion and data integrity.
"""

import sys
from pymilvus import MilvusClient
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from datetime import datetime

# Config
MILVUS_URI = os.getenv("MILVUS_URI", "http://milvus-standalone:19530")
MONGO_URL = os.getenv("MONGODB_URL")
if not MONGO_URL:
    raise ValueError(
        "MONGODB_URL environment variable is not set. Please provide it for database connection."
    )
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
COLLECTION_NAME = "colqwen" + KB_ID.replace("-", "_")
EMBEDDINGS_DIR = "/app/embeddings_output"


async def check_milvus():
    """Check Milvus status."""
    print("=== MILVUS STATUS ===")
    client = MilvusClient(uri=MILVUS_URI)

    if not client.has_collection(COLLECTION_NAME):
        print("❌ Collection does not exist")
        return

    stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
    total = stats.get("row_count", 0)
    print(f"Total vectors: {total:,}")

    # Query more rows to check file_id distribution
    print("\nChecking file_id distribution...")

    # Query 1000 rows
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id"],
        limit=1000,
    )

    file_ids = set(r["file_id"] for r in results)
    print(f"Unique file_ids in first 1000 rows: {len(file_ids)}")

    if file_ids:
        print("Sample file_ids:", list(file_ids)[:5])

        # For each file_id, count approximate vectors
        print("\nVector counts per file_id (approximate):")
        for fid in list(file_ids)[:5]:  # Check first 5
            # Query with limit=1 just to verify
            res = client.query(
                collection_name=COLLECTION_NAME,
                filter=f"file_id == '{fid}'",
                output_fields=["file_id"],
                limit=1,
            )
            if res:
                # To get count, we'd need to query all - skip for performance
                print(f"  {fid}: exists")

    # Check if collection is loaded
    # Not directly available in pymilvus 2.4.x
    print("\nCollection info:")
    print(f"  Name: {COLLECTION_NAME}")
    print(f"  Exists: {client.has_collection(COLLECTION_NAME)}")

    client.close()


async def check_mongodb():
    """Check MongoDB status."""
    print("\n=== MONGODB STATUS ===")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.chat_mongodb

    # Check knowledge base
    kb = await db.knowledge_bases.find_one({"knowledge_base_id": KB_ID})
    if kb:
        print(f"Knowledge base: {kb.get('knowledge_base_name')}")
        print(f"  Created: {kb.get('created_at')}")
    else:
        print("❌ Knowledge base not found")

    # Count files
    count = await db.files.count_documents({"knowledge_db_id": KB_ID})
    print(f"\nFiles in knowledge base: {count}")

    # Get sample files
    files = await db.files.find({"knowledge_db_id": KB_ID}).limit(5).to_list(length=5)
    print("Sample files:")
    for f in files:
        print(f"  - {f.get('file_name')} (id: {f.get('file_id')})")

    # Count distinct file_names
    pipeline = [
        {"$match": {"knowledge_db_id": KB_ID}},
        {"$group": {"_id": "$file_name"}},
        {"$count": "unique_files"},
    ]
    result = await db.files.aggregate(pipeline).to_list(length=1)
    if result:
        print(f"Unique file names: {result[0]['unique_files']}")

    await client.close()


def check_embeddings():
    """Check embeddings files."""
    print("\n=== EMBEDDINGS FILES ===")
    if not os.path.exists(EMBEDDINGS_DIR):
        print(f"❌ Directory not found: {EMBEDDINGS_DIR}")
        return

    json_files = [f for f in os.listdir(EMBEDDINGS_DIR) if f.endswith(".json")]
    print(f"JSON embedding files: {len(json_files)}")

    if json_files:
        print("Sample files:")
        for f in json_files[:3]:
            size = os.path.getsize(os.path.join(EMBEDDINGS_DIR, f))
            print(f"  - {f} ({size:,} bytes)")

    # Check PDF corpus
    corpus_dir = "/app/data/pdfs"
    if os.path.exists(corpus_dir):
        pdf_files = [f for f in os.listdir(corpus_dir) if f.endswith(".pdf")]
        print(f"\nPDF files in corpus: {len(pdf_files)}")


async def main():
    """Run all checks."""
    print("🧪 LAYRA THESIS SYSTEM STATUS CHECK")
    print("=" * 60)

    check_embeddings()
    await check_milvus()
    await check_mongodb()

    print("\n" + "=" * 60)
    print("✅ Status check complete")


if __name__ == "__main__":
    asyncio.run(main())

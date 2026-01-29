#!/usr/bin/env python3
"""
Test ingestion with a small sample.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest_corpus_best_practice import (
    Config,
    DatabaseManager,
    MilvusManager,
    EmbeddingPage,
)
import asyncio
import json
import uuid
from datetime import datetime


async def test_single_file():
    """Test processing a single file."""
    print("🧪 Testing ingestion with single file")

    # Use test configuration
    config = Config()

    # Initialize database connections
    db = DatabaseManager()
    await db.connect()

    try:
        # Initialize Milvus
        milvus = MilvusManager(db.milvus_client)
        await milvus.ensure_collection()

        # Pick a test JSON file
        test_files = [
            f for f in os.listdir(config.embeddings_dir) if f.endswith(".json")
        ]
        if not test_files:
            print("No JSON files found")
            return

        test_file = test_files[0]
        print(f"Testing with file: {test_file}")

        # Load embeddings
        json_path = os.path.join(config.embeddings_dir, test_file)
        with open(json_path, "r") as f:
            data = json.load(f)

        # Parse pages
        pages = []
        for item in data[:2]:  # Just first 2 pages for testing
            page = EmbeddingPage(
                filename=item["filename"],
                page_number=item["page_number"],
                embeddings=item["embedding"][:10],  # First 10 vectors per page
            )
            pages.append(page)

        # Generate file ID
        pdf_filename = test_file.replace(".json", "")
        file_id = f"{config.username}_test_{uuid.uuid4()}"

        # Insert embeddings
        print(f"Inserting embeddings for file_id: {file_id}")
        vector_count = await milvus.insert_file_embeddings(file_id, pages)

        print(f"✅ Successfully inserted {vector_count} vectors")

        # Verify insertion by querying
        # Query for the file_id we just inserted
        results = db.milvus_client.query(
            collection_name=config.collection_name,
            filter=f"file_id == '{file_id}'",
            output_fields=["file_id", "image_id", "page_number"],
            limit=5,
        )

        print(f"Verification query returned {len(results)} rows")
        for i, row in enumerate(results[:3]):
            print(
                f"  Row {i}: file_id={row['file_id']}, image_id={row['image_id']}, page={row['page_number']}"
            )

        # Cleanup: delete test vectors
        print(f"Cleaning up test vectors for file_id: {file_id}")
        db.milvus_client.delete(
            collection_name=config.collection_name, filter=f"file_id == '{file_id}'"
        )

        print("✅ Test completed successfully")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await db.disconnect()


async def test_minio_upload():
    """Test MinIO upload functionality."""
    print("\n🧪 Testing MinIO upload")

    config = Config()
    db = DatabaseManager()
    await db.connect()

    try:
        await db.ensure_minio_bucket()

        # Find a PDF file
        pdf_files = [f for f in os.listdir(config.corpus_dir) if f.endswith(".pdf")]
        if not pdf_files:
            print("No PDF files found")
            return

        test_pdf = pdf_files[0]
        pdf_path = os.path.join(config.corpus_dir, test_pdf)

        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            return

        # Upload to MinIO
        object_name = f"test/{uuid.uuid4()}/{test_pdf}"
        print(f"Uploading {test_pdf} to MinIO...")

        minio_url = await db.upload_to_minio(pdf_path, object_name)

        print(f"✅ Upload successful: {minio_url}")

    except Exception as e:
        print(f"❌ MinIO test failed: {e}")
    finally:
        await db.disconnect()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 LAYRA INGESTION PIPELINE TEST SUITE")
    print("=" * 60)

    await test_single_file()
    await test_minio_upload()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

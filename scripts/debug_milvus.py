#!/usr/bin/env python3
"""
Debug Milvus data and queries.
"""

import sys
from pymilvus import MilvusClient

# Config
MILVUS_URI = "http://milvus-standalone:19530"
KB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
COLLECTION_NAME = "colqwen" + KB_ID.replace("-", "_")


def main():
    print(f"Connecting to Milvus at {MILVUS_URI}")
    client = MilvusClient(uri=MILVUS_URI)

    if not client.has_collection(COLLECTION_NAME):
        print(f"Collection {COLLECTION_NAME} does not exist!")
        return

    print(f"Collection {COLLECTION_NAME} exists.")

    # Check if collection is loaded
    # Get collection stats
    stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
    print(f"Collection stats: {stats}")

    # Total row count
    total = stats.get("row_count", 0)
    print(f"Total vectors: {total}")

    # Query some sample data
    print("\nSample data (first 10 rows):")
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id", "image_id", "page_number"],
        limit=10,
    )

    for i, row in enumerate(results):
        print(
            f"  {i}: file_id={row['file_id']}, image_id={row['image_id']}, page={row['page_number']}"
        )

    # Count distinct file_ids
    print("\nCounting distinct file_ids (approximate)...")
    # Query more rows to see distribution
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id"],
        limit=1000,
    )

    file_ids = set(row["file_id"] for row in results)
    print(f"Unique file_ids in first 1000 rows: {len(file_ids)}")
    if file_ids:
        print(f"Sample file_ids: {list(file_ids)[:5]}")

    # Test query with specific file_id from earlier test
    test_file_id = "thesis_test_a00dd651-3185-48b2-a8ce-a4cc74788722"
    print(f"\nQuerying for test file_id: {test_file_id}")
    test_results = client.query(
        collection_name=COLLECTION_NAME,
        filter=f"file_id == '{test_file_id}'",
        output_fields=["file_id", "image_id", "page_number"],
        limit=10,
    )

    print(f"Found {len(test_results)} rows with test file_id")
    for i, row in enumerate(test_results):
        print(
            f"  {i}: file_id={row['file_id']}, image_id={row['image_id']}, page={row['page_number']}"
        )

    # Test search with random vector
    print("\nTesting vector search with random query...")
    import random

    random_vector = [[random.random() for _ in range(128)]]

    search_params = {"metric_type": "IP", "params": {"ef": 100}}
    search_results = client.search(
        collection_name=COLLECTION_NAME,
        data=random_vector,
        limit=5,
        output_fields=["file_id", "image_id", "page_number"],
        search_params=search_params,
    )

    if search_results:
        print(f"Search returned {len(search_results[0])} results")
        for i, hit in enumerate(search_results[0][:3]):
            print(
                f"  {i}: id={hit.id}, score={hit.score}, file_id={hit.entity.get('file_id')}"
            )

    client.close()


if __name__ == "__main__":
    main()

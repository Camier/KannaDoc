#!/usr/bin/env python3
"""
Inspect existing Milvus collection to understand current data.
"""

import sys

sys.path.insert(0, "/LAB/@thesis/layra/backend")

from pymilvus import MilvusClient
import os

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

    # Get total entity count
    stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
    print(f"Collection stats: {stats}")

    # Query distinct file_ids (need to iterate through segments or use query with limit)
    # Use query with output_fields=["file_id"] and limit=1000 to sample
    # For distinct values, we'll need to query all vectors (could be large). Use iterator.
    # Let's get first 10 rows to see structure.
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id", "image_id", "page_number"],
        limit=10,
    )
    print(f"Sample rows (first 10):")
    for i, row in enumerate(results):
        print(
            f"  {i}: file_id={row['file_id']}, image_id={row['image_id']}, page={row['page_number']}"
        )

    # Get distinct file_ids count using aggregation? Not directly supported.
    # We'll query with a large limit and use set.
    # But we can approximate with counting unique file_ids in first 1000 rows.
    results = client.query(
        collection_name=COLLECTION_NAME,
        filter="",
        output_fields=["file_id"],
        limit=1000,
    )
    file_ids = set(row["file_id"] for row in results)
    print(f"Unique file_ids in first 1000 rows: {len(file_ids)}")
    print(f"Sample file_ids: {list(file_ids)[:5]}")

    # Count vectors per file_id (approximate) - we'll do a query with filter for each file_id?
    # Too heavy. Let's just get total entity count per file_id using count?
    # Use count with filter.
    # We'll pick one sample file_id and count.
    if file_ids:
        sample_fid = next(iter(file_ids))
        count = client.count(
            collection_name=COLLECTION_NAME, filter=f"file_id == '{sample_fid}'"
        )
        print(f"Sample file_id '{sample_fid}' has {count} vectors")

    # Try to get total number of distinct file_ids via query with grouping? Not supported.
    # We'll need to iterate through all vectors using query iterator (cursor).
    # For now, we'll just get total entity count.
    total = client.count(collection_name=COLLECTION_NAME, filter="")
    print(f"Total vectors in collection: {total}")

    # Check if there are any NaN vectors (should be sanitized)
    # Not easy.

    print("\nInspection complete.")


if __name__ == "__main__":
    main()

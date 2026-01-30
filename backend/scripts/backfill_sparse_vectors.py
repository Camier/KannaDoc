#!/usr/bin/env python3
"""Async backfill job for sparse vectors.

This script iterates over all documents in Milvus collections that have empty
sparse vectors and generates them using the BGE-M3 model server endpoint.

Features:
- Checkpointing for resume after failure
- Rate limiting to prevent overload
- Progress tracking with ETA
- Skip documents that already have sparse vectors
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx
from pymilvus import MilvusClient

CHECKPOINT_FILE = Path("/tmp/backfill_sparse_checkpoint.json")
MODEL_SERVER_URL = os.environ.get("MODEL_SERVER_URL", "http://model-server:8005")
MILVUS_URI = os.environ.get("MILVUS_URI", "http://milvus-standalone:19530")


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"processed_pks": [], "last_offset": 0, "collection": None}


def save_checkpoint(checkpoint):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f)


async def fetch_sparse_embeddings(
    texts: list[str], timeout: float = 60.0
) -> list[dict]:
    if not texts:
        return []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MODEL_SERVER_URL}/embed_sparse",
                json={"texts": texts},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json().get("embeddings", [])
    except Exception as e:
        print(f"  [WARN] Sparse embedding failed: {e}")
        return []


def get_empty_sparse_count(client: MilvusClient, collection: str) -> int:
    try:
        result = client.query(
            collection,
            filter="",
            output_fields=["pk"],
            limit=1,
        )
        stats = client.get_collection_stats(collection)
        return stats.get("row_count", 0)
    except Exception:
        return 0


async def backfill_collection(
    collection: str,
    batch_size: int = 100,
    limit: int | None = None,
    dry_run: bool = False,
    rate_limit_delay: float = 0.5,
):
    print(f"\n{'=' * 60}")
    print(f"Backfilling collection: {collection}")
    print(
        f"Batch size: {batch_size}, Limit: {limit or 'unlimited'}, Dry run: {dry_run}"
    )
    print(f"{'=' * 60}\n")

    client = MilvusClient(uri=MILVUS_URI)

    if not client.has_collection(collection):
        print(f"[ERROR] Collection '{collection}' does not exist")
        return

    checkpoint = load_checkpoint()
    if checkpoint.get("collection") != collection:
        checkpoint = {"processed_pks": [], "last_offset": 0, "collection": collection}

    processed_set = set(checkpoint.get("processed_pks", []))
    offset = checkpoint.get("last_offset", 0)

    total_processed = 0
    total_updated = 0
    total_skipped = 0
    start_time = time.time()

    try:
        client.load_collection(collection)
    except Exception as e:
        print(f"[WARN] Could not load collection: {e}")

    while True:
        if limit and total_processed >= limit:
            print(f"\n[INFO] Reached limit of {limit} documents")
            break

        current_batch_size = min(
            batch_size, (limit - total_processed) if limit else batch_size
        )

        try:
            rows = client.query(
                collection,
                filter="",
                output_fields=[
                    "pk",
                    "vector",
                    "image_id",
                    "file_id",
                    "page_number",
                    "sparse_vector",
                ],
                limit=current_batch_size,
                offset=offset,
            )
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            break

        if not rows:
            print("\n[INFO] No more rows to process")
            break

        needs_update = []
        for row in rows:
            pk = row.get("pk")
            if pk in processed_set:
                total_skipped += 1
                continue

            sparse_vec = row.get("sparse_vector", {})
            if sparse_vec and isinstance(sparse_vec, dict) and len(sparse_vec) > 0:
                total_skipped += 1
                processed_set.add(pk)
                continue

            needs_update.append(row)

        if needs_update:
            texts = []
            for row in needs_update:
                text = f"{row.get('file_id', '')} {row.get('image_id', '')} page {row.get('page_number', 0)}"
                texts.append(text.strip())

            if dry_run:
                print(
                    f"  [DRY RUN] Would generate sparse vectors for {len(needs_update)} rows"
                )
                sparse_vecs = [{} for _ in needs_update]
            else:
                sparse_vecs = await fetch_sparse_embeddings(texts)
                if len(sparse_vecs) != len(needs_update):
                    print(
                        f"  [WARN] Sparse count mismatch: {len(sparse_vecs)} vs {len(needs_update)}"
                    )
                    sparse_vecs = [{} for _ in needs_update]

            for i, row in enumerate(needs_update):
                pk = row.get("pk")
                sparse_vec = sparse_vecs[i] if i < len(sparse_vecs) else {}

                if not dry_run and sparse_vec:
                    try:
                        row_data = {
                            "pk": row["pk"],
                            "vector": row["vector"],
                            "image_id": row.get("image_id", ""),
                            "file_id": row.get("file_id", ""),
                            "page_number": row.get("page_number", 0),
                            "sparse_vector": sparse_vec,
                        }
                        client.upsert(
                            collection,
                            [row_data],
                        )
                        total_updated += 1
                    except Exception as e:
                        print(f"  [WARN] Upsert failed for pk={pk}: {e}")

                processed_set.add(pk)
                total_processed += 1

        else:
            total_processed += len(rows)

        offset += len(rows)

        checkpoint["processed_pks"] = list(processed_set)[-10000:]
        checkpoint["last_offset"] = offset
        save_checkpoint(checkpoint)

        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        print(
            f"  Progress: {total_processed} processed, {total_updated} updated, "
            f"{total_skipped} skipped | Rate: {rate:.1f}/s"
        )

        if rate_limit_delay > 0:
            await asyncio.sleep(rate_limit_delay)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("BACKFILL COMPLETE")
    print(f"  Total processed: {total_processed}")
    print(f"  Total updated: {total_updated}")
    print(f"  Total skipped: {total_skipped}")
    print(f"  Elapsed time: {elapsed:.1f}s")
    print(f"{'=' * 60}\n")

    if not dry_run and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Backfill sparse vectors for existing Milvus documents"
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Milvus collection name to backfill",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of documents per batch (default: 100)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum documents to process (default: unlimited)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        help="Delay between batches in seconds (default: 0.5)",
    )

    args = parser.parse_args()

    print("\nSparse Vector Backfill Job")
    print(f"Model server: {MODEL_SERVER_URL}")
    print(f"Milvus URI: {MILVUS_URI}")

    asyncio.run(
        backfill_collection(
            collection=args.collection,
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run,
            rate_limit_delay=args.rate_limit,
        )
    )


if __name__ == "__main__":
    main()

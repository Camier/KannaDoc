#!/usr/bin/env python3
"""Ensure scalar (metadata) indexes exist on thesis Milvus collections.

This script is intentionally SAFE and idempotent:
- It never drops collections or indexes.
- It never re-ingests vectors.
- It only creates missing scalar indexes on existing fields.

Primary use-case (thesis RAG):
- Patch vectors collection (ColPali/ColQwen style) uses patch-level rows.
- Retrieval/rerank groups by (file_id, page_number) at page-level.
- Fast filters and page grouping benefit from scalar indexes on:
  - file_id (VARCHAR) -> INVERTED
  - image_id (VARCHAR) -> INVERTED (debug / patch id)
  - page_number (INT64) -> INVERTED
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

from pymilvus import MilvusClient


DEFAULT_FIELDS = ("file_id", "image_id", "page_number")


def _iter_target_collections(
    client: MilvusClient, explicit: list[str] | None, match_substrings: list[str]
) -> list[str]:
    if explicit:
        return list(dict.fromkeys([c for c in explicit if isinstance(c, str) and c.strip()]))

    all_collections = [str(c) for c in (client.list_collections() or [])]
    lowered = [(c, c.lower()) for c in all_collections]

    needles = [s.lower() for s in match_substrings if s and s.strip()]
    if not needles:
        return all_collections

    out: list[str] = []
    for c, cl in lowered:
        if any(n in cl for n in needles):
            out.append(c)
    return out


def _collection_fields(client: MilvusClient, collection_name: str) -> set[str]:
    desc = client.describe_collection(collection_name)
    fields = desc.get("fields") or []
    out: set[str] = set()
    for f in fields:
        if isinstance(f, dict) and isinstance(f.get("name"), str):
            out.add(f["name"])
    return out


def _has_any_index_on_field(client: MilvusClient, collection_name: str, field_name: str) -> bool:
    try:
        idxs = client.list_indexes(collection_name=collection_name, field_name=field_name)
    except Exception:
        return False

    # pymilvus returns a list; entries may be dicts or strings depending on version.
    if not idxs:
        return False
    return True


def _ensure_inverted_index(
    client: MilvusClient,
    collection_name: str,
    field_name: str,
    index_name: str,
    dry_run: bool,
) -> bool:
    """Return True if an index was created, False if skipped."""
    if _has_any_index_on_field(client, collection_name, field_name):
        return False

    if dry_run:
        print(f"[DRY] create INVERTED index on {collection_name}.{field_name} (name={index_name})")
        return True

    idx_params = client.prepare_index_params()
    idx_params.add_index(
        field_name=field_name,
        index_name=index_name,
        index_type="INVERTED",
    )
    client.create_index(collection_name=collection_name, index_params=idx_params, sync=True)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ensure scalar INVERTED indexes exist on thesis Milvus collections."
    )
    parser.add_argument(
        "--uri",
        default=os.environ.get("MILVUS_URI", "http://milvus-standalone:19530"),
        help="Milvus URI. Defaults to $MILVUS_URI or http://milvus-standalone:19530",
    )
    parser.add_argument(
        "--collections",
        nargs="*",
        default=None,
        help="Explicit collection names to inspect. If omitted, collections are auto-selected via --match.",
    )
    parser.add_argument(
        "--match",
        nargs="*",
        default=["colpali", "colqwen", "_pages_sparse", "thesis"],
        help="Substrings used to select collections when --collections is not provided.",
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        default=list(DEFAULT_FIELDS),
        help="Scalar fields to ensure indexes for (default: file_id image_id page_number).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without making changes.",
    )

    args = parser.parse_args(argv)

    try:
        client = MilvusClient(uri=str(args.uri))
    except Exception as exc:
        print(f"[ERROR] Failed to connect to Milvus at {args.uri}: {exc}")
        return 2

    targets = _iter_target_collections(
        client=client,
        explicit=list(args.collections) if args.collections else None,
        match_substrings=list(args.match or []),
    )

    if not targets:
        print("No collections matched selection. Nothing to do.")
        return 0

    created_total = 0
    skipped_total = 0

    for coll in targets:
        if not client.has_collection(coll):
            print(f"[SKIP] {coll}: not found")
            continue

        try:
            fields_present = _collection_fields(client, coll)
        except Exception as exc:
            print(f"[WARN] {coll}: describe_collection failed: {exc}")
            continue

        print(f"\n== {coll} ==")
        created_here = 0
        skipped_here = 0

        for field in list(args.fields or []):
            if field not in fields_present:
                print(f"[SKIP] field {field}: not in schema")
                skipped_here += 1
                continue

            index_name = f"{field}_index"
            try:
                created = _ensure_inverted_index(
                    client=client,
                    collection_name=coll,
                    field_name=field,
                    index_name=index_name,
                    dry_run=bool(args.dry_run),
                )
            except Exception as exc:
                print(f"[WARN] field {field}: create_index failed: {exc}")
                continue

            if created:
                print(f"[OK] ensured INVERTED index for field {field} (name={index_name})")
                created_here += 1
            else:
                print(f"[OK] index already exists for field {field}")
                skipped_here += 1

        created_total += created_here
        skipped_total += skipped_here

    print(f"\nDone. created={created_total} skipped={skipped_total} dry_run={bool(args.dry_run)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

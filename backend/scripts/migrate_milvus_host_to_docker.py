#!/usr/bin/env python3
"""Migrate Milvus collections from host Milvus -> docker-compose Milvus.

This script is designed for the thesis deployment where:
- Source Milvus runs on the host (systemd) on :19530
- Target Milvus runs in docker-compose and is published on 127.0.0.1:19531

Goals:
- Preserve collection names, schema, index types/params, and aliases.
- Keep the source intact for easy rollback.

Notes:
- Patch collection uses auto_id=True, so PK values are not preserved.
- Indexes are created AFTER data copy to avoid incremental indexing overhead.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Iterable, cast

from pymilvus import DataType, MilvusClient


PATCH_FIELDS = ["vector", "image_id", "page_number", "file_id", "filename"]
SPARSE_FIELDS = ["page_id", "sparse_vector", "file_id", "page_number", "text_preview"]


@dataclass
class IndexSpec:
    index_name: str
    field_name: str
    index_type: str
    metric_type: str | None
    params: dict[str, Any]


def _now_s() -> float:
    return time.time()


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", "_")


def _write_status(path: str, payload: dict[str, Any]) -> None:
    try:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        # Status file is best-effort; do not break migration.
        return


def _require_collection(client: MilvusClient, name: str, role: str) -> None:
    if not client.has_collection(name):
        raise RuntimeError(f"{role} Milvus missing expected collection: {name}")


def _drop_if_exists(client: MilvusClient, name: str) -> None:
    if client.has_collection(name):
        client.drop_collection(name)


def _drop_aliases_pointing_to(client: MilvusClient, collection_name: str) -> None:
    """Drop all aliases that resolve to the given collection.

    Milvus forbids dropping a collection while aliases exist.
    """
    try:
        aliases_resp = client.list_aliases()
        aliases = (
            aliases_resp.get("aliases") if isinstance(aliases_resp, dict) else None
        )
    except Exception:
        aliases = None

    if not aliases:
        return

    for a in list(aliases):
        try:
            desc = client.describe_alias(alias=str(a))
            if desc.get("collection_name") == collection_name:
                client.drop_alias(alias=str(a))
        except Exception:
            continue


def _collection_stats_rows(client: MilvusClient, name: str) -> int:
    stats = client.get_collection_stats(name)
    try:
        return int(stats.get("row_count", 0))
    except Exception:
        return 0


def _describe_schema(client: MilvusClient, name: str) -> dict[str, Any]:
    d = cast(dict[str, Any], client.describe_collection(name))
    # Keep only what we need for schema comparisons.
    out: dict[str, Any] = {
        "collection_name": d.get("collection_name"),
        "auto_id": d.get("auto_id"),
        "enable_dynamic_field": d.get("enable_dynamic_field"),
        "num_shards": d.get("num_shards"),
        "consistency_level": d.get("consistency_level"),
        "fields": [],
    }

    fields = d.get("fields") or []
    for f in fields:
        if not isinstance(f, dict):
            continue
        t = f.get("type")
        type_id = None
        if t is not None:
            try:
                type_id = int(t)
            except Exception:
                type_id = None
        out["fields"].append(
            {
                "name": f.get("name"),
                "type": type_id,
                "is_primary": bool(f.get("is_primary"))
                if f.get("is_primary") is not None
                else False,
                "params": f.get("params") or {},
            }
        )
    out["fields"].sort(key=lambda x: str(x.get("name")))
    return out


def _get_index_specs(client: MilvusClient, collection_name: str) -> list[IndexSpec]:
    specs: list[IndexSpec] = []
    for idx_name in client.list_indexes(collection_name=collection_name) or []:
        desc = cast(
            dict[str, Any],
            client.describe_index(collection_name=collection_name, index_name=idx_name),
        )
        params = dict(desc or {})
        index_type = str(params.pop("index_type", ""))
        field_name = str(params.pop("field_name", ""))
        metric_type = params.pop("metric_type", None)
        index_name = str(params.pop("index_name", idx_name))
        # Remaining keys are implementation details; keep only explicit params we can recreate.
        explicit_params: dict[str, Any] = {}
        for k, v in params.items():
            if k in {"M", "efConstruction", "drop_ratio_build"}:
                explicit_params[k] = v

        specs.append(
            IndexSpec(
                index_name=index_name,
                field_name=field_name,
                index_type=index_type,
                metric_type=str(metric_type) if metric_type is not None else None,
                params=explicit_params,
            )
        )

    # Stable ordering for logs.
    specs.sort(key=lambda s: (s.field_name, s.index_name))
    return specs


def _create_patch_collection(dst: MilvusClient, name: str) -> None:
    # pymilvus uses kwargs for schema flags; across versions the kwarg name
    # has been "enable_dynamic_field" (singular) rather than "...fields".
    schema = dst.create_schema(auto_id=True, enable_dynamic_field=True)
    schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=128)
    schema.add_field(field_name="image_id", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(field_name="file_id", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="filename", datatype=DataType.VARCHAR, max_length=65535)
    dst.create_collection(collection_name=name, schema=schema, shards_num=1)


def _create_sparse_collection(dst: MilvusClient, name: str) -> None:
    schema = dst.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(
        field_name="page_id",
        datatype=DataType.VARCHAR,
        max_length=1024,
        is_primary=True,
    )
    schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)
    schema.add_field(field_name="file_id", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="page_number", datatype=DataType.INT64)
    schema.add_field(
        field_name="text_preview", datatype=DataType.VARCHAR, max_length=65535
    )
    dst.create_collection(collection_name=name, schema=schema, shards_num=1)


def _iter_rows(
    client: MilvusClient,
    collection_name: str,
    output_fields: list[str],
    batch_size: int,
    limit: int,
) -> Iterable[list[dict[str, Any]]]:
    it = client.query_iterator(
        collection_name=collection_name,
        filter="",
        output_fields=list(output_fields),
        batch_size=int(batch_size),
        limit=int(limit),
    )
    try:
        while True:
            batch = it.next()
            if not batch:
                break
            yield batch
    finally:
        try:
            it.close()
        except Exception:
            pass


def _insert_batch(
    dst: MilvusClient, collection_name: str, rows: list[dict[str, Any]]
) -> int:
    if not rows:
        return 0
    dst.insert(collection_name=collection_name, data=rows)
    return len(rows)


def _copy_collection(
    *,
    src: MilvusClient,
    dst: MilvusClient,
    name: str,
    output_fields: list[str],
    batch_size: int,
    limit: int,
    flush_every: int,
    status_path: str,
    status_key: str,
) -> None:
    total = _collection_stats_rows(src, name)
    start = _now_s()
    inserted = 0
    batches = 0

    for batch in _iter_rows(
        client=src,
        collection_name=name,
        output_fields=output_fields,
        batch_size=batch_size,
        limit=limit,
    ):
        # Milvus query_iterator may include primary key fields even if not requested.
        # To keep inserts compatible with the target schema, project strictly to the
        # expected output_fields.
        projected: list[dict[str, Any]] = []
        for row in batch:
            if not isinstance(row, dict):
                continue
            projected.append({k: row.get(k) for k in output_fields})
        batches += 1
        inserted += _insert_batch(dst, name, projected)

        if flush_every > 0 and (batches % int(flush_every) == 0):
            dst.flush(collection_name=name)

        if batches == 1 or (batches % 25 == 0):
            elapsed = max(_now_s() - start, 1e-6)
            rate = inserted / elapsed
            pct = (inserted / total * 100.0) if total else 0.0
            eta_s = int((total - inserted) / rate) if (total and rate > 0) else -1
            status = {
                "stage": status_key,
                "collection": name,
                "inserted": inserted,
                "total": total,
                "percent": round(pct, 4),
                "rate_rows_per_s": round(rate, 2),
                "eta_s": eta_s,
                "batches": batches,
                "ts": int(_now_s()),
            }
            _write_status(status_path, status)
            print(
                f"[{status_key}] {name}: inserted={_fmt_int(inserted)}/{_fmt_int(total)} "
                f"({pct:.2f}%) rate={rate:.1f}/s eta_s={eta_s}",
                flush=True,
            )

    dst.flush(collection_name=name)
    final = _collection_stats_rows(dst, name)
    print(
        f"[{status_key}] {name}: flush complete, dst_row_count={_fmt_int(final)}",
        flush=True,
    )


def _create_indexes_from_specs(
    dst: MilvusClient, collection_name: str, specs: list[IndexSpec]
) -> None:
    if not specs:
        return

    # Build in a deterministic order.
    for spec in specs:
        idx_params = dst.prepare_index_params()
        kwargs: dict[str, Any] = {
            "field_name": spec.field_name,
            "index_name": spec.index_name,
            "index_type": spec.index_type,
        }
        if spec.metric_type:
            kwargs["metric_type"] = spec.metric_type
        if spec.params:
            # Normalize common numeric params.
            norm: dict[str, Any] = {}
            for k, v in spec.params.items():
                if k in {"M", "efConstruction"}:
                    try:
                        norm[k] = int(v)
                    except Exception:
                        norm[k] = v
                elif k in {"drop_ratio_build"}:
                    try:
                        norm[k] = float(v)
                    except Exception:
                        norm[k] = v
                else:
                    norm[k] = v
            kwargs["params"] = norm

        idx_params.add_index(**kwargs)
        dst.create_index(
            collection_name=collection_name, index_params=idx_params, sync=True
        )


def _verify_schema_equal(src: MilvusClient, dst: MilvusClient, name: str) -> None:
    s = _describe_schema(src, name)
    d = _describe_schema(dst, name)

    # Ignore collection_id / timestamps, but require core schema flags.
    for k in ["auto_id", "enable_dynamic_field", "num_shards"]:
        if s.get(k) != d.get(k):
            raise RuntimeError(
                f"Schema mismatch for {name}: {k} src={s.get(k)} dst={d.get(k)}"
            )

    if s.get("fields") != d.get("fields"):
        raise RuntimeError(
            f"Schema fields mismatch for {name}: src_fields != dst_fields"
        )


def _verify_indexes_equal(src: MilvusClient, dst: MilvusClient, name: str) -> None:
    src_specs = _get_index_specs(src, name)
    dst_specs = _get_index_specs(dst, name)

    def key(s: IndexSpec) -> tuple:
        return (
            s.index_name,
            s.field_name,
            s.index_type,
            s.metric_type,
            tuple(sorted((s.params or {}).items())),
        )

    sset = {key(s) for s in src_specs}
    dset = {key(s) for s in dst_specs}
    if sset != dset:
        missing = sset - dset
        extra = dset - sset
        raise RuntimeError(
            f"Index mismatch for {name}: missing={len(missing)} extra={len(extra)}"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Migrate Milvus collections host->docker.")
    p.add_argument("--src-uri", default="http://127.0.0.1:19530")
    p.add_argument("--dst-uri", default="http://127.0.0.1:19531")
    p.add_argument("--patch-collection", default="colpali_kanna_128")
    p.add_argument("--sparse-collection", default="colpali_kanna_128_pages_sparse")
    p.add_argument(
        "--alias",
        default="colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1",
        help="Alias to recreate on target (points to patch collection)",
    )
    p.add_argument("--batch-size", type=int, default=2048)
    p.add_argument("--limit", type=int, default=-1)
    p.add_argument("--flush-every", type=int, default=50)
    p.add_argument("--drop-dst", action="store_true")
    p.add_argument("--skip-data", action="store_true")
    p.add_argument("--verify-only", action="store_true")
    p.add_argument(
        "--status-file",
        default="/tmp/layra_milvus_migration_status.json",
        help="Writes JSON status periodically for monitoring",
    )

    args = p.parse_args(argv)

    src = MilvusClient(uri=str(args.src_uri))
    dst = MilvusClient(uri=str(args.dst_uri))

    patch = str(args.patch_collection)
    sparse = str(args.sparse_collection)
    alias = str(args.alias).strip()

    _require_collection(src, patch, role="source")
    _require_collection(src, sparse, role="source")

    if args.verify_only:
        _require_collection(dst, patch, role="target")
        _require_collection(dst, sparse, role="target")
        _verify_schema_equal(src, dst, patch)
        _verify_schema_equal(src, dst, sparse)
        _verify_indexes_equal(src, dst, patch)
        _verify_indexes_equal(src, dst, sparse)
        if alias:
            da = dst.describe_alias(alias=alias)
            if da.get("collection_name") != patch:
                raise RuntimeError(f"Alias mismatch: {alias} -> {da}")
        print("OK: verification passed", flush=True)
        return 0

    if args.drop_dst:
        # Drop aliases before dropping collections.
        if alias:
            try:
                dst.drop_alias(alias=alias)
            except Exception:
                pass
        _drop_aliases_pointing_to(dst, patch)
        _drop_aliases_pointing_to(dst, sparse)
        _drop_if_exists(dst, sparse)
        _drop_if_exists(dst, patch)

    if dst.has_collection(patch) or dst.has_collection(sparse):
        raise RuntimeError(
            "Target already has collections. Use --drop-dst to replace, or --verify-only."
        )

    # Create target collections with exact schema.
    _create_patch_collection(dst, patch)
    _create_sparse_collection(dst, sparse)

    # Copy data.
    if not args.skip_data:
        _copy_collection(
            src=src,
            dst=dst,
            name=sparse,
            output_fields=SPARSE_FIELDS,
            batch_size=max(256, int(args.batch_size)),
            limit=int(args.limit),
            flush_every=max(1, int(args.flush_every)),
            status_path=str(args.status_file),
            status_key="copy_sparse",
        )

        _copy_collection(
            src=src,
            dst=dst,
            name=patch,
            output_fields=PATCH_FIELDS,
            batch_size=max(256, int(args.batch_size)),
            limit=int(args.limit),
            flush_every=max(1, int(args.flush_every)),
            status_path=str(args.status_file),
            status_key="copy_patch",
        )

    # Create indexes based on source descriptions.
    print("[index] describing source indexes...", flush=True)
    src_patch_specs = _get_index_specs(src, patch)
    src_sparse_specs = _get_index_specs(src, sparse)
    print(
        f"[index] source patch indexes: {[s.index_name for s in src_patch_specs]}",
        flush=True,
    )
    print(
        f"[index] source sparse indexes: {[s.index_name for s in src_sparse_specs]}",
        flush=True,
    )

    print("[index] creating indexes on target...", flush=True)
    _create_indexes_from_specs(dst, sparse, src_sparse_specs)
    _create_indexes_from_specs(dst, patch, src_patch_specs)

    # Recreate alias.
    if alias:
        print(f"[alias] creating alias {alias} -> {patch}", flush=True)
        dst.create_alias(collection_name=patch, alias=alias)

    # Final verification.
    print("[verify] verifying schema/index/counts...", flush=True)
    _verify_schema_equal(src, dst, patch)
    _verify_schema_equal(src, dst, sparse)
    _verify_indexes_equal(src, dst, patch)
    _verify_indexes_equal(src, dst, sparse)

    src_patch_rows = _collection_stats_rows(src, patch)
    dst_patch_rows = _collection_stats_rows(dst, patch)
    src_sparse_rows = _collection_stats_rows(src, sparse)
    dst_sparse_rows = _collection_stats_rows(dst, sparse)
    if src_patch_rows != dst_patch_rows:
        raise RuntimeError(
            f"Row count mismatch patch: src={src_patch_rows} dst={dst_patch_rows}"
        )
    if src_sparse_rows != dst_sparse_rows:
        raise RuntimeError(
            f"Row count mismatch sparse: src={src_sparse_rows} dst={dst_sparse_rows}"
        )

    if alias:
        da = dst.describe_alias(alias=alias)
        if da.get("collection_name") != patch:
            raise RuntimeError(f"Alias mismatch: {alias} -> {da}")

    _write_status(
        str(args.status_file),
        {
            "stage": "done",
            "ts": int(_now_s()),
            "patch": patch,
            "sparse": sparse,
            "alias": alias,
            "dst_uri": str(args.dst_uri),
        },
    )
    print("DONE: migration complete and verified", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

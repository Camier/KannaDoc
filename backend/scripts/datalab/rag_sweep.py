#!/usr/bin/env python3
"""Sweep RAG retrieval parameters and emit JSONL results.

This script runs the backend eval runner directly (no HTTP) across a small
parameter grid and writes one JSON object per line (append-safe).

Usage:
  cd backend && PYTHONPATH=. python3 scripts/datalab/rag_sweep.py \
    --dataset-id <id> \
    --output data/sweep_results.jsonl \
    --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class SweepParams:
    retrieval_mode: str
    rag_max_query_vecs: int
    ef: int
    top_k: int


def _csv_list(raw: str) -> List[str]:
    return [x.strip() for x in (raw or "").split(",") if x.strip()]


def _csv_ints(raw: str) -> List[int]:
    out: List[int] = []
    for part in _csv_list(raw):
        out.append(int(part))
    return out


def _git_commit_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _pymilvus_version() -> str:
    try:
        return metadata.version("pymilvus")
    except Exception:
        return "unknown"


def _build_grid(
    retrieval_modes: Iterable[str],
    max_query_vecs: Iterable[int],
    ef_values: Iterable[int],
    top_k: int,
) -> List[SweepParams]:
    out: List[SweepParams] = []
    for mode in retrieval_modes:
        for vecs in max_query_vecs:
            for ef in ef_values:
                out.append(
                    SweepParams(
                        retrieval_mode=str(mode),
                        rag_max_query_vecs=int(vecs),
                        ef=int(ef),
                        top_k=int(top_k),
                    )
                )
    return out


async def _validate_dataset_exists(dataset_id: str) -> None:
    from app.db.mongo import get_mongo
    from app.eval.dataset import get_dataset

    mongo = await get_mongo()
    db = mongo.db
    assert db is not None, "MongoDB not connected"

    ds = await get_dataset(dataset_id, db=db)
    if ds is None:
        raise ValueError(f"Dataset '{dataset_id}' not found")


async def run_sweep(
    dataset_id: str,
    output_path: Path,
    grid: List[SweepParams],
) -> None:
    from app.eval.runner import run_evaluation

    git_commit = _git_commit_short()
    pymilvus_version = _pymilvus_version()
    ts = datetime.now(timezone.utc).isoformat()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as f:
        for idx, params in enumerate(grid, start=1):
            cfg = {
                "top_k": params.top_k,
                "retrieval_mode": params.retrieval_mode,
                "rag_max_query_vecs": params.rag_max_query_vecs,
                "ef": params.ef,
            }

            try:
                eval_run = await run_evaluation(dataset_id=dataset_id, config=cfg)
                metrics: Dict[str, Any] = dict(eval_run.metrics or {})

                row = {
                    "params": {
                        "retrieval_mode": params.retrieval_mode,
                        "rag_max_query_vecs": params.rag_max_query_vecs,
                        "ef": params.ef,
                        "top_k": params.top_k,
                    },
                    "metrics": {
                        "mrr": metrics.get("mrr", 0.0),
                        "ndcg": metrics.get("ndcg", 0.0),
                        "precision": metrics.get("precision", 0.0),
                        "recall": metrics.get("recall", 0.0),
                    },
                    "timing": metrics.get("timing_ms", {}),
                    "meta": {
                        "timestamp": ts,
                        "git_commit": git_commit,
                        "pymilvus_version": pymilvus_version,
                        "dataset_id": dataset_id,
                        "queries_total": metrics.get("queries_total", None),
                    },
                }

                f.write(json.dumps(row, ensure_ascii=True) + "\n")
                f.flush()

                p95 = metrics.get("p95_latency_ms", 0.0)
                print(
                    f"[{idx}/{len(grid)}] mode={params.retrieval_mode} vecs={params.rag_max_query_vecs} ef={params.ef} "
                    f"-> MRR={row['metrics']['mrr']:.4f} p95={float(p95):.1f}ms"
                )
            except Exception as exc:
                print(
                    f"[{idx}/{len(grid)}] mode={params.retrieval_mode} vecs={params.rag_max_query_vecs} ef={params.ef} "
                    f"-> ERROR: {exc}"
                )
                continue


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sweep retrieval params and emit JSONL")
    p.add_argument("--dataset-id", required=True, help="Evaluation dataset id")
    p.add_argument(
        "--output",
        required=False,
        default="data/sweep_results.jsonl",
        help="Output JSONL path (append-safe)",
    )
    p.add_argument(
        "--retrieval-modes",
        default="dense,dual_then_rerank",
        help="Comma-separated modes (default: dense,dual_then_rerank)",
    )
    p.add_argument(
        "--max-query-vecs",
        default="48,32,24,16",
        help="Comma-separated rag_max_query_vecs values",
    )
    p.add_argument(
        "--ef-values",
        default="100,200,400",
        help="Comma-separated ef values (search-time)",
    )
    p.add_argument("--top-k", type=int, default=10, help="top_k for evaluation")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print grid size and exit without running",
    )
    return p


async def main() -> None:
    args = build_parser().parse_args()

    retrieval_modes = _csv_list(args.retrieval_modes)
    max_query_vecs = _csv_ints(args.max_query_vecs)
    ef_values = _csv_ints(args.ef_values)
    grid = _build_grid(
        retrieval_modes, max_query_vecs, ef_values, top_k=int(args.top_k)
    )

    if args.dry_run:
        print(f"Dry run: {len(grid)} combinations")
        for i, params in enumerate(grid[: min(10, len(grid))], start=1):
            print(
                f"  {i}. mode={params.retrieval_mode} vecs={params.rag_max_query_vecs} ef={params.ef} top_k={params.top_k}"
            )
        if len(grid) > 10:
            print("  ...")
        return

    await _validate_dataset_exists(str(args.dataset_id))
    await run_sweep(
        dataset_id=str(args.dataset_id),
        output_path=Path(str(args.output)),
        grid=grid,
    )


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Summarize capability probe failures and record a snapshot for change detection.

By default, exits non-zero only when new failures appear.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing capabilities file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_failures(models: Dict[str, Any]) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []
    keys = ("chat", "embeddings", "rerank", "stream", "tools_auto", "tools_required")
    for model_name, info in models.items():
        if not isinstance(info, dict):
            continue
        if info.get("skipped") is True:
            continue
        for key in keys:
            payload = info.get(key)
            if not isinstance(payload, dict):
                continue
            status = payload.get("status")
            if isinstance(status, int) and status not in (200, 204):
                failures.append(
                    {
                        "model": model_name,
                        "probe": key,
                        "status": status,
                        "error": str(payload.get("error") or "")[:200],
                    }
                )
    return failures


def _failure_keys(failures: List[Dict[str, Any]]) -> List[str]:
    return [f"{f['model']}::{f['probe']}::{f['status']}" for f in failures]


def _write_snapshot(path: Path, failures: List[Dict[str, Any]]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "failures": failures,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Report LiteLLM probe failures")
    parser.add_argument(
        "--input",
        default="state/model_capabilities.json",
        help="Path to model_capabilities.json",
    )
    parser.add_argument(
        "--snapshot",
        default="state/model_capabilities.failures.json",
        help="Path to failure snapshot JSON",
    )
    parser.add_argument(
        "--fail-on-any",
        action="store_true",
        help="Exit non-zero if any failures are present (not just new ones).",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    snapshot_path = Path(args.snapshot)

    try:
        payload = _load_json(input_path)
    except Exception as exc:
        print(f"[error] {exc}")
        return 2

    models = payload.get("models", {})
    if not isinstance(models, dict):
        print("[error] invalid model_capabilities.json format (missing models dict)")
        return 2

    failures = _collect_failures(models)
    current_keys = set(_failure_keys(failures))

    previous_keys: set[str] = set()
    if snapshot_path.exists():
        try:
            previous = json.loads(snapshot_path.read_text(encoding="utf-8"))
            prev_failures = previous.get("failures") or []
            if isinstance(prev_failures, list):
                previous_keys = set(_failure_keys(prev_failures))
        except Exception:
            previous_keys = set()

    new_failures = sorted(current_keys - previous_keys)

    _write_snapshot(snapshot_path, failures)

    if failures:
        if new_failures:
            print("[alert] new failures detected:")
            for item in new_failures:
                print(f"  - {item}")
        else:
            print(f"[ok] {len(failures)} existing failure(s), no new failures")
    else:
        print("[ok] no failures detected")

    if args.fail_on_any and failures:
        return 1
    if new_failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

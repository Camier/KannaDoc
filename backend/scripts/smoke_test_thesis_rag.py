"""Non-destructive smoke test for the thesis RAG pipeline.

Run inside the backend container:
  docker compose exec -T backend python scripts/smoke_test_thesis_rag.py

It validates:
1) Thesis KB present (base endpoints)
2) Retrieval mode effectively behaves as thesis dual/sparse (top_k minimum normalization)
3) Search preview diversity (distinct file_id >= threshold)
4) Thesis preview rendering endpoints (page-image returns image/png)
5) Milvus scalar indexes script succeeds (dry-run; no drops, no re-ingestion)
6) SSE chat emits file_used (even if LLM call fails)

This script prints only counts and HTTP statuses; it does not print env vars or secrets.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urljoin

import httpx


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    api_prefix: str = "/api/v1"
    min_preview_results: int = 50
    min_distinct_files_preview: int = 10
    min_distinct_files_sse: int = 10
    sse_timeout_s: float = 60.0


def _fail(msg: str) -> None:
    raise RuntimeError(msg)


def _get_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        _fail(f"Non-JSON response from {resp.request.method} {resp.request.url} status={resp.status_code}")


def _distinct_files(items: Iterable[dict]) -> int:
    return len({str(x.get("file_id")) for x in items if isinstance(x, dict) and x.get("file_id")})


def _pick_thesis_kb_id(knowledge_bases: list[dict]) -> str:
    for kb in knowledge_bases:
        kid = kb.get("knowledge_base_id")
        if isinstance(kid, str) and kid.startswith("thesis_"):
            return kid
    _fail("No thesis_ knowledge base found in /base/knowledge_bases")
    return ""  # unreachable


def _run_scalar_index_dry_run() -> None:
    # Run locally (inside container) against the configured MILVUS_URI.
    cmd = [sys.executable, "scripts/milvus_ensure_scalar_indexes.py", "--dry-run"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        _fail(f"milvus_ensure_scalar_indexes dry-run failed rc={proc.returncode}")
    # Print one short line (no secrets).
    tail = (proc.stdout or "").strip().splitlines()[-1:] or []
    if tail:
        print(f"[OK] scalar-index dry-run: {tail[0]}")
    else:
        print("[OK] scalar-index dry-run: ok")


def _sse_read_first_file_used(
    client: httpx.Client,
    url: str,
    json_body: dict[str, Any],
    timeout_s: float,
) -> list[dict]:
    file_used: list[dict] | None = None
    t0 = time.time()

    with client.stream("POST", url, json=json_body, timeout=timeout_s) as resp:
        if resp.status_code != 200:
            _fail(f"SSE chat status={resp.status_code}")

        # Server yields lines like: "data: {...}\n\n"
        for raw in resp.iter_lines():
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                continue
            if not line.startswith("data: "):
                if time.time() - t0 > timeout_s:
                    break
                continue

            payload = line[len("data: ") :]
            try:
                msg = json.loads(payload)
            except Exception:
                continue

            if msg.get("type") == "file_used":
                data = msg.get("data")
                if isinstance(data, list):
                    file_used = [x for x in data if isinstance(x, dict)]
                    break

            if time.time() - t0 > timeout_s:
                break

    if file_used is None:
        _fail("SSE did not emit file_used within timeout")
    return file_used


def main() -> int:
    cfg = SmokeConfig(
        base_url=os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/"),
        min_preview_results=int(os.getenv("SMOKE_MIN_PREVIEW_RESULTS", "50")),
        min_distinct_files_preview=int(os.getenv("SMOKE_MIN_DISTINCT_FILES_PREVIEW", "10")),
        min_distinct_files_sse=int(os.getenv("SMOKE_MIN_DISTINCT_FILES_SSE", "10")),
    )

    api_base = cfg.base_url + cfg.api_prefix
    print(f"[INFO] base_url={cfg.base_url} api_prefix={cfg.api_prefix}")

    with httpx.Client() as client:
        # 1) Enumerate KBs and pick the thesis KB.
        r = client.get(api_base + "/base/knowledge_bases", timeout=10.0)
        if r.status_code != 200:
            _fail(f"GET /base/knowledge_bases status={r.status_code}")
        kbs = _get_json(r)
        if not isinstance(kbs, list):
            _fail("Expected list response from /base/knowledge_bases")
        kb_id = _pick_thesis_kb_id(kbs)
        print(f"[OK] thesis_kb_id={kb_id}")

        # 2) search-preview: ensure thesis mode prevents tiny recall (top_k minimum normalization).
        preview_url = api_base + f"/kb/knowledge-base/{kb_id}/search-preview"
        preview_req = {"query": "introduction", "top_k": 2}
        r = client.post(preview_url, json=preview_req, timeout=60.0)
        if r.status_code != 200:
            _fail(f"POST /search-preview status={r.status_code}")
        payload = _get_json(r)
        results = payload.get("results", [])
        if not isinstance(results, list):
            _fail("search-preview results must be a list")

        total_results = int(payload.get("total_results") or len(results))
        distinct_files = _distinct_files(results)
        print(f"[OK] search-preview total_results={total_results} distinct_files={distinct_files}")

        if total_results < cfg.min_preview_results:
            _fail(
                f"search-preview returned too few results: {total_results} < {cfg.min_preview_results} "
                "(retrieval_mode might be mis-set or top_k normalization regressed)"
            )
        if distinct_files < cfg.min_distinct_files_preview:
            _fail(
                f"search-preview returned too few distinct files: {distinct_files} < {cfg.min_distinct_files_preview}"
            )

        # 3) Thesis preview URL should work (image/png).
        if results:
            minio_url = str(results[0].get("minio_url") or "")
            if not minio_url:
                _fail("search-preview first result missing minio_url")

            # minio_url is a relative API path in thesis fallback; resolve against base_url.
            image_url = urljoin(cfg.base_url + "/", minio_url.lstrip("/"))
            img = client.get(image_url, timeout=60.0)
            ct = (img.headers.get("content-type") or "").lower()
            if img.status_code != 200 or "image/png" not in ct:
                _fail(f"thesis preview image fetch failed status={img.status_code} content-type={ct}")
            print("[OK] thesis page-image preview returns image/png")

        # 4) Milvus scalar indexes dry-run succeeds (idempotent; does not touch vectors).
        _run_scalar_index_dry_run()

        # 5) SSE chat emits file_used with adequate diversity.
        conv_id = str(uuid.uuid4())
        create_conv_url = api_base + "/chat/conversations"
        sse_url = api_base + "/sse/chat"

        # Use a system_* style config so runtime can pick env-backed providers.
        create_req = {
            "conversation_id": conv_id,
            "username": "miko",
            "conversation_name": f"thesis-smoke-{conv_id}",
            "chat_model_config": {
                "model_id": "system_deepseek-chat",
                "model_name": "deepseek-chat",
                "model_url": "",
                "api_key": None,
                "provider": "deepseek",
                "base_used": [],
                "system_prompt": "",
                "temperature": -1,
                "max_length": -1,
                "top_P": -1,
                "top_K": -1,
                "score_threshold": -1,
            },
        }
        r = client.post(create_conv_url, json=create_req, timeout=10.0)
        if r.status_code != 200:
            _fail(f"POST /chat/conversations status={r.status_code}")

        sse_req = {
            "conversation_id": conv_id,
            "parent_id": "",
            "user_message": "introduction",
            "temp_db_id": kb_id,
        }
        file_used = _sse_read_first_file_used(
            client=client,
            url=sse_url,
            json_body=sse_req,
            timeout_s=cfg.sse_timeout_s,
        )
        df = _distinct_files(file_used)
        print(f"[OK] sse file_used len={len(file_used)} distinct_files={df}")

        if df < cfg.min_distinct_files_sse:
            _fail(
                f"SSE file_used diversity too low: distinct_files={df} < {cfg.min_distinct_files_sse}"
            )

    print("[SUCCESS] thesis RAG smoke test passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"[FAIL] {e}")
        raise SystemExit(2)


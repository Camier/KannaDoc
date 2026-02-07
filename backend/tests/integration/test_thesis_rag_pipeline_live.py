"""Live integration smoke test for the thesis RAG pipeline.

This test is intentionally skipped by default because it requires:
- The backend server running (e.g. inside the backend container)
- Milvus accessible at runtime (host Milvus or compose milvus-standalone)
- Embedding/sparse services configured (MODEL_SERVER_URL, etc.)

Run explicitly:
  docker compose exec -T backend env LAYRA_LIVE_INTEGRATION=1 pytest -m integration -s

This is the pytest version of backend/scripts/smoke_test_thesis_rag.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Iterable
from urllib.parse import urljoin

import httpx
import pytest


pytestmark = pytest.mark.integration


def _distinct_files(items: Iterable[dict]) -> int:
    return len({str(x.get("file_id")) for x in items if isinstance(x, dict) and x.get("file_id")})


def _get_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception as exc:
        raise AssertionError(
            f"Non-JSON response: {resp.request.method} {resp.request.url} status={resp.status_code}"
        ) from exc


def _pick_thesis_kb_id(knowledge_bases: list[dict]) -> str:
    for kb in knowledge_bases:
        kid = kb.get("knowledge_base_id")
        if isinstance(kid, str) and kid.startswith("thesis_"):
            return kid
    raise AssertionError("No thesis_ knowledge base found in /base/knowledge_bases")


def _run_scalar_index_dry_run() -> None:
    cmd = [sys.executable, "scripts/milvus_ensure_scalar_indexes.py", "--dry-run"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"milvus_ensure_scalar_indexes dry-run failed rc={proc.returncode}"


def _sse_read_first_file_used(
    client: httpx.Client,
    url: str,
    json_body: dict[str, Any],
    timeout_s: float,
) -> list[dict]:
    file_used: list[dict] | None = None
    t0 = time.time()

    with client.stream("POST", url, json=json_body, timeout=timeout_s) as resp:
        assert resp.status_code == 200, f"SSE chat status={resp.status_code}"

        for raw in resp.iter_lines():
            if raw is None:
                continue
            line = raw.strip()
            if not line or not line.startswith("data: "):
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

    assert file_used is not None, "SSE did not emit file_used within timeout"
    return file_used


@pytest.mark.skipif(
    os.getenv("LAYRA_LIVE_INTEGRATION") != "1",
    reason="Set LAYRA_LIVE_INTEGRATION=1 to run live integration tests",
)
def test_thesis_rag_pipeline_live() -> None:
    base_url = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    api_base = base_url + "/api/v1"

    min_preview_results = int(os.getenv("SMOKE_MIN_PREVIEW_RESULTS", "50"))
    min_distinct_files_preview = int(os.getenv("SMOKE_MIN_DISTINCT_FILES_PREVIEW", "10"))
    min_distinct_files_sse = int(os.getenv("SMOKE_MIN_DISTINCT_FILES_SSE", "10"))
    sse_timeout_s = float(os.getenv("SMOKE_SSE_TIMEOUT_S", "60"))

    with httpx.Client() as client:
        r = client.get(api_base + "/base/knowledge_bases", timeout=10.0)
        assert r.status_code == 200
        kbs = _get_json(r)
        assert isinstance(kbs, list)
        kb_id = _pick_thesis_kb_id(kbs)

        # search-preview should normalize top_k up (avoid accidental tiny recall).
        preview_url = api_base + f"/kb/knowledge-base/{kb_id}/search-preview"
        preview_req = {"query": "introduction", "top_k": 2}
        r = client.post(preview_url, json=preview_req, timeout=60.0)
        assert r.status_code == 200
        payload = _get_json(r)
        results = payload.get("results", [])
        assert isinstance(results, list)

        total_results = int(payload.get("total_results") or len(results))
        distinct_files = _distinct_files(results)
        assert total_results >= min_preview_results
        assert distinct_files >= min_distinct_files_preview

        # Thesis preview fallback should return image/png.
        assert results, "Expected at least one search-preview result"
        minio_url = str(results[0].get("minio_url") or "")
        assert minio_url, "Expected minio_url for preview rendering"
        image_url = urljoin(base_url + "/", minio_url.lstrip("/"))
        img = client.get(image_url, timeout=60.0)
        ct = (img.headers.get("content-type") or "").lower()
        assert img.status_code == 200
        assert "image/png" in ct

        # Scalar index script must succeed in dry-run (no drops, no vector touches).
        _run_scalar_index_dry_run()

        # SSE chat must emit file_used early and with decent diversity.
        conv_id = str(uuid.uuid4())
        create_conv_url = api_base + "/chat/conversations"
        sse_url = api_base + "/sse/chat"

        create_req = {
            "conversation_id": conv_id,
            "username": "miko",
            "conversation_name": f"thesis-live-integration-{conv_id}",
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
        assert r.status_code == 200

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
            timeout_s=sse_timeout_s,
        )
        assert _distinct_files(file_used) >= min_distinct_files_sse


"""Unit tests for eval timing + retrieval overrides.

These tests avoid live infra by monkeypatching embedding/search/database calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest

pytestmark = pytest.mark.unit


@dataclass
class _Query:
    query_text: str
    relevant_docs: List[Dict[str, Any]]


@dataclass
class _Dataset:
    name: str
    kb_id: str
    queries: List[_Query]


def _fake_hits(file_id: str = "f1", page_number: int = 1, score: float = 0.5):
    return [
        [
            {
                "entity": {"file_id": file_id, "page_number": page_number},
                "distance": float(score),
            }
        ]
    ]


def test_timing_backward_compat_returns_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """MilvusManager.search() should return a plain list by default."""
    from app.db.milvus import MilvusManager

    m = MilvusManager.__new__(MilvusManager)
    monkeypatch.setattr(m, "load_collection", lambda _name: None)
    monkeypatch.setattr(m, "_search_with_retry", lambda *_a, **_k: _fake_hits())
    monkeypatch.setattr(
        m,
        "_exact_rerank_pages",
        lambda *_a, **_k: (
            [{"score": 1.0, "file_id": "f1", "page_number": 1}],
            {"vector_fetch_ms": 1.0, "maxsim_rerank_ms": 2.0},
        ),
    )

    out = m.search("c", data=[[0.0] * 128], topk=5)
    assert isinstance(out, list)


def test_timing_dict_keys_and_total(monkeypatch: pytest.MonkeyPatch) -> None:
    """MilvusManager.search(return_timing=True) returns (results, timing) with stable keys."""
    from app.db.milvus import MilvusManager

    m = MilvusManager.__new__(MilvusManager)
    monkeypatch.setattr(m, "load_collection", lambda _name: None)
    monkeypatch.setattr(m, "_search_with_retry", lambda *_a, **_k: _fake_hits())
    monkeypatch.setattr(
        m,
        "_exact_rerank_pages",
        lambda *_a, **_k: (
            [{"score": 1.0, "file_id": "f1", "page_number": 1}],
            {"vector_fetch_ms": 1.25, "maxsim_rerank_ms": 2.50},
        ),
    )

    results, timing = m.search("c", data=[[0.0] * 128], topk=5, return_timing=True)
    assert isinstance(results, list)
    assert isinstance(timing, dict)

    expected = {
        "candidate_gen_ms",
        "vector_fetch_ms",
        "maxsim_rerank_ms",
        "total_search_ms",
    }
    assert expected.issubset(set(timing.keys()))

    for k in expected:
        assert isinstance(timing[k], float)
        assert timing[k] >= 0.0

    assert timing["total_search_ms"] == pytest.approx(
        timing["candidate_gen_ms"]
        + timing["vector_fetch_ms"]
        + timing["maxsim_rerank_ms"],
        rel=1e-6,
    )


@pytest.mark.asyncio
async def test_eval_runner_override_dual_then_rerank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Eval runner should honor retrieval_mode + ef + rag_max_query_vecs overrides."""
    from app.eval import runner

    ds = _Dataset(
        name="t",
        kb_id="kb",
        queries=[
            _Query(
                query_text="hello",
                relevant_docs=[{"doc_id": "f1", "relevance_score": 1}],
            )
        ],
    )

    async def _fake_get_dataset(*_a, **_k):
        return ds

    monkeypatch.setattr(runner, "get_dataset", _fake_get_dataset)
    monkeypatch.setattr(
        runner.vector_db_client, "check_collection", lambda *_a, **_k: True
    )

    async def _fake_embed(*_a, **_k):
        return [[0.0] * 128]

    async def _fake_sparse(*_a, **_k):
        return [{1: 0.25}]

    monkeypatch.setattr(runner, "get_embeddings_from_httpx", _fake_embed)
    monkeypatch.setattr(runner, "get_sparse_embeddings", _fake_sparse)
    monkeypatch.setattr(runner, "normalize_multivector", lambda x: x)
    monkeypatch.setattr(runner, "downsample_multivector", lambda x, _k: x)

    called: Dict[str, Any] = {}

    def _fake_search(
        collection_name: str, data: Any, topk: int = 10, return_timing: bool = False
    ):
        called["collection_name"] = collection_name
        called["data"] = data
        called["topk"] = topk
        assert return_timing is True
        return (
            [{"file_id": "f1", "page_number": 1, "image_id": "p1", "score": 1.0}],
            {
                "candidate_gen_ms": 1.0,
                "vector_fetch_ms": 2.0,
                "maxsim_rerank_ms": 3.0,
                "total_search_ms": 6.0,
            },
        )

    monkeypatch.setattr(runner.vector_db_client, "search", _fake_search)

    class _FakeRepo:
        def __init__(self, _db):
            pass

        async def create_run(self, _run_dict):
            return None

    monkeypatch.setattr(runner, "EvalRepository", _FakeRepo)

    eval_run = await runner.run_evaluation(
        dataset_id="ds",
        config={
            "top_k": 5,
            "retrieval_mode": "dual_then_rerank",
            "rag_max_query_vecs": 16,
            "ef": 200,
        },
        db=object(),
    )

    assert called["topk"] == 5
    assert isinstance(called["data"], dict)
    assert called["data"]["mode"] == "dual_then_rerank"
    assert called["data"]["ef"] == 200

    assert "timing_ms" in eval_run.metrics
    assert "total_search_ms" in eval_run.metrics["timing_ms"]


@pytest.mark.asyncio
async def test_eval_runner_records_per_query_timing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.eval import runner

    ds = _Dataset(
        name="t",
        kb_id="kb",
        queries=[_Query(query_text="hello", relevant_docs=[])],
    )

    async def _fake_get_dataset(*_a, **_k):
        return ds

    monkeypatch.setattr(runner, "get_dataset", _fake_get_dataset)
    monkeypatch.setattr(
        runner.vector_db_client, "check_collection", lambda *_a, **_k: True
    )
    monkeypatch.setattr(runner, "normalize_multivector", lambda x: x)
    monkeypatch.setattr(runner, "downsample_multivector", lambda x, _k: x)

    async def _fake_embed(*_a, **_k):
        return [[0.0] * 128]

    monkeypatch.setattr(runner, "get_embeddings_from_httpx", _fake_embed)

    async def _fake_sparse(*_a, **_k):
        return []

    monkeypatch.setattr(runner, "get_sparse_embeddings", _fake_sparse)

    def _fake_search(*_a, **_k):
        return (
            [],
            {
                "candidate_gen_ms": 0.1,
                "vector_fetch_ms": 0.2,
                "maxsim_rerank_ms": 0.3,
                "total_search_ms": 0.6,
            },
        )

    monkeypatch.setattr(runner.vector_db_client, "search", _fake_search)

    class _FakeRepo:
        def __init__(self, _db):
            pass

        async def create_run(self, _run_dict):
            return None

    monkeypatch.setattr(runner, "EvalRepository", _FakeRepo)

    eval_run = await runner.run_evaluation(dataset_id="ds", config={}, db=object())
    assert eval_run.results
    assert "timing_ms" in eval_run.results[0]
    assert "embed_ms" in eval_run.results[0]["timing_ms"]

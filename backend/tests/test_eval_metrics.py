import pytest
import math
from app.eval.metrics import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    compute_all_metrics,
    EvalResult,
)

pytestmark = pytest.mark.unit


def test_mean_reciprocal_rank():
    assert mean_reciprocal_rank([1, 3, 5]) == pytest.approx(1.0)
    assert mean_reciprocal_rank([2, 3, 5]) == pytest.approx(0.5)
    assert mean_reciprocal_rank([]) == 0.0
    assert mean_reciprocal_rank([10]) == pytest.approx(0.1)


def test_ndcg_at_k():
    assert ndcg_at_k([1, 1, 1], 3) == pytest.approx(1.0)
    assert ndcg_at_k([0, 1, 0], 3) == pytest.approx(1.0 / math.log2(3), abs=1e-5)
    assert ndcg_at_k([], 3) == 0.0
    assert ndcg_at_k([0, 0, 0], 3) == 0.0


def test_precision_at_k():
    assert precision_at_k(2, 5) == pytest.approx(0.4)
    assert precision_at_k(0, 5) == 0.0
    assert precision_at_k(5, 5) == 1.0


def test_recall_at_k():
    assert recall_at_k(2, 4) == pytest.approx(0.5)
    assert recall_at_k(0, 4) == 0.0
    assert recall_at_k(4, 4) == 1.0
    assert recall_at_k(2, 0) == 0.0


def test_compute_all_metrics():
    results = [
        EvalResult(
            relevant_ranks=[1, 3],
            relevances=[1, 0, 1, 0],
            relevant_count=2,
            total_relevant=2,
        ),
        EvalResult(
            relevant_ranks=[2],
            relevances=[0, 1, 0, 0],
            relevant_count=1,
            total_relevant=2,
        ),
    ]

    summary = compute_all_metrics(results, k=4)
    assert summary.mrr == pytest.approx(0.75)
    assert summary.precision == pytest.approx(0.375)
    assert summary.recall == pytest.approx(0.75)

    res1_dcg = 1.0 + 1.0 / math.log2(4)
    res1_idcg = 1.0 + 1.0 / math.log2(3)
    res1_ndcg = res1_dcg / res1_idcg

    res2_ndcg = 1.0 / math.log2(3)

    expected_mean_ndcg = (res1_ndcg + res2_ndcg) / 2
    assert summary.ndcg == pytest.approx(expected_mean_ndcg, abs=1e-5)

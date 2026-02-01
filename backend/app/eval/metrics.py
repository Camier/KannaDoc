import math
from typing import List, NamedTuple


class EvalResult(NamedTuple):
    relevant_ranks: List[int]
    relevances: List[int]
    relevant_count: int
    total_relevant: int


class MetricsSummary(NamedTuple):
    mrr: float
    ndcg: float
    precision: float
    recall: float


def mean_reciprocal_rank(relevant_ranks: List[int]) -> float:
    if not relevant_ranks:
        return 0.0
    return 1.0 / min(relevant_ranks)


def ndcg_at_k(relevances: List[int], k: int) -> float:
    if not relevances:
        return 0.0

    relevances_at_k = relevances[:k]
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances_at_k))

    ideal_relevances = sorted(relevances, reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_relevances))

    if idcg == 0:
        return 0.0
    return dcg / idcg


def precision_at_k(relevant_count: int, k: int) -> float:
    if k <= 0:
        return 0.0
    return relevant_count / k


def recall_at_k(relevant_count: int, total_relevant: int) -> float:
    if total_relevant <= 0:
        return 0.0
    return relevant_count / total_relevant


def compute_all_metrics(results: List[EvalResult], k: int = 10) -> MetricsSummary:
    if not results:
        return MetricsSummary(0.0, 0.0, 0.0, 0.0)

    count = len(results)
    total_mrr = sum(mean_reciprocal_rank(r.relevant_ranks) for r in results)
    total_ndcg = sum(ndcg_at_k(r.relevances, k) for r in results)
    total_precision = sum(precision_at_k(r.relevant_count, k) for r in results)
    total_recall = sum(recall_at_k(r.relevant_count, r.total_relevant) for r in results)

    return MetricsSummary(
        mrr=total_mrr / count,
        ndcg=total_ndcg / count,
        precision=total_precision / count,
        recall=total_recall / count,
    )

"""
Batch Evaluation Runner for RAG Retrieval

Orchestrates evaluation of retrieval quality by:
1. Loading evaluation dataset from MongoDB
2. Executing retrieval for each query using vector_db_client
3. Comparing retrieved documents against ground truth labels
4. Computing per-query metrics (MRR, NDCG@K, P@K, R@K)
5. Aggregating metrics across all queries
6. Storing results in MongoDB
"""

import uuid
from typing import Dict, Any, List, Optional

from app.core.logging import logger
from app.db.vector_db import vector_db_client
from app.db.repositories.eval import EvalRepository, EvalRun
from app.eval.dataset import get_dataset
from app.eval.metrics import (
    EvalResult,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    compute_all_metrics,
)
from app.rag.get_embedding import get_embeddings_from_httpx
from app.utils.timezone import beijing_time_now
from app.utils.ids import to_milvus_collection_name


async def run_evaluation(
    dataset_id: str,
    config: Dict[str, Any],
    db=None,
) -> EvalRun:
    """
    Execute batch evaluation on a dataset.

    Args:
        dataset_id: ID of the evaluation dataset to use
        config: Configuration parameters:
            - top_k (int): Number of documents to retrieve per query (default: 10)
            - score_threshold (float): Minimum score threshold (default: 10)
            - nprobe (int): Milvus search parameter (optional, not used directly)
        db: MongoDB database instance (optional, for testing)

    Returns:
        EvalRun: Evaluation run with per-query results and aggregated metrics

    Raises:
        ValueError: If dataset not found
        RuntimeError: If vector collection doesn't exist
    """
    if db is None:
        from app.db.mongo import get_mongo

        mongo = await get_mongo()
        db = mongo.db
        assert db is not None, "MongoDB not connected"

    repo = EvalRepository(db)
    run_id = str(uuid.uuid4())

    top_k = config.get("top_k", 10)
    score_threshold = config.get("score_threshold", 10)

    logger.info(f"Loading evaluation dataset: {dataset_id}")
    dataset = await get_dataset(dataset_id, db=db)
    if dataset is None:
        raise ValueError(f"Dataset '{dataset_id}' not found")

    collection_name = to_milvus_collection_name(dataset.kb_id)
    if not vector_db_client.check_collection(collection_name):
        raise RuntimeError(
            f"Knowledge base '{dataset.kb_id}' not found in vector database. "
            "Ensure the knowledge base exists and has indexed documents."
        )

    logger.info(
        f"Starting evaluation run {run_id} on dataset '{dataset.name}' "
        f"({len(dataset.queries)} queries, top_k={top_k})"
    )

    per_query_results: List[Dict[str, Any]] = []
    eval_results_for_aggregation: List[EvalResult] = []
    queries_processed = 0
    queries_failed = 0

    for query in dataset.queries:
        query_text = query.query_text
        ground_truth_docs = query.relevant_docs

        try:
            logger.info(
                f"Processing query {queries_processed + 1}/{len(dataset.queries)}: '{query_text[:50]}...'"
            )

            query_embeddings = await get_embeddings_from_httpx(
                data=[query_text],
                endpoint="embed_text",
            )

            if not query_embeddings or not query_embeddings[0]:
                logger.warning(f"Empty embedding for query: '{query_text[:50]}...'")
                queries_failed += 1
                per_query_results.append(
                    {
                        "query_text": query_text,
                        "status": "failed",
                        "error": "Empty embedding returned",
                        "retrieved_docs": [],
                        "metrics": None,
                    }
                )
                continue

            search_results = vector_db_client.search(
                collection_name,
                data=query_embeddings[0],
                topk=top_k,
            )

            retrieved_docs = []
            for result in search_results:
                retrieved_docs.append(
                    {
                        "doc_id": result.get("image_id") or result.get("file_id"),
                        "file_id": result.get("file_id"),
                        "image_id": result.get("image_id"),
                        "page_number": result.get("page_number"),
                        "score": result.get("score", 0.0),
                    }
                )

            if not ground_truth_docs:
                logger.info(
                    f"No ground truth labels for query: '{query_text[:50]}...' - skipping metrics"
                )
                per_query_results.append(
                    {
                        "query_text": query_text,
                        "status": "success",
                        "retrieved_docs": retrieved_docs,
                        "ground_truth_count": 0,
                        "metrics": None,
                    }
                )
                queries_processed += 1
                continue

            relevant_doc_ids = set()
            relevance_scores_map: Dict[str, int] = {}
            for gt_doc in ground_truth_docs:
                doc_id = gt_doc.get("doc_id") or gt_doc.get("image_id")
                if doc_id:
                    relevant_doc_ids.add(doc_id)
                    relevance_scores_map[doc_id] = gt_doc.get("relevance_score", 1)

            relevant_ranks: List[int] = []
            relevances: List[int] = []
            relevant_count = 0

            for rank, retrieved in enumerate(retrieved_docs, start=1):
                doc_id = retrieved.get("doc_id")
                if doc_id in relevant_doc_ids:
                    relevant_ranks.append(rank)
                    relevances.append(relevance_scores_map.get(doc_id, 1))
                    relevant_count += 1
                else:
                    relevances.append(0)

            total_relevant = len(relevant_doc_ids)

            query_mrr = mean_reciprocal_rank(relevant_ranks)
            query_ndcg = ndcg_at_k(relevances, top_k)
            query_precision = precision_at_k(relevant_count, top_k)
            query_recall = recall_at_k(relevant_count, total_relevant)

            eval_results_for_aggregation.append(
                EvalResult(
                    relevant_ranks=relevant_ranks,
                    relevances=relevances,
                    relevant_count=relevant_count,
                    total_relevant=total_relevant,
                )
            )

            per_query_results.append(
                {
                    "query_text": query_text,
                    "status": "success",
                    "retrieved_docs": retrieved_docs,
                    "ground_truth_count": total_relevant,
                    "relevant_retrieved": relevant_count,
                    "metrics": {
                        "mrr": query_mrr,
                        "ndcg": query_ndcg,
                        "precision": query_precision,
                        "recall": query_recall,
                    },
                }
            )
            queries_processed += 1

        except Exception as e:
            logger.error(f"Failed to process query '{query_text[:50]}...': {e}")
            queries_failed += 1
            per_query_results.append(
                {
                    "query_text": query_text,
                    "status": "failed",
                    "error": str(e),
                    "retrieved_docs": [],
                    "metrics": None,
                }
            )

    logger.info(
        f"Aggregating metrics: {queries_processed} processed, {queries_failed} failed"
    )

    aggregated_metrics: Dict[str, Any] = {
        "queries_total": len(dataset.queries),
        "queries_processed": queries_processed,
        "queries_failed": queries_failed,
        "queries_with_labels": len(eval_results_for_aggregation),
    }

    if eval_results_for_aggregation:
        summary = compute_all_metrics(eval_results_for_aggregation, k=top_k)
        aggregated_metrics.update(
            {
                "mrr": summary.mrr,
                "ndcg": summary.ndcg,
                "precision": summary.precision,
                "recall": summary.recall,
            }
        )
    else:
        aggregated_metrics.update(
            {
                "mrr": 0.0,
                "ndcg": 0.0,
                "precision": 0.0,
                "recall": 0.0,
            }
        )

    eval_run = EvalRun(
        id=run_id,
        dataset_id=dataset_id,
        config=config,
        results=per_query_results,
        metrics=aggregated_metrics,
        created_at=beijing_time_now(),
    )

    try:
        run_dict = eval_run.model_dump()
        await repo.create_run(run_dict)
        logger.info(
            f"Evaluation run {run_id} completed and stored. "
            f"MRR={aggregated_metrics.get('mrr', 0):.4f}, "
            f"NDCG={aggregated_metrics.get('ndcg', 0):.4f}, "
            f"P@{top_k}={aggregated_metrics.get('precision', 0):.4f}, "
            f"R@{top_k}={aggregated_metrics.get('recall', 0):.4f}"
        )
    except Exception as e:
        logger.error(f"Failed to store evaluation run in MongoDB: {e}")
        raise RuntimeError(f"Failed to store evaluation run: {e}")

    return eval_run

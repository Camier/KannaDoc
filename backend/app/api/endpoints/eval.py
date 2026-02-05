"""
Evaluation API endpoints for RAG retrieval quality assessment.

Provides REST endpoints to:
- Create evaluation datasets from knowledge base corpus
- List and retrieve datasets
- Execute evaluation runs
- Retrieve and list evaluation results
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.logging import logger
from app.db.mongo import get_mongo
from app.eval.query_generator import generate_queries_from_corpus
from app.eval.dataset import create_dataset, get_dataset, list_datasets
from app.eval.runner import run_evaluation
from app.db.repositories.eval import EvalRepository

router = APIRouter()


# ============================================================
# Request Models
# ============================================================


class CreateDatasetRequest(BaseModel):
    """Request to create a new evaluation dataset."""

    name: str = Field(..., description="Dataset name (must be unique per KB)")
    kb_id: str = Field(..., description="Knowledge base ID")
    query_count: int = Field(
        ..., ge=1, le=500, description="Number of queries to generate (1-500)"
    )
    label_with_llm: bool = Field(
        default=False, description="Use LLM to label relevance scores"
    )


class RunEvaluationRequest(BaseModel):
    """Request to execute an evaluation run."""

    dataset_id: str = Field(..., description="Dataset ID to evaluate")
    config: Dict[str, Any] = Field(
        default_factory=lambda: {"top_k": 10, "score_threshold": 10},
        description="Retrieval configuration (top_k, score_threshold, etc.)",
    )


# ============================================================
# Response Models
# ============================================================


class QueryResponse(BaseModel):
    """Single query in a dataset."""

    query_text: str
    relevant_docs: List[Dict[str, Any]]


class DatasetResponse(BaseModel):
    """Evaluation dataset details."""

    id: str
    name: str
    kb_id: str
    query_count: int
    created_at: str
    queries: Optional[List[QueryResponse]] = None

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    """List of datasets."""

    datasets: List[DatasetResponse]


class MetricsResponse(BaseModel):
    """Aggregated metrics for an evaluation run."""

    queries_total: int
    queries_processed: int
    queries_failed: int
    queries_with_labels: int
    mrr: float = Field(..., description="Mean Reciprocal Rank")
    ndcg: float = Field(..., description="Normalized Discounted Cumulative Gain")
    precision: float = Field(..., description="Precision@K")
    recall: float = Field(..., description="Recall@K")


class RunResponse(BaseModel):
    """Evaluation run results."""

    id: str
    dataset_id: str
    config: Dict[str, Any]
    metrics: MetricsResponse
    created_at: str
    results: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    """List of evaluation runs."""

    runs: List[RunResponse]


# ============================================================
# Endpoints
# ============================================================


@router.post("/datasets", response_model=DatasetResponse, status_code=201)
async def create_evaluation_dataset(
    request: CreateDatasetRequest,
):
    """
    Create a new evaluation dataset from a knowledge base.

    Workflow:
    1. Generates queries from KB corpus using LLM
    2. Optionally labels query-document relevance with LLM
    3. Stores dataset in MongoDB

    Args:
        request: Dataset creation parameters

    Returns:
        Created dataset with metadata

    Raises:
        400: Invalid KB ID or dataset name already exists
        500: Query generation or storage failed
    """
    try:
        logger.info(
            f"Creating dataset '{request.name}' "
            f"for KB '{request.kb_id}' with {request.query_count} queries"
        )

        # Generate queries from corpus
        queries = await generate_queries_from_corpus(request.kb_id, request.query_count)
        if not queries:
            raise HTTPException(
                status_code=400,
                detail=f"No documents found in knowledge base '{request.kb_id}'",
            )

        # Create dataset with generated queries
        mongo = await get_mongo()
        dataset = await create_dataset(
            name=request.name,
            kb_id=request.kb_id,
            queries=queries,
            label_with_llm=request.label_with_llm,
            db=mongo.db,
        )

        return DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            kb_id=dataset.kb_id,
            query_count=len(dataset.queries),
            created_at=dataset.created_at.isoformat(),
        )

    except ValueError as e:
        logger.warning(f"Dataset creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to create dataset: {e}")
        raise HTTPException(
            status_code=500, detail=f"Dataset creation failed: {str(e)}"
        )


@router.get("/datasets", response_model=DatasetListResponse)
async def get_datasets(
    kb_id: str = Query(..., description="Knowledge base ID"),
):
    """
    List all evaluation datasets for a knowledge base.

    Args:
        kb_id: Knowledge base ID

    Returns:
        List of datasets (newest first)
    """
    try:
        logger.info(f"Listing datasets for KB '{kb_id}'")

        mongo = await get_mongo()
        datasets = await list_datasets(kb_id, db=mongo.db)

        return DatasetListResponse(
            datasets=[
                DatasetResponse(
                    id=ds.id,
                    name=ds.name,
                    kb_id=ds.kb_id,
                    query_count=len(ds.queries),
                    created_at=ds.created_at.isoformat(),
                )
                for ds in datasets
            ]
        )

    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve datasets: {str(e)}"
        )


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_details(
    dataset_id: str,
):
    """
    Retrieve full details of an evaluation dataset.

    Args:
        dataset_id: Dataset unique identifier

    Returns:
        Dataset with all queries and relevant documents

    Raises:
        404: Dataset not found
    """
    try:
        logger.info(f"Retrieving dataset '{dataset_id}'")

        mongo = await get_mongo()
        dataset = await get_dataset(dataset_id, db=mongo.db)

        if not dataset:
            raise HTTPException(
                status_code=404, detail=f"Dataset '{dataset_id}' not found"
            )

        return DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            kb_id=dataset.kb_id,
            query_count=len(dataset.queries),
            created_at=dataset.created_at.isoformat(),
            queries=[
                QueryResponse(
                    query_text=q.query_text,
                    relevant_docs=q.relevant_docs,
                )
                for q in dataset.queries
            ],
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve dataset: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve dataset: {str(e)}"
        )


@router.post("/run", response_model=RunResponse)
async def execute_evaluation(
    request: RunEvaluationRequest,
):
    """
    Execute an evaluation run on a dataset.

    Workflow:
    1. Validates dataset exists
    2. Retrieves documents for each query using vector search
    3. Computes metrics (MRR, NDCG@K, P@K, R@K)
    4. Stores results in MongoDB

    Args:
        request: Evaluation configuration

    Returns:
        Evaluation run with aggregated metrics

    Raises:
        400: Invalid dataset ID
        404: Dataset not found
        500: Evaluation execution failed
    """
    try:
        logger.info(
            f"Starting evaluation run on dataset '{request.dataset_id}'"
        )

        mongo = await get_mongo()
        eval_run = await run_evaluation(
            dataset_id=request.dataset_id,
            config=request.config,
            db=mongo.db,
        )

        return RunResponse(
            id=eval_run.id,
            dataset_id=eval_run.dataset_id,
            config=eval_run.config,
            metrics=MetricsResponse(**eval_run.metrics),
            created_at=eval_run.created_at.isoformat(),
        )

    except ValueError as e:
        logger.warning(f"Evaluation run failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to execute evaluation: {e}")
        raise HTTPException(
            status_code=500, detail=f"Evaluation execution failed: {str(e)}"
        )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run_results(
    run_id: str,
):
    """
    Retrieve full results of an evaluation run.

    Args:
        run_id: Evaluation run ID

    Returns:
        Evaluation run with per-query results and metrics

    Raises:
        404: Run not found
    """
    try:
        logger.info(f"Retrieving run '{run_id}'")

        mongo = await get_mongo()
        assert mongo.db is not None, "MongoDB not connected"
        repo = EvalRepository(mongo.db)
        run_dict = await repo.get_run(run_id)

        if not run_dict:
            raise HTTPException(
                status_code=404, detail=f"Evaluation run '{run_id}' not found"
            )

        if "_id" in run_dict:
            run_dict["id"] = run_dict.pop("_id")

        return RunResponse(
            id=run_dict["id"],
            dataset_id=run_dict["dataset_id"],
            config=run_dict["config"],
            metrics=MetricsResponse(**run_dict["metrics"]),
            created_at=run_dict["created_at"].isoformat(),
            results=run_dict["results"],
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve run: {str(e)}")


@router.get("/runs", response_model=RunListResponse)
async def get_runs_for_dataset(
    dataset_id: str = Query(..., description="Dataset ID"),
):
    """
    List all evaluation runs for a dataset.

    Args:
        dataset_id: Dataset ID

    Returns:
        List of evaluation runs (newest first)
    """
    try:
        logger.info(
            f"Listing runs for dataset '{dataset_id}'"
        )

        mongo = await get_mongo()
        assert mongo.db is not None, "MongoDB not connected"
        repo = EvalRepository(mongo.db)

        cursor = repo.runs_collection.find({"dataset_id": dataset_id}).sort(
            "created_at", -1
        )
        runs = []

        async for run_dict in cursor:
            # Map MongoDB _id to id
            if "_id" in run_dict:
                run_dict["id"] = run_dict.pop("_id")

            runs.append(
                RunResponse(
                    id=run_dict["id"],
                    dataset_id=run_dict["dataset_id"],
                    config=run_dict["config"],
                    metrics=MetricsResponse(**run_dict["metrics"]),
                    created_at=run_dict["created_at"].isoformat(),
                )
            )

        return RunListResponse(runs=runs)

    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve runs: {str(e)}"
        )

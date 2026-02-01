"""
Dataset Management for RAG Evaluation

Creates, retrieves, and manages evaluation datasets with optional LLM labeling.
Integrates with Milvus for document retrieval and MongoDB for storage.
"""

from typing import List, Dict, Any, Optional
import uuid

from app.core.logging import logger
from app.db.vector_db import vector_db_client
from app.db.repositories.eval import EvalRepository, EvalDataset, EvalQuery
from app.utils.timezone import beijing_time_now
from app.utils.ids import to_milvus_collection_name
from pymongo.errors import DuplicateKeyError


async def create_dataset(
    name: str,
    kb_id: str,
    queries: List[str],
    label_with_llm: bool = True,
    topk: int = 10,
    db=None,
) -> EvalDataset:
    """
    Create an evaluation dataset with query-document pairs.

    Args:
        name: Dataset name (must be unique per knowledge base)
        kb_id: Knowledge base ID to retrieve documents from
        queries: List of query texts
        label_with_llm: If True, use LLM to score query-document relevance (default: True)
        topk: Number of documents to retrieve per query (default: 10)
        db: MongoDB database instance (optional, for testing)

    Returns:
        EvalDataset: Created dataset with labeled query-document pairs

    Raises:
        ValueError: If dataset name already exists for this knowledge base
        RuntimeError: If vector collection doesn't exist or retrieval fails
    """
    if db is None:
        from app.db.mongo import get_mongo

        mongo = await get_mongo()
        db = mongo.db
        assert db is not None, "MongoDB not connected"

    repo = EvalRepository(db)
    dataset_id = str(uuid.uuid4())

    existing = await repo.datasets_collection.find_one({"kb_id": kb_id, "name": name})
    if existing:
        raise ValueError(
            f"Dataset '{name}' already exists for knowledge base '{kb_id}'. "
            "Please use a unique name."
        )

    collection_name = to_milvus_collection_name(kb_id)
    if not vector_db_client.check_collection(collection_name):
        raise RuntimeError(
            f"Knowledge base '{kb_id}' not found in vector database. "
            "Ensure the knowledge base exists and has indexed documents."
        )

    eval_queries = []
    for query_text in queries:
        try:
            logger.info(
                f"Retrieving documents for query: '{query_text}' from '{kb_id}'"
            )

            relevant_docs = []
            # TODO: Integrate embedding service + Milvus search
            # query_embedding = await model_server.embed_query(query_text)
            # search_results = vector_db_client.search(collection_name, query_embedding, topk)
            # relevant_docs = format_search_results(search_results)

            if label_with_llm:
                # TODO: Integrate labeler.py (Task 3)
                # from app.eval.labeler import label_relevance
                # relevant_docs = await label_relevance(query_text, relevant_docs)
                logger.warning(
                    f"LLM labeling skipped for '{query_text[:50]}...' - labeler.py pending"
                )

            eval_queries.append(
                EvalQuery(query_text=query_text, relevant_docs=relevant_docs)
            )

        except Exception as e:
            logger.error(f"Failed to retrieve documents for query '{query_text}': {e}")
            eval_queries.append(EvalQuery(query_text=query_text, relevant_docs=[]))

    dataset = EvalDataset(
        id=dataset_id,
        name=name,
        kb_id=kb_id,
        queries=eval_queries,
        created_at=beijing_time_now(),
    )

    try:
        dataset_dict = dataset.model_dump()
        dataset_dict["queries"] = [
            {"query_text": q.query_text, "relevant_docs": q.relevant_docs}
            for q in dataset.queries
        ]
        await repo.create_dataset(dataset_dict)
        logger.info(
            f"Created dataset '{name}' (ID: {dataset_id}) with {len(queries)} queries"
        )
        return dataset

    except DuplicateKeyError:
        raise ValueError(f"Dataset ID '{dataset_id}' already exists (UUID collision)")
    except Exception as e:
        logger.error(f"Failed to store dataset in MongoDB: {e}")
        raise RuntimeError(f"Database error: {e}")


async def get_dataset(dataset_id: str, db=None) -> Optional[EvalDataset]:
    """
    Retrieve an evaluation dataset by ID.

    Args:
        dataset_id: Dataset unique identifier
        db: MongoDB database instance (optional, for testing)

    Returns:
        EvalDataset if found, None otherwise
    """
    if db is None:
        from app.db.mongo import get_mongo

        mongo = await get_mongo()
        db = mongo.db
        assert db is not None, "MongoDB not connected"

    repo = EvalRepository(db)
    dataset_dict = await repo.get_dataset(dataset_id)

    if not dataset_dict:
        return None

    if "_id" in dataset_dict:
        dataset_dict["id"] = dataset_dict.pop("_id")

    dataset_dict["queries"] = [EvalQuery(**q) for q in dataset_dict["queries"]]

    return EvalDataset(**dataset_dict)


async def list_datasets(kb_id: str, db=None) -> List[EvalDataset]:
    """
    List all evaluation datasets for a knowledge base.

    Args:
        kb_id: Knowledge base ID
        db: MongoDB database instance (optional, for testing)

    Returns:
        List of EvalDataset objects, sorted by creation time (newest first)
    """
    if db is None:
        from app.db.mongo import get_mongo

        mongo = await get_mongo()
        db = mongo.db
        assert db is not None, "MongoDB not connected"

    repo = EvalRepository(db)
    cursor = repo.datasets_collection.find({"kb_id": kb_id}).sort("created_at", -1)
    datasets = []

    async for dataset_dict in cursor:
        if "_id" in dataset_dict:
            dataset_dict["id"] = dataset_dict.pop("_id")

        dataset_dict["queries"] = [EvalQuery(**q) for q in dataset_dict["queries"]]

        datasets.append(EvalDataset(**dataset_dict))

    return datasets

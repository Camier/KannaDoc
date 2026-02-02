"""
Dataset Management for RAG Evaluation

Creates, retrieves, and manages evaluation datasets with optional LLM labeling.
Integrates with Milvus for document retrieval and MongoDB for storage.
"""

from typing import List, Dict, Any, Optional
import uuid
import asyncio
from functools import partial

from app.core.logging import logger
from app.db.vector_db import vector_db_client
from app.db.repositories.eval import EvalRepository, EvalDataset, EvalQuery
from app.utils.timezone import beijing_time_now
from app.utils.ids import to_milvus_collection_name
from pymongo.errors import DuplicateKeyError
from app.rag.get_embedding import get_embeddings_from_httpx
from app.eval.labeler import label_relevance


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

            query_embeddings = await get_embeddings_from_httpx(
                data=[query_text],
                endpoint="embed_text",
            )

            if not query_embeddings or not query_embeddings[0]:
                logger.warning(f"Empty embedding for query: '{query_text[:50]}...'")
                eval_queries.append(EvalQuery(query_text=query_text, relevant_docs=[]))
                continue

            loop = asyncio.get_running_loop()
            search_func = partial(
                vector_db_client.search,
                collection_name,
                data=query_embeddings[0],
                topk=topk,
            )
            search_results = await loop.run_in_executor(None, search_func)

            if not search_results:
                logger.info(f"No search results for query: '{query_text[:50]}...'")
                eval_queries.append(EvalQuery(query_text=query_text, relevant_docs=[]))
                continue

            relevant_docs = []

            llm_config = {
                "model_name": "gemini-3-flash",
                "temperature": 0.0,
                "max_length": 10,
            }

            for result in search_results:
                file_id = result.get("file_id")
                image_id = result.get("image_id")
                page_number = result.get("page_number")

                filename = "Unknown"
                if file_id:
                    file_doc = await db.files.find_one(
                        {"file_id": file_id, "is_delete": False},
                        projection={"filename": 1},
                    )
                    if file_doc:
                        filename = file_doc.get("filename", "Unknown")

                doc_repr = f"Document: {filename}, Page {page_number}"

                relevance_score = 0
                if label_with_llm:
                    for attempt in range(3):
                        try:
                            relevance_score = await label_relevance(
                                query=query_text,
                                document=doc_repr,
                                llm_config=llm_config,
                            )
                            break
                        except Exception as e:
                            if attempt < 2:
                                logger.warning(
                                    f"Labeling retry {attempt + 1} for '{query_text[:30]}...' - {e}"
                                )
                            else:
                                logger.warning(
                                    f"Labeling failed after 3 attempts for '{query_text[:30]}...' - skipping"
                                )
                                relevance_score = 0

                if relevance_score >= 2:
                    relevant_docs.append(
                        {
                            "doc_id": image_id,  # CRITICAL: image_id required for runner.py ID matching
                            "file_id": file_id,
                            "image_id": image_id,
                            "page_number": page_number,
                            "relevance_score": relevance_score,
                        }
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

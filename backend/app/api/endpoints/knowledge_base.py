"""
Knowledge Base API endpoints for managing document collections.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.db.vector_db import vector_db_client
from app.rag.get_embedding import get_embeddings_from_httpx, get_sparse_embeddings
from app.core.embeddings import normalize_multivector, downsample_multivector
from app.core.config import settings
from app.core.logging import logger
from app.core.rag.retrieval_params import normalize_top_k as normalize_rag_top_k
from app.utils.thesis_urls import build_thesis_page_image_url
from app.utils.ids import to_milvus_collection_name

router = APIRouter()


class SearchPreviewRequest(BaseModel):
    """Request model for search preview"""

    query: str
    top_k: int = 10
    min_score: Optional[float] = None
    retrieval_mode: Optional[str] = None


class SearchPreviewResult(BaseModel):
    """Single search result with metadata"""

    image_id: str
    file_id: str
    page_number: int
    score: float
    filename: str
    minio_url: str


class SearchPreviewResponse(BaseModel):
    """Response model for search preview"""

    query: str
    results: List[SearchPreviewResult]
    total_results: int
    collection_name: str


@router.post(
    "/knowledge-base/{kb_id}/search-preview", response_model=SearchPreviewResponse
)
async def search_preview(
    kb_id: str,
    request: SearchPreviewRequest,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """
    Preview vector search results without LLM generation.

    This endpoint allows debugging RAG quality by seeing:
    - Which document chunks match their query
    - Similarity scores for each match
    - Page numbers and filenames

    Args:
        kb_id: Knowledge base ID to search
        request: Search parameters (query, top_k, min_score)
        repo_manager: Database repository manager

    Returns:
        Search results with scores and metadata

    Raises:
        HTTPException 404: Knowledge base not found
        HTTPException 500: Embedding or vector search failed
    """

    # Verify KB exists
    kb = await repo_manager.knowledge_base.get_knowledge_base_by_id(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Get embeddings for query
    try:
        logger.info(f"Generating embeddings for query: {request.query}")
        raw_embeddings = await get_embeddings_from_httpx(
            [request.query], endpoint="embed_text"
        )

        if not raw_embeddings:
            raise HTTPException(
                status_code=500, detail="Failed to generate query embeddings"
            )

        # Normalize and downsample multi-vector embeddings (ColQwen format)
        query_embeddings = normalize_multivector(raw_embeddings)
        query_embeddings = downsample_multivector(
            query_embeddings, settings.rag_max_query_vecs
        )
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Embedding generation failed: {str(e)}"
        )

    # Search Milvus
    collection_name = to_milvus_collection_name(kb_id)

    # Determine retrieval mode (defaulting to runtime settings).
    retrieval_mode = request.retrieval_mode or getattr(settings, "rag_retrieval_mode", "dense")
    # Backward compatibility: older deployments only used rag_hybrid_enabled.
    if retrieval_mode == "dense" and getattr(settings, "rag_hybrid_enabled", False):
        retrieval_mode = "hybrid"

    # Normalize top_k consistently with ChatService to avoid drift.
    top_k = normalize_rag_top_k(
        int(request.top_k or 0),
        retrieval_mode=retrieval_mode,
        default_top_k=int(getattr(settings, "rag_default_top_k", 50)),
        top_k_cap=int(getattr(settings, "rag_top_k_cap", 120)),
        sparse_min_k=int(getattr(settings, "rag_search_limit_min", 50)),
    )

    try:
        # Ensure collection is loaded
        if not vector_db_client.check_collection(collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Vector collection not found: {collection_name}",
            )

        vector_db_client.load_collection(collection_name)

        # Optionally compute sparse query for hybrid/sparse modes.
        sparse_query = None
        if retrieval_mode in ["hybrid", "sparse_then_rerank", "dual_then_rerank"]:
            try:
                sparse_result = await get_sparse_embeddings([request.query])
                if sparse_result and len(sparse_result) > 0:
                    sparse_query = sparse_result[0]
            except Exception as e:
                logger.warning(f"Sparse embedding failed, falling back to dense-only: {e}")

        # Prepare search data based on retrieval mode.
        if retrieval_mode in ["sparse_then_rerank", "dual_then_rerank"] and sparse_query:
            search_data = {
                "mode": retrieval_mode,
                "dense_vecs": query_embeddings,
                "sparse_query": sparse_query,
            }
        elif retrieval_mode == "hybrid" and sparse_query:
            # Hybrid search expects dense+sparse vectors (length-matched).
            search_data = {
                "dense_vecs": query_embeddings,
                "sparse_vecs": [sparse_query] * len(query_embeddings),
            }
        else:
            search_data = query_embeddings

        # Perform search
        search_results = vector_db_client.search(
            collection_name=collection_name, data=search_data, topk=top_k
        )

        if not search_results:
            return SearchPreviewResponse(
                query=request.query,
                results=[],
                total_results=0,
                collection_name=collection_name,
            )

    except Exception as e:
        logger.error(f"Milvus search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")

    # Batch-fetch metadata for (file_id, image_id). This avoids N+1 and provides the
    # image minio_url when available. In thesis deployments, Mongo "files" may be empty
    # (or file_id may not match), so we also provide a safe fallback image URL.
    file_infos: list[dict] = []
    try:
        file_image_pairs = [
            (r.get("file_id", ""), r.get("image_id", "")) for r in (search_results or [])
        ]
        file_infos = await repo_manager.file.get_files_and_images_batch(file_image_pairs)
    except Exception as e:
        logger.warning(f"Failed to fetch file/image metadata in batch: {e}")
        file_infos = [{"status": "failed"} for _ in (search_results or [])]

    # Format results
    formatted_results = []
    for result, file_info in zip(search_results, file_infos):
        file_id = result.get("file_id", "") or ""
        page_number = int(result.get("page_number", 0) or 0)

        # Apply score filter if specified
        score = result.get("score", 0.0)
        if request.min_score is not None and score < request.min_score:
            continue

        filename = "Unknown"
        image_url = ""
        if isinstance(file_info, dict) and file_info.get("status") == "success":
            filename = str(file_info.get("file_name") or file_id or "Unknown")
            # For preview we want the page image.
            image_url = str(file_info.get("image_minio_url") or "")
        else:
            # Thesis fallback: when Mongo metadata doesn't exist / doesn't match, we can still
            # render a preview image from the locally served PDFs.
            filename = str(file_id or "Unknown")
            if str(kb_id).startswith("thesis_") and file_id and page_number:
                image_url = build_thesis_page_image_url(
                    settings.api_version_url,
                    file_id=str(file_id),
                    page_number=page_number,
                    dpi=150,
                )

        formatted_results.append(
            SearchPreviewResult(
                image_id=result.get("image_id", ""),
                file_id=file_id,
                page_number=page_number,
                score=score,
                filename=filename,
                # Historical field name. In preview UI this is rendered as an <img src>.
                minio_url=image_url,
            )
        )

    return SearchPreviewResponse(
        query=request.query,
        results=formatted_results,
        total_results=len(formatted_results),
        collection_name=collection_name,
    )

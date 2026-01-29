"""
Knowledge Base API endpoints for managing document collections.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.user import User
from app.core.security import get_current_user
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.db.vector_db import vector_db_client
from app.rag.get_embedding import get_embeddings_from_httpx
from app.core.logging import logger

router = APIRouter()


class SearchPreviewRequest(BaseModel):
    """Request model for search preview"""

    query: str
    top_k: int = 10
    min_score: Optional[float] = None


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
    current_user: User = Depends(get_current_user),
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """
    Preview vector search results without LLM generation.

    This endpoint allows users to debug RAG quality by seeing:
    - Which document chunks match their query
    - Similarity scores for each match
    - Page numbers and filenames

    Useful for understanding why certain answers are generated.

    Args:
        kb_id: Knowledge base ID to search
        request: Search parameters (query, top_k, min_score)
        current_user: Authenticated user
        repo_manager: Database repository manager

    Returns:
        Search results with scores and metadata

    Raises:
        HTTPException 404: Knowledge base not found
        HTTPException 403: User doesn't have access to this KB
    """

    # Verify KB exists and user has access
    kb = await repo_manager.knowledge_base.get_knowledge_base_by_id(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Check ownership (respect single-tenant mode if enabled)
    if kb["username"] != current_user.username:
        from app.core.config import settings

        if not getattr(settings, "single_tenant_mode", False):
            raise HTTPException(
                status_code=403, detail="You don't have access to this knowledge base"
            )

    # Get embeddings for query
    try:
        logger.info(f"Generating embeddings for query: {request.query}")
        query_embeddings = await get_embeddings_from_httpx(request.query)

        if not query_embeddings:
            raise HTTPException(
                status_code=500, detail="Failed to generate query embeddings"
            )
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Embedding generation failed: {str(e)}"
        )

    # Search Milvus
    collection_name = f"colqwen{kb_id.replace('-', '_')}"

    try:
        # Ensure collection is loaded
        if not vector_db_client.check_collection(collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Vector collection not found: {collection_name}",
            )

        vector_db_client.load_collection(collection_name)

        # Perform search
        search_results = vector_db_client.search(
            collection_name=collection_name, data=query_embeddings, topk=request.top_k
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

    # Get file metadata for results
    file_ids = list(set([r["file_id"] for r in search_results if "file_id" in r]))

    # Fetch file details from MongoDB
    files_map = {}
    try:
        files = await repo_manager.file.get_files_by_ids(file_ids)
        files_map = {f["file_id"]: f for f in files}
    except Exception as e:
        logger.warning(f"Failed to fetch file metadata: {e}")
        # Continue with empty files_map - we'll return partial results

    # Format results
    formatted_results = []
    for result in search_results:
        file_id = result.get("file_id", "")
        file_meta = files_map.get(file_id, {})

        # Apply score filter if specified
        score = result.get("score", 0.0)
        if request.min_score is not None and score < request.min_score:
            continue

        formatted_results.append(
            SearchPreviewResult(
                image_id=result.get("image_id", ""),
                file_id=file_id,
                page_number=result.get("page_number", 0),
                score=score,
                filename=file_meta.get("filename", "Unknown"),
                minio_url=file_meta.get("minio_url", ""),
            )
        )

    return SearchPreviewResponse(
        query=request.query,
        results=formatted_results,
        total_results=len(formatted_results),
        collection_name=collection_name,
    )

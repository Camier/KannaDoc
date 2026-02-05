from typing import List
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from app.db.redis import redis
from app.db.milvus import MilvusManager
from app.db.db_utils import format_page_response
from app.models.conversation import GetUserFiles
from app.models.knowledge_base import (
    BulkDeleteRequestItem,
    KnowledgeBaseCreate,
    KnowledgeBaseRenameInput,
    KnowledgeBaseSummary,
    PageResponse,
)
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.core.config import settings
from app.rag.convert_file import (
    save_file_to_minio,
)
from app.utils.kafka_producer import kafka_producer_manager
from app.core.logging import logger
from app.db.miniodb import async_minio_manager

router = APIRouter()
milvus_client = MilvusManager()

# Use settings.default_username instead of hardcoded string
USERNAME = settings.default_username


# 查询所有知识库
@router.get(
    "/knowledge_bases", response_model=List[KnowledgeBaseSummary]
)
async def get_knowledge_bases(
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    knowledge_bases = await repo_manager.knowledge_base.get_knowledge_bases_by_user(
        USERNAME
    )
    if not knowledge_bases:
        return []

    return [
        {
            "knowledge_base_id": kb["knowledge_base_id"],
            "knowledge_base_name": kb["knowledge_base_name"],
            "description": kb.get("description", ""),
            "created_at": kb["created_at"].isoformat(),
            "last_modify_at": kb["last_modify_at"].isoformat(),
            "file_number": len(kb.get("files", [])),
            "is_delete": kb.get("is_delete", False),
        }
        for kb in knowledge_bases
    ]


# 创建知识库
@router.post("/knowledge_bases", status_code=201)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.knowledge_base.create_knowledge_base(
        username=USERNAME,
        knowledge_base_name=knowledge_base.knowledge_base_name,
        knowledge_base_id=knowledge_base.knowledge_base_id,
        is_temp=knowledge_base.is_temp,
    )
    return result


@router.post("/knowledge_bases/rename")
async def rename_knowledge_base(
    renameInput: KnowledgeBaseRenameInput,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.knowledge_base.update_knowledge_base_name(
        renameInput.knowledge_base_id, renameInput.knowledge_base_new_name
    )
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return result


# 删除知识库
@router.delete("/knowledge_bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.knowledge_base.delete_knowledge_base(kb_id)
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


# 批量删除知识库
@router.post("/knowledge_bases/bulk-delete")
async def bulk_delete_knowledge_bases(
    items: List[BulkDeleteRequestItem],
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    results = []
    for item in items:
        result = await repo_manager.knowledge_base.delete_knowledge_base(
            item.knowledge_base_id
        )
        results.append(
            {
                "knowledge_base_id": item.knowledge_base_id,
                "status": result["status"],
                "message": result.get("message"),
            }
        )
    return {"results": results}


# 查询知识库详情
@router.get("/knowledge_bases/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    kb = await repo_manager.knowledge_base.get_knowledge_base_by_id(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    return {
        "knowledge_base_id": kb["knowledge_base_id"],
        "knowledge_base_name": kb["knowledge_base_name"],
        "description": kb.get("description", ""),
        "created_at": kb["created_at"].isoformat(),
        "last_modify_at": kb["last_modify_at"].isoformat(),
        "file_count": kb.get("file_count", 0),
        "files": kb.get("files", []),
    }


@router.post("/knowledge_bases/{kb_id}/files")
async def upload_file_to_kb(
    kb_id: str,
    file: UploadFile,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    knowledge_base = await repo_manager.knowledge_base.get_knowledge_base_by_id(kb_id)
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    minio_filename, minio_url = await save_file_to_minio(USERNAME, file)

    file_id = f"{USERNAME}_{uuid.uuid4()}"
    file_data = {
        "file_id": file_id,
        "filename": file.filename,
        "minio_filename": minio_filename,
        "minio_url": minio_url,
        "uploaded_at": datetime.now().isoformat(),
    }

    await repo_manager.knowledge_base.add_file_to_knowledge_base(
        kb_id, file_data
    )

    return file_data


@router.get("/knowledge_bases/{kb_id}/files")
async def get_kb_files(
    kb_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    files = await repo_manager.knowledge_base.get_files_by_knowledge_base_id(kb_id)
    return {"files": files}


@router.delete("/knowledge_bases/{kb_id}/files/{file_id}")
async def delete_file_from_kb(
    kb_id: str,
    file_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.knowledge_base.delete_file_from_knowledge_base(
        kb_id, file_id
    )
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

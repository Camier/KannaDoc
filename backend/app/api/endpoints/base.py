from typing import List
import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from app.db.redis import redis
from app.db.milvus import milvus_client
from app.db.db_utils import format_page_response
from app.models.conversation import GetUserFiles
from app.models.knowledge_base import (
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
from app.utils.ids import to_milvus_collection_name

router = APIRouter()

# Use settings.default_username instead of hardcoded string
USERNAME = settings.default_username


class FileDownloadRequest(BaseModel):
    username: str = Field(..., description="Username (auth-free mode: default user)")
    minio_filename: str = Field(..., description="MinIO object key for the file")


class KnowledgeBaseBulkDeleteRequestItem(BaseModel):
    knowledge_base_id: str = Field(..., description="Knowledge base id")


# 查询所有知识库
@router.get("/knowledge_bases", response_model=List[KnowledgeBaseSummary])
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
    knowledge_base_id = f"{USERNAME}_{uuid.uuid4()}"
    result = await repo_manager.knowledge_base.create_knowledge_base(
        username=USERNAME,
        knowledge_base_name=knowledge_base.knowledge_base_name,
        knowledge_base_id=knowledge_base_id,
        is_delete=False,
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

    # Drop associated Milvus collection
    collection_name = to_milvus_collection_name(kb_id)
    try:
        milvus_client.delete_collection(collection_name)
    except Exception as e:
        logger.warning(f"Failed to drop Milvus collection {collection_name}: {e}")

    return result


# 删除用户的所有临时知识库 (temp KBs created during chat file uploads)
@router.delete("/temp_knowledge_base/{username}")
async def delete_temp_knowledge_bases(
    username: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """Delete all temporary knowledge bases for a user.

    Temp KBs are created during chat file uploads with IDs starting with 'temp_'.
    The frontend calls this on ChatBox/FlowEditor mount to clean up stale collections.
    """
    all_kbs = await repo_manager.knowledge_base.get_all_knowledge_bases_by_user(
        username
    )
    temp_kbs = [
        kb for kb in all_kbs if kb.get("knowledge_base_id", "").startswith("temp_")
    ]

    if not temp_kbs:
        return {"status": "success", "deleted_count": 0}

    deleted_count = 0
    errors = []
    for kb in temp_kbs:
        kb_id = kb["knowledge_base_id"]
        try:
            result = await repo_manager.knowledge_base.delete_knowledge_base(kb_id)

            collection_name = to_milvus_collection_name(kb_id)
            try:
                milvus_client.delete_collection(collection_name)
            except Exception as e:
                logger.warning(
                    f"Failed to drop Milvus collection {collection_name}: {e}"
                )

            if result.get("status") != "failed":
                deleted_count += 1
            else:
                errors.append({"kb_id": kb_id, "error": result.get("message")})
        except Exception as e:
            logger.error(f"Failed to delete temp KB {kb_id}: {e}")
            errors.append({"kb_id": kb_id, "error": str(e)})

    response = {"status": "success", "deleted_count": deleted_count}
    if errors:
        response["status"] = "partial_success"
        response["errors"] = errors
    return response


# 批量删除知识库
@router.post("/knowledge_bases/bulk-delete")
async def bulk_delete_knowledge_bases(
    items: List[KnowledgeBaseBulkDeleteRequestItem],
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
    files: List[UploadFile],
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    knowledge_base = await repo_manager.knowledge_base.get_knowledge_base_by_id(kb_id)
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    task_id = USERNAME + "_" + str(uuid.uuid4())
    total_files = len(files)
    redis_connection = await redis.get_task_connection()
    await redis_connection.hset(
        f"task:{task_id}",
        mapping={
            "status": "processing",
            "total": total_files,
            "processed": 0,
            "message": "Initializing file processing...",
        },
    )
    await redis_connection.expire(f"task:{task_id}", 3600)

    upload_tasks = [save_file_to_minio(USERNAME, file) for file in files]
    upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

    file_meta_list = []
    return_files = []

    for file, upload_result in zip(files, upload_results):
        if isinstance(upload_result, BaseException):
            logger.error(f"Failed to upload {file.filename}: {upload_result}")
            raise upload_result

        minio_filename, minio_url = upload_result

        file_id = f"{USERNAME}_{uuid.uuid4()}"
        file_data = {
            "file_id": file_id,
            "filename": file.filename,
            "minio_filename": minio_filename,
            "minio_url": minio_url,
            "uploaded_at": datetime.now().isoformat(),
        }

        await repo_manager.knowledge_base.knowledge_base_add_file(
            knowledge_base_id=kb_id,
            file_id=file_id,
            original_filename=str(file.filename or ""),
            minio_filename=minio_filename,
            minio_url=minio_url,
        )

        file_meta_list.append(
            {
                "file_id": file_id,
                "minio_filename": minio_filename,
                "original_filename": file.filename,
                "minio_url": minio_url,
            }
        )
        return_files.append(file_data)

    for meta in file_meta_list:
        logger.info(
            f"send {task_id} to kafka, file name {meta['original_filename']}, knowledge id {kb_id}."
        )
        await kafka_producer_manager.send_embedding_task(
            task_id=task_id,
            username=USERNAME,
            knowledge_db_id=kb_id,
            file_meta=meta,
            priority="1",
        )

    return {"task_id": task_id, "files": return_files}


@router.get("/knowledge_bases/{kb_id}/files")
async def get_kb_files(
    kb_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    files = await repo_manager.knowledge_base.get_files_by_knowledge_base_id(kb_id)
    return {"files": files}


@router.post("/files/download")
async def get_file_download_url(payload: FileDownloadRequest):
    """Return a fresh presigned URL for a KB file.

    Rationale: KB file list may contain missing/expired `minio_url` values (e.g. corpus
    ingested via scripts). Frontend should call this endpoint using `minio_filename`.
    """

    minio_filename = payload.minio_filename.strip()
    if not minio_filename:
        raise HTTPException(status_code=400, detail="minio_filename is required")

    # Best-effort validation (helps return a clear error instead of a dead link)
    try:
        exists = await async_minio_manager.validate_file_existence(minio_filename)
    except Exception as e:
        logger.warning(f"MinIO existence check failed for {minio_filename}: {e}")
        exists = True

    if not exists:
        raise HTTPException(status_code=404, detail="file_not_found")

    url = await async_minio_manager.create_presigned_url(minio_filename)
    return {"url": url}


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

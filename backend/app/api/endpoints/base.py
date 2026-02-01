from typing import List
import uuid
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
from app.models.user import User
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.core.config import settings
from app.core.security import get_current_user, verify_username_match
from app.rag.convert_file import (
    save_file_to_minio,
)
from app.utils.kafka_producer import kafka_producer_manager
from app.core.logging import logger
from app.db.miniodb import async_minio_manager

router = APIRouter()
milvus_client = MilvusManager()


# 查询指定用户的所有知识库
@router.get(
    "/users/{username}/knowledge_bases", response_model=List[KnowledgeBaseSummary]
)
async def get_knowledge_bases_by_user(
    username: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, username)
    knowledge_bases = await repo_manager.knowledge_base.get_knowledge_bases_by_user(
        username
    )
    if not knowledge_bases:
        return []

    return [
        {
            "knowledge_base_id": knowledge_base["knowledge_base_id"],
            "knowledge_base_name": knowledge_base["knowledge_base_name"],
            "created_at": knowledge_base["created_at"].isoformat(),
            "last_modify_at": knowledge_base["last_modify_at"].isoformat(),
            "file_number": len(knowledge_base["files"]),
        }
        for knowledge_base in knowledge_bases
    ]


# 创建新知识库
@router.post("/knowledge_base", response_model=dict)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, knowledge_base.username)
    knowledge_base_id = (
        knowledge_base.username + "_" + str(uuid.uuid4())
    )  # 生成 UUIDv4,
    await repo_manager.knowledge_base.create_knowledge_base(
        username=knowledge_base.username,
        knowledge_base_name=knowledge_base.knowledge_base_name,
        knowledge_base_id=knowledge_base_id,
        is_delete=False,
    )
    milvus_client.create_collection("colqwen" + knowledge_base_id.replace("-", "_"))
    return {"status": "success"}


# 修改知识库名称
@router.post("/knowledge_base/rename", response_model=dict)
async def re_name(
    renameInput: KnowledgeBaseRenameInput,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(
        current_user, renameInput.knowledge_base_id.split("_")[0]
    )

    result = await repo_manager.knowledge_base.update_knowledge_base_name(
        renameInput.knowledge_base_id, renameInput.knowledge_base_new_name
    )
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


# 批量删除接口
@router.delete("/files/bulk-delete", response_model=dict)
async def bulk_delete_files(
    delete_list: List[BulkDeleteRequestItem],
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    """
    批量删除知识库文件
    - 验证每个知识库的用户权
    - 执行批量删除操作
    - 返回详细操作结果
    """

    # 权限验证预处理
    valid_operations = []
    invalid_items = []

    for item in delete_list:
        try:
            # 解析用户名（保持与单个删除相同的逻辑）
            if "temp" in item.knowledge_id:
                username = item.knowledge_id.split("_")[1]
            else:
                username = item.knowledge_id.split("_")[0]

            # 验证用户权限
            if (not settings.single_tenant_mode) and username != current_user.username:
                invalid_items.append(
                    {
                        "knowledge_id": item.knowledge_id,
                        "file_id": item.file_id,
                        "reason": "Permission denied",
                    }
                )
                continue

            valid_operations.append(item.model_dump())

        except Exception as e:
            invalid_items.append(
                {
                    "knowledge_id": item.knowledge_id,
                    "file_id": item.file_id,
                    "reason": f"Invalid format: {str(e)}",
                }
            )

    # 执行批量删除
    deletion_result = (
        await repo_manager.knowledge_base.bulk_delete_files_from_knowledge(
            valid_operations
        )
    )

    # 处理 Milvus 删除
    if deletion_result.get("status") in ["success", "partial_success"]:
        for item in valid_operations:
            try:
                collection_name = "colqwen" + item["knowledge_id"].replace("-", "_")
                milvus_client.delete_files(collection_name, [item["file_id"]])
            except Exception as e:
                logger.error(f"Milvus 删除失败 {item}: {str(e)}")
                if "milvus_errors" not in deletion_result:
                    deletion_result["milvus_errors"] = []
                deletion_result["milvus_errors"].append(
                    {
                        "knowledge_id": item["knowledge_id"],
                        "file_id": item["file_id"],
                        "error": str(e),
                    }
                )

    # 构建最终响应
    response = {
        "status": "success",
        "detail": {
            "processed_count": len(valid_operations),
            "invalid_items": invalid_items,
            "database_result": deletion_result,
        },
    }

    # 处理部分成功情况
    if invalid_items or deletion_result["status"] != "success":
        response["status"] = "partial_success"
        if deletion_result["status"] == "error":
            response["status"] = "failed"

    return response


# 删除知识库文件
@router.delete("/file/{knowledge_base_id}/{file_id}", response_model=dict)
async def delete_file(
    knowledge_base_id: str,
    file_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    if "temp" in knowledge_base_id:
        username = knowledge_base_id.split("_")[1]
    else:
        username = knowledge_base_id.split("_")[0]
    await verify_username_match(current_user, username)
    result = await repo_manager.knowledge_base.delete_file_from_knowledge_base(
        knowledge_base_id, file_id
    )
    milvus_client.delete_files(
        "colqwen" + knowledge_base_id.replace("-", "_"), [file_id]
    )
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


# 删除知识库
@router.delete("/knowledge_base/{knowledge_base_id}", response_model=dict)
async def delete_knowledge_base(
    knowledge_base_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, knowledge_base_id.split("_")[0])
    result = await repo_manager.knowledge_base.delete_knowledge_base(knowledge_base_id)
    milvus_client.delete_collection("colqwen" + knowledge_base_id.replace("-", "_"))
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


# 清空未被对话引用的临时数据库
@router.delete("/temp_knowledge_base/{username}", response_model=dict)
async def clear_temp_knowledge_bases(
    username: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, username)
    knowledge_bases = await repo_manager.knowledge_base.get_all_knowledge_bases_by_user(
        username
    )

    if not knowledge_bases:
        return {
            "status": "success",
            "message": "用户知识库数量为0，无需清除",
        }
    failed_count = 0
    success_count = 0

    conversations = await repo_manager.conversation.get_conversations_by_user(username)
    if not conversations:
        chat_chatflow_id = []
    else:
        chat_chatflow_id = [
            conversation["conversation_id"] for conversation in conversations
        ]

    chatflows = await repo_manager.chatflow.get_chatflows_by_user(username)
    if not chatflows:
        pass
    else:
        chat_chatflow_id.extend([chatflow["chatflow_id"] for chatflow in chatflows])

    for knowledge_base in knowledge_bases:
        if knowledge_base["knowledge_base_id"].startswith("temp_"):
            temp_knowledge_base_id = knowledge_base["knowledge_base_id"]
            if (
                "_".join(temp_knowledge_base_id[5:].split("_")[0:2])
                not in chat_chatflow_id
            ):
                result = await repo_manager.knowledge_base.delete_knowledge_base(
                    temp_knowledge_base_id
                )
                milvus_client.delete_collection(
                    "colqwen" + temp_knowledge_base_id.replace("-", "_")
                )
                if result["status"] == "failed":
                    failed_count += 1
                else:
                    success_count += 1

    return {
        "status": "success",
        "message": f"成功删除 {success_count} 个知识库， 删除失败 {failed_count} 个",
    }


@router.post("/knowledge_bases/{knowledge_base_id}/files", response_model=PageResponse)
async def get_knowledge_base_files(
    knowledge_base_id: str,
    get_files: GetUserFiles,
    current_user: User = Depends(get_current_user),
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """
    获取指定知识库的文件列表（分页+搜索）
    """
    await verify_username_match(current_user, knowledge_base_id.split("_")[0])
    skip = (get_files.page - 1) * get_files.page_size
    result = await repo_manager.knowledge_base.get_kb_files_with_pagination(
        knowledge_base_id=knowledge_base_id,
        keyword=get_files.keyword,
        skip=skip,
        limit=get_files.page_size,
    )
    return format_page_response(result, get_files.page, get_files.page_size)


@router.post("/users/{username}/files", response_model=PageResponse)
async def get_user_all_files(
    username: str,
    get_files: GetUserFiles,
    current_user: User = Depends(get_current_user),
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """
    获取用户所有知识库文件（分页+搜索）
    """
    await verify_username_match(current_user, username)
    skip = (get_files.page - 1) * get_files.page_size
    result = await repo_manager.knowledge_base.get_user_files_with_pagination(
        username=username,
        keyword=get_files.keyword,
        skip=skip,
        limit=get_files.page_size,
    )
    return format_page_response(result, get_files.page, get_files.page_size)


@router.post("/files/download")
async def download_file(
    username: str,
    minio_filename: str,
    current_user: User = Depends(get_current_user),
):
    """
    通过MinIO下载文件（生成预签名URL）
    """

    try:
        await verify_username_match(current_user, username)
        if await async_minio_manager.validate_file_existence(minio_filename):
            url = await async_minio_manager.create_presigned_url(minio_filename)
            return RedirectResponse(url=url)
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")


import hashlib


# 上传文件
@router.post("/upload/{knowledge_db_id}", response_model=dict)
async def upload_multiple_files(
    files: List[UploadFile],
    knowledge_db_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
    current_user: User = Depends(get_current_user),
):
    # 验证当前用户是否与要删除的用户名匹配
    username = knowledge_db_id.split("_")[0]
    await verify_username_match(current_user, username)
    return_files = []
    # 生成任务ID
    task_id = username + "_" + str(uuid.uuid4())
    total_files = len(files)
    redis_connection = await redis.get_task_connection()

    # 保存文件元数据并准备Kafka消息
    file_meta_list = []
    skipped_count = 0

    for file in files:
        # 读取文件内容以计算哈希 (用于去重)
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        await file.seek(0)  # 重置指针以便后续保存

        # 检查是否已存在相同内容的文件
        existing_file = await repo_manager.file.get_file_by_hash(
            file_hash, username, knowledge_db_id
        )
        if existing_file:
            logger.info(
                f"File {file.filename} already exists in knowledge base {knowledge_db_id} (hash match). Skipping."
            )
            return_files.append(
                {
                    "id": existing_file["file_id"],
                    "minio_filename": existing_file["minio_filename"],
                    "filename": existing_file["filename"],
                    "url": existing_file["minio_url"],
                    "status": "skipped",
                    "message": "Duplicate content detected",
                }
            )
            skipped_count += 1
            continue

        # 保存文件到MinIO
        minio_filename, minio_url = await save_file_to_minio(username, file)

        # 生成文件ID并保存元数据
        file_id = f"{username}_{uuid.uuid4()}"
        file_meta_list.append(
            {
                "file_id": file_id,
                "minio_filename": minio_filename,
                "original_filename": file.filename,
                "minio_url": minio_url,
                "file_hash": file_hash,
            }
        )
        return_files.append(
            {
                "id": file_id,
                "minio_filename": minio_filename,
                "filename": file.filename,
                "url": minio_url,
            }
        )

    # 如果所有文件都被跳过
    if not file_meta_list:
        return {
            "task_id": "none",
            "knowledge_db_id": knowledge_db_id,
            "files": return_files,
            "message": f"All {total_files} files were already indexed.",
        }

    # 初始化任务状态
    await redis_connection.hset(
        f"task:{task_id}",
        mapping={
            "status": "processing",
            "total": len(file_meta_list),
            "processed": 0,
            "message": f"Processing {len(file_meta_list)} new files...",
        },
    )
    await redis_connection.expire(f"task:{task_id}", 3600)  # 1小时过期

    # 发送Kafka消息（每个文件一个消息）
    for meta in file_meta_list:
        logger.info(
            f"send {task_id} to kafka, file name {meta['original_filename']}, knowledge id {knowledge_db_id}."
        )
        await kafka_producer_manager.send_embedding_task(
            task_id=task_id,
            username=username,
            knowledge_db_id=knowledge_db_id,
            file_meta=meta,
            priority=1,
        )

    return {
        "task_id": task_id,
        "knowledge_db_id": knowledge_db_id,
        "files": return_files,
    }

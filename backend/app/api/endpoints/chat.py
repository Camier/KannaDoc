from typing import List
import uuid
import asyncio
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.db.redis import redis
from app.models.conversation import (
    ConversationCreate,
    ConversationOutput,
    ConversationRenameInput,
    ConversationSummary,
    ConversationUpdateModelConfig,
)
from app.schemas.chat_responses import (
    ConversationCreateResponse,
    ConversationRenameResponse,
    ConversationUploadResponse,
    StatusResponse,
)
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.rag.convert_file import save_file_to_minio
from app.utils.kafka_producer import kafka_producer_manager
from app.core.logging import logger
from app.db.vector_db import vector_db_client
from app.core.config import settings
from app.utils.ids import to_milvus_collection_name

router = APIRouter()

# Hardcoded username for single-user mode
USERNAME = settings.default_username


# 创建新会话
@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    conversation: ConversationCreate,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    await repo_manager.conversation.create_conversation(
        conversation_id=conversation.conversation_id,
        username=USERNAME,
        conversation_name=conversation.conversation_name,
        model_config=conversation.chat_model_config,
    )
    return ConversationCreateResponse(
        status="success", conversation_id=conversation.conversation_id
    )


# 修改会话名称
@router.post("/conversations/rename", response_model=ConversationRenameResponse)
async def re_name(
    renameInput: ConversationRenameInput,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.conversation.update_conversation_name(
        renameInput.conversation_id, renameInput.conversation_new_name
    )
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationRenameResponse(
        status=result["status"], message=result.get("message") or ""
    )


# 修改会话数据库使用
@router.post("/conversations/config", response_model=StatusResponse)
async def select_bases(
    basesInput: ConversationUpdateModelConfig,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.conversation.update_conversation_model_config(
        basesInput.conversation_id, basesInput.chat_model_config
    )
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail="Conversation not found")
    return StatusResponse(status=result["status"], message=result.get("message") or "")


# 获取指定 conversation_id 的完整会话记录
@router.get("/conversations/{conversation_id}", response_model=ConversationOutput)
async def get_conversation(
    conversation_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    conversation = await repo_manager.conversation.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fix N+1: Collect all unique temp_db IDs and fetch in single query
    temp_db_ids = list(
        {turn["temp_db"] for turn in conversation["turns"] if turn.get("temp_db")}
    )
    kb_files_map = {}

    if temp_db_ids:
        # Single query to fetch all knowledge bases
        # Using db directly here as Repository doesn't expose raw collection access
        # but this query logic could be moved to KnowledgeBaseRepository
        cursor = repo_manager.db.knowledge_bases.find(
            {"knowledge_base_id": {"$in": temp_db_ids}},
            {"knowledge_base_id": 1, "files": 1},
        )
        knowledge_bases = await cursor.to_list(length=100)

        # Build mapping: knowledge_base_id -> files
        for kb in knowledge_bases:
            kb_id = kb["knowledge_base_id"]
            kb_files_map[kb_id] = [
                {"url": file.get("minio_url", ""), "filename": file.get("filename", "")}
                for file in kb.get("files", [])
            ]

    # Use mapping to populate user_files in order
    user_files = [
        kb_files_map.get(turn["temp_db"], []) for turn in conversation["turns"]
    ]

    return {
        "conversation_id": conversation["conversation_id"],
        "conversation_name": conversation["conversation_name"],
        "chat_model_config": conversation["model_config"],
        "username": conversation["username"],
        "turns": [
            {
                "message_id": turn["message_id"],
                "parent_message_id": turn["parent_message_id"],
                "user_message": turn["user_message"],
                "user_file": user_file,
                "temp_db": turn["temp_db"],
                "ai_message": turn["ai_message"],
                "file_used": turn["file_used"],
                "status": turn["status"],
                "timestamp": turn["timestamp"].isoformat(),
                "total_token": turn["total_token"],
                "completion_tokens": turn["completion_tokens"],
                "prompt_tokens": turn["prompt_tokens"],
            }
            for turn, user_file in zip(conversation["turns"], user_files)
        ],
        "created_at": conversation["created_at"].isoformat(),
        "last_modify_at": conversation["last_modify_at"].isoformat(),
    }


# 查询指定用户的所有会话
@router.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations_by_user(
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    conversations = await repo_manager.conversation.get_conversations_by_user(USERNAME)
    if not conversations:
        return []
    return [
        {
            "conversation_id": conversation["conversation_id"],
            "conversation_name": conversation["conversation_name"],
            "chat_model_config": conversation["model_config"],
            "is_read": conversation["is_read"],
            "created_at": conversation["created_at"].isoformat(),
            "last_modify_at": conversation["last_modify_at"].isoformat(),
        }
        for conversation in conversations
    ]


# 删除指定会话
@router.delete("/conversations/{conversation_id}", response_model=StatusResponse)
async def delete_conversation(
    conversation_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    result = await repo_manager.conversation.delete_conversation(conversation_id)
    if result["status"] == "failed":
        raise HTTPException(status_code=404, detail=result["message"])
    return StatusResponse(status=result["status"], message=result.get("message"))


# 删除指定用户的所有会话
@router.delete("/conversations", response_model=StatusResponse)
async def delete_all_conversations_by_user(
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    # 执行批量删除
    result = await repo_manager.conversation.delete_conversations_by_user(USERNAME)

    if result.get("status") != "success":
        raise HTTPException(
            status_code=404, detail=result.get("message", "No conversations found")
        )

    return StatusResponse(
        status="success",
        message=f"Deleted {result.get('deleted_count', 0)} conversations",
    )


# 上传文件
@router.post("/upload/{conversation_id}", response_model=ConversationUploadResponse)
async def upload_multiple_files(
    files: List[UploadFile],
    conversation_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    return_files = []
    id = str(uuid.uuid4())
    knowledge_db_id = "temp_" + conversation_id + "_" + id
    await repo_manager.knowledge_base.create_knowledge_base(
        USERNAME,
        f"temp_base_{USERNAME}_{id}",
        knowledge_db_id,
        True,
    )
    collection_name = to_milvus_collection_name(knowledge_db_id)
    if not vector_db_client.check_collection(collection_name):
        vector_db_client.create_collection(collection_name)
    # 生成任务ID
    task_id = USERNAME + "_" + str(uuid.uuid4())
    total_files = len(files)
    redis_connection = await redis.get_task_connection()
    # 初始化任务状态
    await redis_connection.hset(
        f"task:{task_id}",
        mapping={
            "status": "processing",
            "total": total_files,
            "processed": 0,
            "message": "Initializing file processing...",
        },
    )
    await redis_connection.expire(f"task:{task_id}", 3600)  # 1小时过期

    # 保存文件元数据并准备Kafka消息
    file_meta_list = []

    # Batch MinIO uploads in parallel for -50% upload latency
    upload_tasks = [save_file_to_minio(USERNAME, file) for file in files]
    upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

    for file, upload_result in zip(files, upload_results):
        if isinstance(upload_result, BaseException):
            logger.error(f"Failed to upload {file.filename}: {upload_result}")
            raise upload_result

        if (
            not isinstance(upload_result, tuple)
            or len(upload_result) != 2
            or not all(isinstance(x, str) for x in upload_result)
        ):
            raise RuntimeError(f"Unexpected MinIO upload result: {upload_result!r}")

        minio_filename, minio_url = upload_result

        # 生成文件ID并保存元数据
        file_id = f"{USERNAME}_{uuid.uuid4()}"

        file_meta_list.append(
            {
                "file_id": file_id,
                "minio_filename": minio_filename,
                "original_filename": file.filename,
                "minio_url": minio_url,
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

    # 发送Kafka消息（每个文件一个消息）
    for meta in file_meta_list:
        logger.info(
            f"send {task_id} to kafka, file name {meta['original_filename']}, knowledge id {knowledge_db_id}."
        )
        await kafka_producer_manager.send_embedding_task(
            task_id=task_id,
            username=USERNAME,
            knowledge_db_id=knowledge_db_id,
            file_meta=meta,
            priority="1",
        )

    return ConversationUploadResponse(
        task_id=task_id,
        knowledge_db_id=knowledge_db_id,
        files=return_files,
    )

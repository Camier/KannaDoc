import asyncio
import copy
import os
import uuid
from app.db.vector_db import vector_db_client
from app.db.repositories.repository_manager import get_repository_manager
from app.rag.convert_file import convert_file_to_images, save_image_to_minio
from app.rag.get_embedding import get_embeddings_from_httpx
from app.db.miniodb import async_minio_manager
from app.core.logging import logger

try:
    EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "16"))
except ValueError:
    EMBED_BATCH_SIZE = 16
EMBED_BATCH_SIZE = max(1, EMBED_BATCH_SIZE)


def sort_and_filter(data, min_score=None, max_score=None):
    # 筛选
    if min_score is not None:
        data = [item for item in data if item["score"] >= min_score]
    if max_score is not None:
        data = [item for item in data if item["score"] <= max_score]
    # 排序
    sorted_data = sorted(data, key=lambda x: x["score"], reverse=True)
    return sorted_data


async def update_task_progress(redis, task_id, status, message):
    await redis.hset(f"task:{task_id}", mapping={"status": status, "message": message})


async def handle_processing_error(redis, task_id, error_msg):
    await redis.hset(
        f"task:{task_id}", mapping={"status": "failed", "message": error_msg}
    )


async def process_file(redis, task_id, username, knowledge_db_id, file_meta):
    file_record_created = False
    kb_file_added = False
    collection_name = None
    try:
        repo_manager = await get_repository_manager()
        knowledge_base = await repo_manager.knowledge_base.get_knowledge_base_by_id(
            knowledge_db_id, include_deleted=True
        )
        if not knowledge_base:
            raise ValueError(f"Knowledge base not found: {knowledge_db_id}")

        minio_filename = file_meta["minio_filename"]

        # Verify file exists in MinIO before attempting download
        if not await async_minio_manager.validate_file_existence(minio_filename):
            error_msg = f"File not found in MinIO: {minio_filename} (Original: {file_meta.get('original_filename')})"
            logger.error(f"task:{task_id}: {error_msg}")
            raise FileNotFoundError(error_msg)

        # 从MinIO获取文件内容
        file_content = await async_minio_manager.get_file_from_minio(minio_filename)

        # 解析为图片
        images_buffer = await convert_file_to_images(
            file_content, file_meta["original_filename"]
        )
        if not images_buffer:
            raise ValueError(
                f"No images extracted from file: {file_meta.get('original_filename')}"
            )

        # 保存图片并生成嵌入
        image_ids = [f"{username}_{uuid.uuid4()}" for _ in range(len(images_buffer))]

        # 插入Milvus
        collection_name = f"colqwen{knowledge_db_id.replace('-', '_')}"

        create_result = await repo_manager.file.create_files(
            file_id=file_meta["file_id"],
            username=username,
            filename=file_meta["original_filename"],
            minio_filename=file_meta["minio_filename"],
            minio_url=file_meta["minio_url"],
            knowledge_db_id=knowledge_db_id,
            file_hash=file_meta.get("file_hash"),
        )
        if create_result.get("status") != "success":
            raise RuntimeError(
                f"Failed to create file record: {create_result.get('message', 'unknown error')}"
            )
        file_record_created = True

        kb_result = await repo_manager.knowledge_base.knowledge_base_add_file(
            knowledge_base_id=knowledge_db_id,
            file_id=file_meta["file_id"],
            original_filename=file_meta["original_filename"],
            minio_filename=file_meta["minio_filename"],
            minio_url=file_meta["minio_url"],
        )
        if kb_result.get("status") != "success":
            raise RuntimeError(
                f"Failed to attach file to knowledge base: {kb_result.get('message', 'unknown error')}"
            )
        kb_file_added = True

        logger.info(
            f"task:{task_id}: save file of {file_meta['original_filename']} to mongodb"
        )

        # 生成嵌入向量 + 插入 Milvus + 保存图片（分批处理）
        for batch_start in range(0, len(images_buffer), EMBED_BATCH_SIZE):
            batch_end = min(batch_start + EMBED_BATCH_SIZE, len(images_buffer))
            batch_buffers = images_buffer[batch_start:batch_end]
            batch_image_ids = image_ids[batch_start:batch_end]

            batch_embeddings = await generate_embeddings(
                batch_buffers, file_meta["original_filename"], start_index=batch_start
            )
            if len(batch_embeddings) != len(batch_buffers):
                raise RuntimeError(
                    f"Embedding count mismatch: expected {len(batch_buffers)}, got {len(batch_embeddings)}"
                )

            await insert_to_milvus(
                collection_name,
                batch_embeddings,
                batch_image_ids,
                file_meta["file_id"],
                page_offset=batch_start,
            )

            for offset, (image_buffer, image_id) in enumerate(
                zip(batch_buffers, batch_image_ids), start=batch_start
            ):
                # 保存图片到MinIO
                minio_imagename, image_url = await save_image_to_minio(
                    username, file_meta["original_filename"], image_buffer
                )

                # 保存图片元数据
                await repo_manager.file.add_images(
                    file_id=file_meta["file_id"],
                    images_id=image_id,
                    minio_filename=minio_imagename,
                    minio_url=image_url,
                    page_number=offset + 1,
                )

            for idx in range(batch_start, batch_end):
                if images_buffer[idx] is not None:
                    images_buffer[idx].close()
                images_buffer[idx] = None

        logger.info(
            f"task:{task_id}: images of {file_meta['original_filename']} inserted to milvus {collection_name}!"
        )
        logger.info(
            f"task:{task_id}: save images of {file_meta['original_filename']} to minio and mongodb"
        )

        # 更新处理进度
        await redis.hincrby(f"task:{task_id}", "processed", 1)
        current = int(await redis.hget(f"task:{task_id}", "processed"))
        total = int(await redis.hget(f"task:{task_id}", "total"))
        logger.info(f"task:{task_id} files processed + 1!")

        if current == total:
            await redis.hset(f"task:{task_id}", "status", "completed")
            await redis.hset(
                f"task:{task_id}", "message", "All files processed successfully"
            )
            logger.info(f"task:{task_id} All files processed successfully")

    except Exception as e:
        error_msg = str(e).lower()
        # Check if error is recoverable (embedding OOM, memory issues)
        is_recoverable_error = any(
            keyword in error_msg
            for keyword in [
                "embedding",
                "memory",
                "oom",
                "cuda",
                "gpu",
                "out of memory",
            ]
        )

        # Only cleanup on non-recoverable errors
        if not is_recoverable_error:
            if collection_name and file_meta.get("file_id"):
                try:
                    vector_db_client.delete_files(
                        collection_name, [file_meta["file_id"]]
                    )
                except Exception as cleanup_error:
                    logger.warning(
                        f"task:{task_id}: failed to cleanup milvus vectors: {cleanup_error}"
                    )

            try:
                repo_manager = await get_repository_manager()
                if kb_file_added:
                    await repo_manager.knowledge_base.delete_file_from_knowledge_base(
                        knowledge_db_id, file_meta["file_id"]
                    )
                elif file_record_created:
                    await repo_manager.file.delete_files_bulk([file_meta["file_id"]])
            except Exception as cleanup_error:
                logger.warning(
                    f"task:{task_id}: failed to cleanup mongo/minio: {cleanup_error}"
                )
            logger.warning(
                f"task:{task_id}: Cleanup performed due to non-recoverable error: {error_msg}"
            )
        else:
            logger.warning(
                f"task:{task_id}: Skipping cleanup for recoverable error: {error_msg}"
            )

        await handle_processing_error(
            redis, task_id, f"File processing failed: {str(e)}"
        )
        raise


async def generate_embeddings(images_buffer, filename, start_index=0):
    # 将同步函数包装到线程池执行
    images_request = []
    for i, img in enumerate(images_buffer):
        if img is None:
            continue
        img.seek(0)
        images_request.append(
            ("images", (f"{filename}_{start_index + i}.png", img, "image/png"))
        )
    return await get_embeddings_from_httpx(images_request, endpoint="embed_image")


async def insert_to_milvus(
    collection_name, embeddings, image_ids, file_id, page_offset=0
):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: [
            vector_db_client.insert(
                {
                    "colqwen_vecs": emb,
                    "page_number": page_offset + i,
                    "image_id": image_ids[i],
                    "file_id": file_id,
                },
                collection_name,
            )
            for i, emb in enumerate(embeddings)
        ],
    )


async def replace_image_content(messages):
    # 创建深拷贝以保证原始数据不变
    new_messages = copy.deepcopy(messages)
    # 遍历每条消息
    for message in new_messages:
        if "content" not in message:
            continue

        if not isinstance(message["content"], list):
            continue

        new_content = []  # 创建新的内容列表
        # 遍历content中的每个内容项
        for item in message["content"]:
            if isinstance(item, dict) and item.get("type") == "image_url":
                image_base64 = (
                    await async_minio_manager.download_image_and_convert_to_base64(
                        item["image_url"]
                    )
                )
                if image_base64:
                    new_item = copy.deepcopy(item)
                    new_item["image_url"] = {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                    new_content.append(new_item)
            else:
                new_content.append(item)
        message["content"] = new_content

    return new_messages
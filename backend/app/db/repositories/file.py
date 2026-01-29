from typing import Dict, Any, List, Optional
from app.core.logging import logger
from app.utils.timezone import beijing_time_now
from pymongo import DeleteMany
from app.db.miniodb import async_minio_manager
from .base import BaseRepository


class FileRepository(BaseRepository):
    async def create_files(
        self,
        file_id: str,
        username: str,
        filename: str,
        minio_filename: str,
        minio_url: str,
        knowledge_db_id: str,
        file_hash: Optional[str] = None,
    ):
        """创建文件记录（带唯一索引保护）"""
        file = {
            "file_id": file_id,
            "filename": filename,
            "username": username,
            "minio_filename": minio_filename,
            "minio_url": minio_url,
            "knowledge_db_id": knowledge_db_id,
            "file_hash": file_hash,
            "images": [],
            "created_at": beijing_time_now(),
            "last_modify_at": beijing_time_now(),
            "is_delete": False,
        }

        try:
            await self.db.files.insert_one(file)
            return {"status": "success"}
        except Exception:
            # DuplicateKeyError is handled by caller or generic exception logging
            logger.warning(f"文件ID冲突: {file_id}")
            return {"status": "failed", "message": "文件ID已存在，请勿重复上传"}

    async def get_file_by_hash(
        self, file_hash: str, username: str, knowledge_db_id: str
    ) -> Optional[Dict[str, Any]]:
        """查找指定知识库中是否存在相同哈希的文件"""
        return await self.db.files.find_one(
            {
                "username": username,
                "knowledge_db_id": knowledge_db_id,
                "file_hash": file_hash,
                "is_delete": False,
            }
        )

    async def add_images(
        self,
        file_id: str,
        images_id: str,
        minio_filename: str,
        minio_url: str,
        page_number: str,
    ) -> Dict[str, Any]:
        """向指定的 file_id 中添加解析的图片"""
        images = {
            "images_id": images_id,
            "minio_filename": minio_filename,
            "minio_url": minio_url,
            "page_number": page_number,
        }
        result = await self.db.files.update_one(
            {"file_id": file_id, "is_delete": False},
            {
                "$push": {
                    "images": images,
                },
                "$set": {"last_modify_at": beijing_time_now()},
            },
        )
        return {"status": "success" if result.modified_count > 0 else "failed"}

    async def get_file_and_image_info(
        self, file_id: str, image_id: str
    ) -> Dict[str, Any]:
        """
        根据 file_id 和 image_id 获取：
        - knowledge_db_id
        - filename
        - 文件的 minio_filename 和 minio_url
        - 图片的 minio_filename 和 minio_url
        """
        # 查询文件文档，并匹配对应的图片
        file_doc = await self.db.files.find_one(
            {
                "file_id": file_id,
                "is_delete": False,
                "images.images_id": image_id,  # 确保存在该 image_id 的图片
            },
            projection={
                "knowledge_db_id": 1,
                "filename": 1,
                "minio_filename": 1,  # 文件的 minio_filename
                "minio_url": 1,  # 文件的 minio_url
                "images.$": 1,  # 使用 $ 操作符获取匹配的第一个图片元素
            },
        )

        if not file_doc:
            return {"status": "failed", "message": "file_id or image_id not found"}

        # 提取文件信息
        knowledge_db_id = file_doc.get("knowledge_db_id")
        file_name = file_doc.get("filename")
        file_minio_filename = file_doc.get("minio_filename")
        file_minio_url = file_doc.get("minio_url")  # 新增文件的 minio_url

        # 提取图片信息
        images = file_doc.get("images", [])
        if not images:
            return {"status": "failed", "message": "image not found"}

        image_info = images[0]  # 因为使用了 $ 操作符，数组只有一个匹配元素
        image_minio_filename = image_info.get("minio_filename")
        image_minio_url = image_info.get("minio_url")  # 新增图片的 minio_url

        # 返回所有字段
        return {
            "status": "success",
            "knowledge_db_id": knowledge_db_id,
            "file_name": file_name,
            "file_minio_filename": file_minio_filename,
            "file_minio_url": file_minio_url,  # 文件的 URL
            "image_minio_filename": image_minio_filename,
            "image_minio_url": image_minio_url,  # 图片的 URL
        }

    async def delete_files_bulk(self, file_ids: List[str]) -> dict:
        """批量删除文件记录及关联的 MinIO 文件"""
        # 去重处理
        unique_ids = list(set(file_ids))
        if not unique_ids:
            return {"status": "success", "message": "空文件列表，无需处理"}

        # 查询所有相关文档
        cursor = self.db.files.find({"file_id": {"$in": unique_ids}})
        files = await cursor.to_list(length=100)

        # 收集所有需要删除的 MinIO 文件
        minio_files = []
        found_ids = set()

        for file in files:
            found_ids.add(file["file_id"])
            # 主文件
            if main_file := file.get("minio_filename"):
                minio_files.append(main_file)
            # 图片文件
            minio_files.extend(
                img["minio_filename"]
                for img in file.get("images", [])
                if img.get("minio_filename")
            )

        # 执行 MinIO 批量删除
        error_messages = []

        try:
            if minio_files:
                await async_minio_manager.bulk_delete(list(set(minio_files)))  # 去重
                logger.info(f"批量删除 MinIO 文件成功")
        except Exception as e:
            error_messages.append(f"MinIO 批量删除异常: {str(e)}")
            logger.error(f"批量删除 MinIO 文件异常 | {str(e)}")

        # 执行 MongoDB 批量删除
        db_success = 0
        try:
            result = await self.db.files.bulk_write(
                [DeleteMany({"file_id": {"$in": unique_ids}})]
            )
            db_success = result.deleted_count
            logger.info(f"批量删除 mongo 数据库记录成功")
        except Exception as e:
            error_messages.append(f"数据库删除失败: {str(e)}")
            logger.error(f"批量删除数据库记录失败 | {str(e)}")

        # 处理未找到的 file_ids
        not_found_ids = list(set(unique_ids) - found_ids)

        # 构建响应
        response = {
            "status": "success",
            "message": f"成功删除 {db_success} 个文件记录",
            "detail": {
                "total_requested": len(unique_ids),
                "db_deleted": db_success,
                "minio_deleted": len(minio_files),
                "not_found_ids": not_found_ids,
                "errors": error_messages,
            },
        }

        if not_found_ids:
            response["message"] += f"，其中 {len(not_found_ids)} 个 ID 未找到"

        if error_messages:
            response["status"] = "partial_success"
            response["message"] += "（部分操作失败）"

        if db_success == 0 and len(not_found_ids) == len(unique_ids):
            response["status"] = "failed"
            response["message"] = "所有请求的文件 ID 均未找到"

        return response

    async def get_files_by_ids(self, file_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Batch fetch files by their IDs.

        Args:
            file_ids: List of file IDs to fetch

        Returns:
            List of file documents
        """
        if not file_ids:
            return []

        cursor = self.db.files.find({"file_id": {"$in": file_ids}, "is_delete": False})
        return await cursor.to_list(length=len(file_ids))

    async def get_files_and_images_batch(
        self, file_image_pairs: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Batch fetch file and image info for multiple (file_id, image_id) pairs.

        This eliminates N+1 query pattern by fetching all files in a single query
        and then matching images in memory.

        Args:
            file_image_pairs: List of (file_id, image_id) tuples

        Returns:
            List of info dicts in the same order as input pairs.
            Each dict has same structure as get_file_and_image_info().
        """
        if not file_image_pairs:
            return []

        # Extract unique file_ids for batch query
        unique_file_ids = list(set(pair[0] for pair in file_image_pairs))

        # Single query to fetch all files with their images
        cursor = self.db.files.find(
            {"file_id": {"$in": unique_file_ids}, "is_delete": False},
            projection={
                "file_id": 1,
                "knowledge_db_id": 1,
                "filename": 1,
                "minio_filename": 1,
                "minio_url": 1,
                "images": 1,
            },
        )
        files = await cursor.to_list(length=len(unique_file_ids))

        # Build lookup: file_id -> file_doc
        file_map = {f["file_id"]: f for f in files}

        # Build lookup: (file_id, image_id) -> image_info
        image_map = {}
        for file_doc in files:
            file_id = file_doc["file_id"]
            for img in file_doc.get("images", []):
                image_id = img.get("images_id")
                if image_id:
                    image_map[(file_id, image_id)] = {
                        "file_doc": file_doc,
                        "image_info": img,
                    }

        # Build results in order of input pairs
        results = []
        for file_id, image_id in file_image_pairs:
            key = (file_id, image_id)
            if key not in image_map:
                results.append(
                    {
                        "status": "failed",
                        "message": "file_id or image_id not found",
                    }
                )
                continue

            data = image_map[key]
            file_doc = data["file_doc"]
            image_info = data["image_info"]

            results.append(
                {
                    "status": "success",
                    "knowledge_db_id": file_doc.get("knowledge_db_id"),
                    "file_name": file_doc.get("filename"),
                    "file_minio_filename": file_doc.get("minio_filename"),
                    "file_minio_url": file_doc.get("minio_url"),
                    "image_minio_filename": image_info.get("minio_filename"),
                    "image_minio_url": image_info.get("minio_url"),
                }
            )

        return results

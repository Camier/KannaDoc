"""
File Repository

Handles all operations related to file records and storage.
Lines 957-1302 from original mongo.py
"""

from typing import Dict, Any, List
from pymongo.errors import DuplicateKeyError
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository
from app.db.miniodb import async_minio_manager


class FileRepository(BaseRepository):
    """Repository for file operations."""

    async def create_files(
        self,
        file_id: str,
        username: str,
        filename: str,
        minio_filename: str,
        minio_url: str,
        knowledge_db_id: str,
    ):
        """Create a file record (with unique index protection)."""
        file = {
            "file_id": file_id,
            "filename": filename,
            "username": username,
            "minio_filename": minio_filename,
            "minio_url": minio_url,
            "knowledge_db_id": knowledge_db_id,
            "images": [],
            "created_at": self._get_timestamp(),
            "last_modify_at": self._get_timestamp(),
            "is_delete": False,
        }

        try:
            await self.db.files.insert_one(file)
            return {"status": "success"}
        except DuplicateKeyError:
            logger.warning(f"文件ID冲突: {file_id}")
            return {"status": "failed", "message": "文件ID已存在，请勿重复上传"}

    async def add_images(
        self,
        file_id: str,
        images_id: str,
        minio_filename: str,
        minio_url: str,
        page_number: str,
    ) -> Dict[str, Any]:
        """Add parsed images to a file record."""
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
                "$set": {"last_modify_at": self._get_timestamp()},
            },
        )
        return {"status": "success" if result.modified_count > 0 else "failed"}

    async def get_file_and_image_info(
        self, file_id: str, image_id: str
    ) -> Dict[str, Any]:
        """
        Get file and image information by file_id and image_id.
        Returns:
        - knowledge_db_id
        - filename
        - File's minio_filename and minio_url
        - Image's minio_filename and minio_url
        """
        # Query file document and match corresponding image
        file_doc = await self.db.files.find_one(
            {
                "file_id": file_id,
                "is_delete": False,
                "images.images_id": image_id,
            },
            projection={
                "knowledge_db_id": 1,
                "filename": 1,
                "minio_filename": 1,
                "minio_url": 1,
                "images.$": 1,
            },
        )

        if not file_doc:
            return {"status": "failed", "message": "file_id or image_id not found"}

        # Extract file information
        knowledge_db_id = file_doc.get("knowledge_db_id")
        file_name = file_doc.get("filename")
        file_minio_filename = file_doc.get("minio_filename")
        file_minio_url = file_doc.get("minio_url")

        # Extract image information
        images = file_doc.get("images", [])
        if not images:
            return {"status": "failed", "message": "image not found"}

        image_info = images[0]
        image_minio_filename = image_info.get("minio_filename")
        image_minio_url = image_info.get("minio_url")

        # Return all fields
        return {
            "status": "success",
            "knowledge_db_id": knowledge_db_id,
            "file_name": file_name,
            "file_minio_filename": file_minio_filename,
            "file_minio_url": file_minio_url,
            "image_minio_filename": image_minio_filename,
            "image_minio_url": image_minio_url,
        }

    async def delete_files_base(self, file_id: str) -> dict:
        """Delete a file record by file_id."""
        result = await self.db.files.delete_one({"file_id": file_id})

        if result.deleted_count == 1:
            return {
                "status": "success",
                "message": f"Knowledge Base {file_id} deleted",
            }
        else:
            return {"status": "failed", "message": "Knowledge Base not found"}

    async def delete_files_bulk(self, file_ids: List[str]) -> dict:
        """Batch delete file records and associated MinIO files."""
        from pymongo import DeleteMany

        # Deduplicate
        unique_ids = list(set(file_ids))
        if not unique_ids:
            return {"status": "success", "message": "空文件列表，无需处理"}

        # Query all related documents
        cursor = self.db.files.find({"file_id": {"$in": unique_ids}})
        files = await cursor.to_list(length=self._paginate(len(unique_ids), max_limit=10000))

        # Collect all MinIO files to delete
        minio_files = []
        found_ids = set()

        for file in files:
            found_ids.add(file["file_id"])
            # Main file
            if main_file := file.get("minio_filename"):
                minio_files.append(main_file)
            # Image files
            minio_files.extend(
                img["minio_filename"]
                for img in file.get("images", [])
                if img.get("minio_filename")
            )

        # Execute MinIO batch delete
        error_messages = []

        try:
            if minio_files:
                await async_minio_manager.bulk_delete(list(set(minio_files)))
                logger.info(f"批量删除 MinIO 文件成功")
        except Exception as e:
            error_messages.append(f"MinIO 批量删除异常: {str(e)}")
            logger.error(f"批量删除 MinIO 文件异常 | {str(e)}")

        # Execute MongoDB batch delete
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

        # Process unfound file_ids
        not_found_ids = list(set(unique_ids) - found_ids)

        # Build response
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

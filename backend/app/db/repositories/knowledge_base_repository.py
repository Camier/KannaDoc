"""
Knowledge Base Repository

Handles all operations related to knowledge bases.
Lines 749-956 from original mongo.py
"""

from typing import Dict, Any, List, Optional
from pymongo.errors import DuplicateKeyError
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository
from app.db.ultils import parse_aggregate_result
from app.db.cache import cache_service


class KnowledgeBaseRepository(BaseRepository):
    """Repository for knowledge base operations."""

    async def create_knowledge_base(
        self,
        username: str,
        knowledge_base_name: str,
        knowledge_base_id: str,
        is_delete: bool,
    ):
        """
        Create a new knowledge base.
        If knowledge_base_id doesn't exist, create it; otherwise skip.
        """
        # Check if knowledge_base_id already exists
        existing = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_base_id}
        )
        if existing is not None:
            # If exists, return without inserting
            return

        # Create knowledge base (uses unique index to prevent duplicates)
        knowledge_base = {
            "knowledge_base_id": knowledge_base_id,
            "knowledge_base_name": knowledge_base_name,
            "username": username,
            "files": [],
            "used_chat": [],
            "created_at": self._get_timestamp(),
            "last_modify_at": self._get_timestamp(),
            "is_delete": is_delete,
        }

        try:
            await self.db.knowledge_bases.insert_one(knowledge_base)
            return {"status": "success", "id": knowledge_base_id}
        except DuplicateKeyError:
            logger.warning(f"知识库ID冲突: {knowledge_base_id}")
            return {"status": "failed", "message": "知识库ID已存在，请勿重复创建"}
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            return {"status": "error", "message": f"数据库错误: {str(e)}"}

    async def get_knowledge_bases_by_user(self, username: str) -> List[Dict[str, Any]]:
        """Get all knowledge bases for a user, sorted by time descending."""
        cursor = self.db.knowledge_bases.find(
            {"username": username, "is_delete": False}
        ).sort("last_modify_at", -1)
        return await cursor.to_list(length=self._paginate(None, max_limit=500))

    async def get_all_knowledge_bases_by_user(
        self, username: str
    ) -> List[Dict[str, Any]]:
        """Get all knowledge bases for a user (including deleted)."""
        cursor = self.db.knowledge_bases.find({"username": username})
        return await cursor.to_list(length=self._paginate(None, max_limit=500))

    async def get_knowledge_base_by_id(
        self, knowledge_base_id: str, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a knowledge base by ID with caching."""
        # Skip cache for deleted items or when explicitly including deleted
        if not include_deleted:
            cached = await cache_service.get_kb_metadata(knowledge_base_id)
            if cached:
                logger.debug(f"Cache hit: kb_metadata for {knowledge_base_id}")
                return cached

        query = {"knowledge_base_id": knowledge_base_id}
        if not include_deleted:
            query["is_delete"] = False
        kb = await self.db.knowledge_bases.find_one(query)

        if kb and not include_deleted:
            kb_dict = {k: v for k, v in kb.items() if k != '_id'}
            await cache_service.set_kb_metadata(knowledge_base_id, kb_dict)

        return kb

    async def delete_knowledge_base(
        self, knowledge_base_id: str, file_repo=None
    ) -> dict:
        """
        Delete a knowledge base and all associated files.

        Args:
            knowledge_base_id: Knowledge base ID to delete
            file_repo: Optional FileRepository for deleting associated files
        """
        # Query knowledge base document
        knowledge_base = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_base_id}
        )
        if not knowledge_base:
            return {"status": "failed", "message": "知识库不存在"}

        # Collect all associated file IDs (automatically deduplicated)
        file_ids = list({file["file_id"] for file in knowledge_base.get("files", [])})

        # Batch delete files (includes MongoDB records and MinIO files)
        if file_repo and file_ids:
            file_deletion_result = await file_repo.delete_files_bulk(file_ids)
        else:
            file_deletion_result = {
                "status": "success",
                "message": "无关联文件需要删除",
                "detail": {},
            }

        # Delete knowledge base document
        try:
            delete_result = await self.db.knowledge_bases.delete_one(
                {"knowledge_base_id": knowledge_base_id}
            )
        except Exception as e:
            logger.error(f"删除知识库失败 | ID: {knowledge_base_id} | 错误: {str(e)}")
            return {
                "status": "failed",
                "message": f"数据库删除失败: {str(e)}",
                "file_deletion": file_deletion_result,
            }

        # Process results
        response = {
            "status": "success",
            "message": "知识库及关联文件已删除",
            "detail": {
                "knowledge_base_deleted": delete_result.deleted_count,
                "file_deletion": file_deletion_result,
            },
        }

        # Invalidate cache
        await cache_service.invalidate_kb_metadata(knowledge_base_id)

        # Handle partial success
        if (
            file_deletion_result.get("status") != "success"
            or delete_result.deleted_count != 1
        ):
            response["status"] = "partial_success"
            error_messages = []

            if delete_result.deleted_count != 1:
                error_messages.append("知识库删除失败")

            if file_deletion_result.get("status") != "success":
                error_messages.append("部分文件删除失败")

            response["message"] = ",".join(error_messages)

        return response

    async def update_knowledge_base_name(
        self, knowledge_base_id: str, new_name: str
    ) -> dict:
        """Update knowledge base name."""
        result = await self.db.knowledge_bases.update_one(
            {"knowledge_base_id": knowledge_base_id, "is_delete": False},
            {
                "$set": {
                    "knowledge_base_name": new_name,
                    "last_modify_at": self._get_timestamp(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Knowledge base not found or update failed",
            }
        await cache_service.invalidate_kb_metadata(knowledge_base_id)
        return {"status": "success"}

    async def knowledge_base_add_file(
        self,
        knowledge_base_id: str,
        file_id: str,
        original_filename: str,
        minio_filename: str,
        minio_url: str,
    ) -> Dict[str, Any]:
        """Add a file to a knowledge base."""
        file = {
            "file_id": file_id,
            "filename": original_filename,
            "minio_filename": minio_filename,
            "minio_url": minio_url,
            "created_at": self._get_timestamp(),
        }
        result = await self.db.knowledge_bases.update_one(
            {
                "knowledge_base_id": knowledge_base_id,
                "files.file_id": {"$ne": file_id},
            },
            {
                "$push": {
                    "files": file,
                },
                "$set": {"last_modify_at": self._get_timestamp()},
            },
        )
        if result.modified_count > 0:
            await cache_service.invalidate_kb_metadata(knowledge_base_id)
            return {"status": "success"}

        existing = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_base_id}, projection={"_id": 1}
        )
        if not existing:
            return {"status": "failed", "message": "knowledge_base_not_found"}
        return {"status": "failed", "message": "file_already_exists"}

    async def get_files_by_knowledge_base_id(
        self, knowledge_base_id: str
    ) -> List[Dict[str, str]]:
        """Get all files for a knowledge base (returns only url and filename)."""
        try:
            # Query non-deleted knowledge base
            kb = await self.db.knowledge_bases.find_one(
                {
                    "knowledge_base_id": knowledge_base_id,
                },
                {"files": 1},
            )

            if not kb or "files" not in kb:
                return []

            return [
                {"url": file.get("minio_url", ""), "filename": file.get("filename", "")}
                for file in kb["files"]
            ]

        except Exception as e:
            logger.error(
                f"获取知识库文件失败 | ID: {knowledge_base_id} | 错误: {str(e)}"
            )
            return []

    async def get_kb_files_with_pagination(
        self,
        knowledge_base_id: str,
        keyword: str = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get knowledge base files with pagination and search."""
        pipeline = [
            {"$match": {"knowledge_base_id": knowledge_base_id}},
            {"$unwind": "$files"},
        ]

        # Add filename filter after unwinding array
        if keyword:
            pipeline.append(
                {"$match": {"files.filename": {"$regex": keyword, "$options": "i"}}}
            )

        pipeline.extend(
            [
                {
                    "$replaceRoot": {
                        "newRoot": {
                            "file_id": "$files.file_id",
                            "filename": "$files.filename",
                            "url": "$files.minio_url",
                            "kb_id": "$knowledge_base_id",
                            "upload_time": "$files.created_at",
                            "kb_name": "$knowledge_base_name",
                        }
                    }
                },
                {
                    "$facet": {
                        "metadata": [{"$count": "total"}],
                        "data": [{"$skip": skip}, {"$limit": limit}],
                    }
                },
            ]
        )

        cursor = self.db.knowledge_bases.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return parse_aggregate_result(result)

    async def get_user_files_with_pagination(
        self, username: str, keyword: str = None, skip: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        """Get all user files with pagination and search."""
        pipeline = [
            {"$match": {"username": username, "is_delete": False}},
            {"$unwind": "$files"},
            # Keyword search (correct field path)
            (
                {"$match": {"files.filename": {"$regex": keyword, "$options": "i"}}}
                if keyword
                else {"$match": {}}
            ),
            # Remap fields (key step)
            {
                "$replaceRoot": {
                    "newRoot": {
                        # Promote files object fields to top level
                        "file_id": "$files.file_id",
                        "filename": "$files.filename",
                        "url": "$files.minio_url",
                        "kb_name": "$knowledge_base_name",
                        "kb_id": "$knowledge_base_id",
                        "upload_time": "$files.created_at",
                    }
                }
            },
            # Pagination and statistics
            {
                "$facet": {
                    "metadata": [{"$count": "total"}],
                    "data": [
                        {"$skip": skip},
                        {"$limit": limit},
                    ],
                }
            },
        ]

        cursor = self.db.knowledge_bases.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return parse_aggregate_result(result)

    async def delete_file_from_knowledge_base(
        self, knowledge_id: str, file_id: str, file_repo=None
    ) -> dict:
        """
        Delete a file from a knowledge base, including file record and storage.

        Args:
            knowledge_id: Knowledge base ID
            file_id: File ID to delete
            file_repo: Optional FileRepository for deleting file records
        """
        # Check if file exists in knowledge base
        kb = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_id, "files.file_id": file_id},
            projection={"files.$": 1},
        )
        if not kb:
            logger.warning(
                f"文件 {file_id} 不存在于知识库 {knowledge_id} 或知识库不存在"
            )
            return {"status": "failed", "message": "文件不存在于该知识库或知识库不存在"}

        # Remove file from knowledge base's files array
        update_result = await self.db.knowledge_bases.update_one(
            {"knowledge_base_id": knowledge_id},
            {"$pull": {"files": {"file_id": file_id}}},
        )
        if update_result.modified_count == 0:
            logger.error(f"从知识库 {knowledge_id} 中移除文件 {file_id} 失败")
            return {"status": "failed", "message": "文件移除失败"}

        # Invalidate cache
        await cache_service.invalidate_kb_metadata(knowledge_id)

        # Check if file record belongs to this knowledge base
        file_doc = await self.db.files.find_one(
            {"file_id": file_id, "knowledge_db_id": knowledge_id}
        )
        if not file_doc:
            logger.warning(f"文件记录 {file_id} 不存在或不属于知识库 {knowledge_id}")
            return {"status": "failed", "message": "文件记录不存在或不属于该知识库"}

        # Delete file record and MinIO files
        if file_repo:
            deletion_result = await file_repo.delete_files_bulk([file_id])

            if deletion_result["status"] != "success":
                logger.error(f"删除文件 {file_id} 失败: {deletion_result}")
                return {
                    "status": "partial_success",
                    "message": "文件已从知识库中移除，但删除文件记录或存储文件失败",
                    "detail": deletion_result,
                }

        logger.info(f"成功从知识库 {knowledge_id} 删除文件 {file_id}")
        return {"status": "success", "message": "文件删除成功"}

    async def bulk_delete_files_from_knowledge(
        self, delete_list: List[Dict[str, str]], file_repo=None
    ) -> dict:
        """
        Batch delete files from knowledge bases (supports cross-knowledge-base).
        Parameter format: [{"knowledge_id": "kb1", "file_id": "f1"}, ...]
        Returns detailed operation result report.
        """
        from collections import defaultdict
        from pymongo import UpdateMany, BulkWriteError

        # Deduplicate and group by knowledge_id
        unique_pairs = {(item["knowledge_id"], item["file_id"]) for item in delete_list}
        grouped = defaultdict(list)
        for kb_id, file_id in unique_pairs:
            grouped[kb_id].append(file_id)

        # Phase 1: Batch remove file references from knowledge bases
        bulk_operations = []
        for kb_id, file_ids in grouped.items():
            bulk_operations.append(
                UpdateMany(
                    {"knowledge_base_id": kb_id},
                    {"$pull": {"files": {"file_id": {"$in": file_ids}}}},
                    array_filters=[],
                )
            )

        # Execute batch update
        bulk_result = None
        if bulk_operations:
            try:
                bulk_result = await self.db.knowledge_bases.bulk_write(bulk_operations)
                logger.info(f"批量更新影响知识库数量: {bulk_result.modified_count}")
            except BulkWriteError as e:
                logger.error(f"批量更新异常: {str(e)}")
                return {"status": "error", "message": "批量操作异常"}

        # Phase 2: Verify file ownership and collect IDs to delete
        valid_files = []
        cursor = self.db.files.find(
            {
                "$or": [
                    {"knowledge_db_id": kb_id, "file_id": {"$in": file_ids}}
                    for kb_id, file_ids in grouped.items()
                ]
            },
            projection={"file_id": 1, "knowledge_db_id": 1},
        )

        async for doc in cursor:
            # Verify grouping match
            if doc["file_id"] in grouped.get(doc["knowledge_db_id"], []):
                valid_files.append(doc["file_id"])

        # Phase 3: Execute file deletion
        if file_repo and valid_files:
            deletion_result = await file_repo.delete_files_bulk(valid_files)
        else:
            deletion_result = {"status": "success", "detail": {}}

        # Phase 4: Build detailed response
        return {
            "status": (
                "success"
                if deletion_result["status"] == "success"
                else "partial_success"
            ),
            "detail": {
                "total_requested": len(unique_pairs),
                "valid_files_found": len(valid_files),
                "file_deletion": deletion_result,
                "knowledge_updates": {
                    "attempted": len(grouped),
                    "modified_count": (
                        bulk_result.modified_count if bulk_result else 0
                    ),
                },
            },
        }

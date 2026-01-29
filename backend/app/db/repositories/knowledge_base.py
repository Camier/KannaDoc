from typing import Dict, Any, List, Optional
from collections import defaultdict
from app.core.logging import logger
from app.utils.timezone import beijing_time_now
from app.core.config import settings
from app.db.ultils import parse_aggregate_result
from pymongo import UpdateMany
from pymongo.errors import BulkWriteError, DuplicateKeyError
from .base import BaseRepository
from .file import FileRepository

class KnowledgeBaseRepository(BaseRepository):
    
    def __init__(self, db, file_repo: Optional[FileRepository] = None):
        super().__init__(db)
        self.file_repo = file_repo or FileRepository(db)

    async def create_knowledge_base(
        self,
        username: str,
        knowledge_base_name: str,
        knowledge_base_id: str,
        is_delete: bool,
    ):
        """创建一个新的知识库（如果 knowledge_base_id 不存在则创建，存在则跳过）"""
        # 检查是否已存在相同的 knowledge_base_id
        existing = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_base_id}
        )
        if existing is not None:
            # 如果存在，直接返回，不执行插入
            return

        """创建知识库（使用唯一索引防止重复）"""
        knowledge_base = {
            "knowledge_base_id": knowledge_base_id,
            "knowledge_base_name": knowledge_base_name,
            "username": username,
            "files": [],
            "used_chat": [],
            "created_at": beijing_time_now(),
            "last_modify_at": beijing_time_now(),
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
        """按时间降序获取指定用户的所有会话"""
        query = (
            {"is_delete": False}
            if settings.single_tenant_mode
            else {"username": username, "is_delete": False}
        )
        cursor = self.db.knowledge_bases.find(query).sort(
            "last_modify_at", -1
        )  # -1 表示降序排列
        return await cursor.to_list(length=100)  # 返回所有匹配的记录

    async def get_all_knowledge_bases_by_user(
        self, username: str
    ) -> List[Dict[str, Any]]:
        """按时间降序获取指定用户的所有会话"""
        cursor = self.db.knowledge_bases.find(
            {} if settings.single_tenant_mode else {"username": username}
        )
        return await cursor.to_list(length=100)  # 返回所有匹配的记录

    async def get_knowledge_base_by_id(
        self, knowledge_base_id: str, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a knowledge base by id."""
        query = {"knowledge_base_id": knowledge_base_id}
        if not include_deleted:
            query["is_delete"] = False
        return await self.db.knowledge_bases.find_one(query)

    async def delete_knowledge_base(self, knowledge_base_id: str) -> dict:
        """删除知识库，并删除其关联的文件记录（以及MinIO对象）"""
        knowledge_base = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_base_id}
        )
        if not knowledge_base:
            return {"status": "failed", "message": "知识库不存在"}

        # 收集所有关联文件ID（自动去重）
        file_ids = list({file["file_id"] for file in knowledge_base.get("files", [])})

        # 批量删除文件（包含MongoDB记录和MinIO文件）
        file_deletion_result = (
            await self.file_repo.delete_files_bulk(file_ids)
            if file_ids
            else {"status": "success", "message": "无关联文件需要删除", "detail": {}}
        )

        # 删除知识库文档
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

        # 处理结果
        response = {
            "status": "success",
            "message": "知识库及关联文件已删除",
            "detail": {
                "knowledge_base_deleted": delete_result.deleted_count,
                "file_deletion": file_deletion_result,
            },
        }

        # 处理部分成功情况
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
        result = await self.db.knowledge_bases.update_one(
            {"knowledge_base_id": knowledge_base_id, "is_delete": False},
            {
                "$set": {
                    "knowledge_base_name": new_name,
                    "last_modify_at": beijing_time_now(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Knowledge base not found or update failed",
            }
        return {"status": "success"}

    async def knowledge_base_add_file(
        self,
        knowledge_base_id: str,
        file_id: str,
        original_filename: str,
        minio_filename: str,
        minio_url: str,
    ) -> Dict[str, Any]:
        """向指定的 file_id 中添加解析的图片"""
        file = {
            "file_id": file_id,
            "filename": original_filename,
            "minio_filename": minio_filename,
            "minio_url": minio_url,
            "created_at": beijing_time_now(),
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
                "$set": {"last_modify_at": beijing_time_now()},
            },
        )
        if result.modified_count > 0:
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
        """
        通过知识库ID获取所有文件（仅返回url和filename）
        """
        try:
            # 查询未删除的知识库
            kb = await self.db.knowledge_bases.find_one(
                {
                    "knowledge_base_id": knowledge_base_id,
                },
                {"files": 1},  # 只返回files字段
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
        """
        获取知识库文件（带分页和搜索）
        """
        pipeline = [
            {"$match": {"knowledge_base_id": knowledge_base_id}},
            {"$unwind": "$files"},
        ]

        # 在展开数组后添加文件名过滤
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
        """
        获取用户所有文件（带分页和搜索）
        """
        match_query = (
            {"is_delete": False}
            if settings.single_tenant_mode
            else {"username": username, "is_delete": False}
        )
        pipeline = [
            {"$match": match_query},
            {"$unwind": "$files"},  # 展开后每个文档的 files 字段变为对象（不是数组）
            # 关键字搜索（修正字段路径）
            (
                {"$match": {"files.filename": {"$regex": keyword, "$options": "i"}}}
                if keyword
                else {"$match": {}}
            ),
            # 重新映射字段（关键步骤）
            {
                "$replaceRoot": {
                    "newRoot": {
                        # 将 files 对象的字段提升到顶层
                        "file_id": "$files.file_id",
                        "filename": "$files.filename",
                        "url": "$files.minio_url",
                        # 假设 knowledge_base_id 是知识库的唯一标识
                        "kb_name": "$knowledge_base_name",
                        "kb_id": "$knowledge_base_id",
                        "upload_time": "$files.created_at",
                    }
                }
            },
            # 分页和统计
            {
                "$facet": {
                    "metadata": [{"$count": "total"}],
                    "data": [
                        {"$skip": skip},
                        {"$limit": limit},
                        # 不再需要 $project，因为字段已在 replaceRoot 中处理
                    ],
                }
            },
        ]

        cursor = self.db.knowledge_bases.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return parse_aggregate_result(result)

    async def delete_file_from_knowledge_base(
        self, knowledge_id: str, file_id: str
    ) -> dict:
        """
        从指定知识库中删除文件，并删除对应的文件记录和存储文件
        """
        # 检查文件是否存在于知识库中
        kb = await self.db.knowledge_bases.find_one(
            {"knowledge_base_id": knowledge_id, "files.file_id": file_id},
            projection={"files.$": 1},
        )
        if not kb:
            logger.warning(
                f"文件 {file_id} 不存在于知识库 {knowledge_id} 或知识库不存在"
            )
            return {"status": "failed", "message": "文件不存在于该知识库或知识库不存在"}

        # 从知识库的files数组中移除该文件
        update_result = await self.db.knowledge_bases.update_one(
            {"knowledge_base_id": knowledge_id},
            {"$pull": {"files": {"file_id": file_id}}},
        )
        if update_result.modified_count == 0:
            logger.error(f"从知识库 {knowledge_id} 中移除文件 {file_id} 失败")
            return {"status": "failed", "message": "文件移除失败"}

        # 检查文件记录是否属于该知识库
        file_doc = await self.db.files.find_one(
            {"file_id": file_id, "knowledge_db_id": knowledge_id}
        )
        if not file_doc:
            logger.warning(f"文件记录 {file_id} 不存在或不属于知识库 {knowledge_id}")
            return {"status": "failed", "message": "文件记录不存在或不属于该知识库"}

        # 删除文件记录及MinIO中的文件
        deletion_result = await self.file_repo.delete_files_bulk([file_id])

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
        self, delete_list: List[Dict[str, str]]
    ) -> dict:
        """
        批量从知识库删除文件（支持跨知识库）
        参数格式示例：[{"knowledge_id": "kb1", "file_id": "f1"}, ...]
        返回带详细操作结果的状态报告
        """
        # 去重处理并分组（按knowledge_id分组）
        unique_pairs = {(item["knowledge_id"], item["file_id"]) for item in delete_list}
        grouped = defaultdict(list)
        for kb_id, file_id in unique_pairs:
            grouped[kb_id].append(file_id)

        # 第一阶段：从各知识库批量移除文件引用
        bulk_operations = []
        for kb_id, file_ids in grouped.items():
            bulk_operations.append(
                UpdateMany(
                    {"knowledge_base_id": kb_id},
                    {"$pull": {"files": {"file_id": {"$in": file_ids}}}},
                    array_filters=[],  # 确保正确应用操作
                )
            )

        # 执行批量更新
        if bulk_operations:
            try:
                bulk_result = await self.db.knowledge_bases.bulk_write(bulk_operations)
                # MongoDB bulk_write不返回每个文档的状态，这里记录整体结果
                logger.info(f"批量更新影响知识库数量: {bulk_result.modified_count}")
            except BulkWriteError as e:
                logger.error(f"批量更新异常: {str(e)}")
                return {"status": "error", "message": "批量操作异常"}

        # 第二阶段：验证文件归属并收集待删除ID
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
            # 二次验证分组匹配
            if doc["file_id"] in grouped.get(doc["knowledge_db_id"], []):
                valid_files.append(doc["file_id"])

        # 第三阶段：执行文件删除
        deletion_result = await self.file_repo.delete_files_bulk(valid_files)

        # 第四阶段：构建详细响应
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
                        bulk_result.modified_count if bulk_operations else 0
                    ),
                },
            },
        }

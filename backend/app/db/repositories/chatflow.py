from typing import Dict, Any, List, Optional
from app.core.logging import logger
from app.utils.timezone import beijing_time_now
from app.core.config import settings
from app.db.vector_db import vector_db_client
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from .knowledge_base import KnowledgeBaseRepository

class ChatflowRepository(BaseRepository):
    
    def __init__(self, db, knowledge_base_repo: Optional[KnowledgeBaseRepository] = None):
        super().__init__(db)
        self.knowledge_base_repo = knowledge_base_repo or KnowledgeBaseRepository(db)

    async def create_chatflow(
        self, chatflow_id: str, chatflow_name: str, username: str, workflow_id: str
    ):
        """创建一个新的会话"""

        chatflow = {
            "chatflow_id": chatflow_id,
            "workflow_id": workflow_id,
            "chatflow_name": chatflow_name,
            "username": username,
            "turns": [],  # 初始时为空列表，后续添加对话轮次
            "created_at": beijing_time_now(),
            "last_modify_at": beijing_time_now(),
            "is_read": False,
            "is_delete": False,
        }
        try:
            existing = await self.db.chatflows.find_one({"chatflow_id": chatflow_id})
            if existing:
                return {"status": "success", "message": "chatflow已存在，跳过创建"}

            await self.db.chatflows.insert_one(chatflow)
            return {"status": "success", "id": chatflow_id}
        except Exception as e:
            logger.error(f"创建chatflow失败: {str(e)}")
            return {"status": "error", "message": f"数据库错误: {str(e)}"}

    async def get_chatflow(self, chatflow_id: str):
        """获取指定 chatflow_id 的完整会话记录"""
        chatflow = await self.db.chatflows.find_one(
            {"chatflow_id": chatflow_id, "is_delete": False}
        )
        return chatflow if chatflow else None

    async def get_chatflows_by_user(self, username: str) -> List[Dict[str, Any]]:
        """按时间降序获取指定用户的所有会话"""
        query = (
            {"is_delete": False}
            if settings.single_tenant_mode
            else {"username": username, "is_delete": False}
        )
        cursor = self.db.chatflows.find(query).sort(
            "last_modify_at", -1
        )  # -1 表示降序排列
        return await cursor.to_list(length=100)  # 返回所有匹配的记录

    async def get_chatflows_by_workflow_id(
        self, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """按时间降序获取指定用户的所有会话"""
        cursor = self.db.chatflows.find(
            {"workflow_id": workflow_id, "is_delete": False}
        ).sort("last_modify_at", -1)  # -1 表示降序排列
        return await cursor.to_list(length=100)  # 返回所有匹配的记录

    async def update_chatflow_name(self, chatflow_id: str, new_name: str) -> dict:
        result = await self.db.chatflows.update_one(
            {"chatflow_id": chatflow_id, "is_delete": False},
            {
                "$set": {
                    "chatflow_name": new_name,
                    "last_modify_at": beijing_time_now(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "chatflow not found or update failed",
            }
        return {"status": "success"}

    async def chatflow_add_turn(
        self,
        chatflow_id: str,
        message_id: str,
        parent_message_id: str,
        user_message: str = "",
        ai_message: str = "",
        file_used: Optional[list] = None,
        temp_db: str = "",
        status: str = "",
        total_token: int = 0,
        completion_tokens: int = 0,
        prompt_tokens: int = 0,
    ) -> Dict[str, Any]:
        """向指定的 chatflow_id 中添加一轮chatflow"""
        file_used = file_used or []
        turn = {
            "message_id": message_id,
            "parent_message_id": parent_message_id,
            "user_message": user_message,
            "temp_db": temp_db,
            "ai_message": ai_message,
            "file_used": file_used,
            "status": status,
            "timestamp": beijing_time_now(),
            "total_token": total_token,
            "completion_tokens": completion_tokens,
            "prompt_tokens": prompt_tokens,
        }
        result = await self.db.chatflows.update_one(
            {"chatflow_id": chatflow_id, "is_delete": False},
            {
                "$push": {
                    "turns": turn,
                },
                "$set": {"last_modify_at": beijing_time_now()},
            },
        )
        return {"status": "success" if result.modified_count > 0 else "failed"}

    async def delete_chatflow(self, chatflow_id: str) -> dict:
        """根据 chatflow_id 删除指定会话，并删除关联的临时知识库"""
        # 获取chatflow文档
        chatflow = await self.db.chatflows.find_one({"chatflow_id": chatflow_id})
        if not chatflow:
            return {"status": "failed", "message": "chatflow not found"}

        # 收集所有关联的临时知识库ID
        temp_dbs = []
        for turn in chatflow.get("turns", []):
            if temp_db := turn.get("temp_db"):
                if temp_db.strip():  # 过滤空值
                    temp_dbs.append(temp_db.strip())

        # 去重并删除临时知识库
        deletion_results = []
        for db_id in set(temp_dbs):
            result = await self.knowledge_base_repo.delete_knowledge_base(db_id)
            deletion_results.append({"knowledge_base_id": db_id, "result": result})
            vector_db_client.delete_collection("colqwen" + db_id.replace("-", "_"))

        # 删除chatflow文档
        delete_result = await self.db.chatflows.delete_one({"chatflow_id": chatflow_id})

        if delete_result.deleted_count == 1:
            return {
                "status": "success",
                "message": f"chatflow {chatflow_id} deleted",
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "chatflow not found"}

    async def delete_workflow_all_chatflow(self, workflow_id: str) -> dict:
        """删除指定用户的所有会话及关联的临时知识库"""
        # 获取用户所有chatflow
        chatflows = await self.db.chatflows.find({"workflow_id": workflow_id}).to_list(
            length=100
        )
        # 收集所有临时知识库ID
        temp_dbs = []
        for conv in chatflows:
            for turn in conv.get("turns", []):
                if temp_db := turn.get("temp_db"):
                    if temp_db.strip():
                        temp_dbs.append(temp_db.strip())

        # 去重并删除临时知识库
        deletion_results = []
        for db_id in set(temp_dbs):
            result = await self.knowledge_base_repo.delete_knowledge_base(db_id)
            deletion_results.append({"knowledge_base_id": db_id, "result": result})
            vector_db_client.delete_collection("colqwen" + db_id.replace("-", "_"))

        # 删除所有chatflow文档
        delete_result = await self.db.chatflows.delete_many(
            {"workflow_id": workflow_id}
        )

        if delete_result.deleted_count > 0:
            return {
                "status": "success",
                "deleted_count": delete_result.deleted_count,
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "No chatflows found"}

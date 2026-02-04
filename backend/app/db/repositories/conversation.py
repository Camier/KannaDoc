from typing import Dict, Any, Optional
from app.core.logging import logger
from app.utils.timezone import beijing_time_now
from app.core.config import settings
from app.db.vector_db import vector_db_client
from app.db.cache import cache_service
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from .knowledge_base import KnowledgeBaseRepository


class ConversationRepository(BaseRepository):
    def __init__(
        self, db, knowledge_base_repo: Optional[KnowledgeBaseRepository] = None
    ):
        super().__init__(db)
        self.knowledge_base_repo = knowledge_base_repo or KnowledgeBaseRepository(db)

    async def create_conversation(
        self,
        conversation_id: str,
        username: str,
        conversation_name: str,
        model_config: dict,
    ):
        """创建一个新的会话"""

        conversation = {
            "conversation_id": conversation_id,
            "conversation_name": conversation_name,
            "username": username,
            "model_config": model_config,
            "turns": [],  # 初始时为空列表，后续添加对话轮次
            "created_at": beijing_time_now(),
            "last_modify_at": beijing_time_now(),
            "is_read": False,
            "is_delete": False,
        }
        try:
            await self.db.conversations.insert_one(conversation)
            return {"status": "success", "id": conversation_id}
        except DuplicateKeyError:
            logger.warning(f"对话ID冲突: {conversation_id}")
            return {"status": "failed", "message": "对话ID已存在，请勿重复创建"}
        except Exception as e:
            logger.error(f"创建对话失败: {str(e)}")
            return {"status": "error", "message": f"数据库错误: {str(e)}"}

    async def get_conversation(self, conversation_id: str):
        """获取指定 conversation_id 的完整会话记录"""
        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id, "is_delete": False}
        )
        return conversation if conversation else None

    async def get_conversation_model_config(self, conversation_id: str):
        """获取指定 conversation_id 的model config，优先从缓存读取"""
        cached = await cache_service.get_conversation_model_config(conversation_id)
        if cached is not None:
            return cached

        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id, "is_delete": False}
        )
        if not conversation:
            return None

        model_config = conversation["model_config"]
        await cache_service.set_conversation_model_config(conversation_id, model_config)
        return model_config

    async def get_conversations_by_user(self, username: str):
        """按时间降序获取指定用户的所有会话"""
        query = (
            {"is_delete": False}
            if settings.single_tenant_mode
            else {"username": username, "is_delete": False}
        )
        cursor = self.db.conversations.find(query).sort(
            "last_modify_at", -1
        )  # -1 表示降序排列
        return await cursor.to_list(length=100)  # 返回所有匹配的记录

    async def update_conversation_name(
        self, conversation_id: str, new_name: str
    ) -> dict:
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "is_delete": False},
            {
                "$set": {
                    "conversation_name": new_name,
                    "last_modify_at": beijing_time_now(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Conversation not found or update failed",
            }
        return {"status": "success"}

    async def update_conversation_model_config(
        self, conversation_id: str, model_config: dict
    ) -> dict:
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "is_delete": False},
            {
                "$set": {
                    "model_config": model_config,
                    "last_modify_at": beijing_time_now(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Conversation not found or update failed",
            }
        await cache_service.invalidate_conversation_model_config(conversation_id)
        return {"status": "success"}

    async def update_conversation_read_status(
        self, conversation_id: str, read_status=True
    ) -> dict:
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "is_delete": False},
            {
                "$set": {
                    "is_read": read_status,
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Conversation not found or update failed",
            }
        return {"status": "success"}

    async def add_turn(
        self,
        conversation_id: str,
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
        """向指定的 conversation_id 中添加一轮对话"""
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
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "is_delete": False},
            {
                "$push": {
                    "turns": turn,
                },
                "$set": {"last_modify_at": beijing_time_now()},
            },
        )
        return {"status": "success" if result.modified_count > 0 else "failed"}

    async def delete_conversation(self, conversation_id: str) -> dict:
        """根据 conversation_id 删除指定会话，并删除关联的临时知识库"""
        # 获取对话文档
        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id}
        )
        if not conversation:
            return {"status": "failed", "message": "Conversation not found"}

        # 收集所有关联的临时知识库ID
        temp_dbs = []
        for turn in conversation.get("turns", []):
            if temp_db := turn.get("temp_db"):
                if temp_db.strip():  # 过滤空值
                    temp_dbs.append(temp_db.strip())

        # 去重并删除临时知识库
        deletion_results = []
        for db_id in set(temp_dbs):
            result = await self.knowledge_base_repo.delete_knowledge_base(db_id)
            deletion_results.append({"knowledge_base_id": db_id, "result": result})
            vector_db_client.delete_collection("colqwen" + db_id.replace("-", "_"))

        # 删除对话文档
        delete_result = await self.db.conversations.delete_one(
            {"conversation_id": conversation_id}
        )

        if delete_result.deleted_count == 1:
            await cache_service.invalidate_conversation_model_config(conversation_id)
            return {
                "status": "success",
                "message": f"Conversation {conversation_id} deleted",
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "Conversation not found"}

    async def delete_conversations_by_user(self, username: str) -> dict:
        """删除指定用户的所有会话，并清理会话中引用的临时知识库"""
        conversations = await self.db.conversations.find(
            {"username": username}
        ).to_list(length=100)

        # 收集所有临时知识库ID
        temp_dbs = []
        for conv in conversations:
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

        # 删除所有对话文档
        delete_result = await self.db.conversations.delete_many({"username": username})

        if delete_result.deleted_count > 0:
            return {
                "status": "success",
                "deleted_count": delete_result.deleted_count,
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "No conversations found"}

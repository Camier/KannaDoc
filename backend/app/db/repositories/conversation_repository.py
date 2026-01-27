"""
Conversation Repository

Handles all operations related to chat conversations.
Lines 361-574 from original mongo.py
"""

from typing import Dict, Any, List
from pymongo.errors import DuplicateKeyError
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository
from app.db.vector_db import vector_db_client


class ConversationRepository(BaseRepository):
    """Repository for conversation operations."""

    async def create_conversation(
        self,
        conversation_id: str,
        username: str,
        conversation_name: str,
        model_config: dict,
    ):
        """Create a new conversation."""
        conversation = {
            "conversation_id": conversation_id,
            "conversation_name": conversation_name,
            "username": username,
            "model_config": model_config,
            "turns": [],
            "created_at": self._get_timestamp(),
            "last_modify_at": self._get_timestamp(),
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
        """Get complete conversation record by conversation_id."""
        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id, "is_delete": False}
        )
        return conversation if conversation else None

    async def get_conversation_model_config(self, conversation_id: str):
        """Get the model configuration for a conversation."""
        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id, "is_delete": False}
        )
        return conversation["model_config"] if conversation else None

    async def get_conversations_by_user(self, username: str) -> List[Dict[str, Any]]:
        """Get all conversations for a user, sorted by time descending."""
        cursor = self.db.conversations.find(
            {"username": username, "is_delete": False}
        ).sort("last_modify_at", -1)
        return await cursor.to_list(length=self._paginate(None, max_limit=500))

    async def update_conversation_name(
        self, conversation_id: str, new_name: str
    ) -> dict:
        """Update conversation name."""
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "is_delete": False},
            {
                "$set": {
                    "conversation_name": new_name,
                    "last_modify_at": self._get_timestamp(),
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
        """Update conversation model configuration."""
        result = await self.db.conversations.update_one(
            {"conversation_id": conversation_id, "is_delete": False},
            {
                "$set": {
                    "model_config": model_config,
                    "last_modify_at": self._get_timestamp(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Conversation not found or update failed",
            }
        return {"status": "success"}

    async def update_conversation_read_status(
        self, conversation_id: str, read_status=True
    ) -> dict:
        """Update conversation read status."""
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
        file_used: list = [],
        temp_db: str = "",
        status: str = "",
        total_token: int = 0,
        completion_tokens: int = 0,
        prompt_tokens: int = 0,
    ) -> Dict[str, Any]:
        """Add a conversation turn to a conversation."""
        turn = {
            "message_id": message_id,
            "parent_message_id": parent_message_id,
            "user_message": user_message,
            "temp_db": temp_db,
            "ai_message": ai_message,
            "file_used": file_used,
            "status": status,
            "timestamp": self._get_timestamp(),
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
                "$set": {"last_modify_at": self._get_timestamp()},
            },
        )
        return {"status": "success" if result.modified_count > 0 else "failed"}

    async def delete_conversation(
        self, conversation_id: str, knowledge_base_repo=None
    ) -> dict:
        """
        Delete a conversation and its associated temporary knowledge bases.

        Args:
            conversation_id: Conversation ID to delete
            knowledge_base_repo: Optional KnowledgeBaseRepository for deleting temp KBs
        """
        # Get conversation document
        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id}
        )
        if not conversation:
            return {"status": "failed", "message": "Conversation not found"}

        # Collect all associated temporary knowledge base IDs
        temp_dbs = []
        for turn in conversation.get("turns", []):
            if temp_db := turn.get("temp_db"):
                if temp_db.strip():
                    temp_dbs.append(temp_db.strip())

        # Delete temporary knowledge bases if repository is provided
        deletion_results = []
        if knowledge_base_repo:
            for db_id in set(temp_dbs):
                result = await knowledge_base_repo.delete_knowledge_base(db_id)
                deletion_results.append({"knowledge_base_id": db_id, "result": result})

        # Bulk delete vector collections
        if temp_dbs:
            collection_names = ["colqwen" + db_id.replace("-", "_") for db_id in set(temp_dbs)]
            vector_delete_result = vector_db_client.delete_collections_bulk(collection_names)
            logger.info(f"Bulk deleted {vector_delete_result['deleted_count']}/{vector_delete_result['total_requested']} vector collections")

        # Delete conversation document
        delete_result = await self.db.conversations.delete_one(
            {"conversation_id": conversation_id}
        )

        if delete_result.deleted_count == 1:
            return {
                "status": "success",
                "message": f"Conversation {conversation_id} deleted",
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "Conversation not found"}

    async def delete_all_conversation(
        self, username: str, knowledge_base_repo=None
    ) -> dict:
        """
        Delete all conversations for a user and associated temporary knowledge bases.

        Args:
            username: Username to delete conversations for
            knowledge_base_repo: Optional KnowledgeBaseRepository for deleting temp KBs
        """
        # Get all user conversations
        conversations = await self.db.conversations.find({"username": username}).to_list(
            length=None
        )

        # Collect all temporary knowledge base IDs
        temp_dbs = []
        for conv in conversations:
            for turn in conv.get("turns", []):
                if temp_db := turn.get("temp_db"):
                    if temp_db.strip():
                        temp_dbs.append(temp_db.strip())

        # Delete temporary knowledge bases if repository is provided
        deletion_results = []
        if knowledge_base_repo:
            for db_id in set(temp_dbs):
                result = await knowledge_base_repo.delete_knowledge_base(db_id)
                deletion_results.append({"knowledge_base_id": db_id, "result": result})

        # Bulk delete vector collections
        if temp_dbs:
            collection_names = ["colqwen" + db_id.replace("-", "_") for db_id in set(temp_dbs)]
            vector_delete_result = vector_db_client.delete_collections_bulk(collection_names)
            logger.info(f"Bulk deleted {vector_delete_result['deleted_count']}/{vector_delete_result['total_requested']} vector collections")

        # Delete all conversation documents
        delete_result = await self.db.conversations.delete_many({"username": username})

        if delete_result.deleted_count > 0:
            return {
                "status": "success",
                "deleted_count": delete_result.deleted_count,
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "No conversations found"}

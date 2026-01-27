"""
Chatflow Repository

Handles all operations related to workflow chatflows.
Lines 576-747 from original mongo.py
"""

from typing import Dict, Any, List
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository
from app.db.vector_db import vector_db_client


class ChatflowRepository(BaseRepository):
    """Repository for chatflow operations."""

    async def create_chatflow(
        self, chatflow_id: str, chatflow_name: str, username: str, workflow_id: str
    ):
        """Create a new chatflow."""
        chatflow = {
            "chatflow_id": chatflow_id,
            "workflow_id": workflow_id,
            "chatflow_name": chatflow_name,
            "username": username,
            "turns": [],
            "created_at": self._get_timestamp(),
            "last_modify_at": self._get_timestamp(),
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
        """Get complete chatflow record by chatflow_id."""
        chatflow = await self.db.chatflows.find_one(
            {"chatflow_id": chatflow_id, "is_delete": False}
        )
        return chatflow if chatflow else None

    async def get_chatflows_by_user(self, username: str) -> List[Dict[str, Any]]:
        """Get all chatflows for a user, sorted by time descending."""
        cursor = self.db.chatflows.find(
            {"username": username, "is_delete": False}
        ).sort("last_modify_at", -1)
        return await cursor.to_list(length=self._paginate(None, max_limit=500))

    async def get_chatflows_by_workflow_id(
        self, workflow_id: str
    ) -> List[Dict[str, Any]]:
        """Get all chatflows for a workflow, sorted by time descending."""
        cursor = self.db.chatflows.find(
            {"workflow_id": workflow_id, "is_delete": False}
        ).sort("last_modify_at", -1)
        return await cursor.to_list(length=self._paginate(None, max_limit=500))

    async def update_chatflow_name(self, chatflow_id: str, new_name: str) -> dict:
        """Update chatflow name."""
        result = await self.db.chatflows.update_one(
            {"chatflow_id": chatflow_id, "is_delete": False},
            {
                "$set": {
                    "chatflow_name": new_name,
                    "last_modify_at": self._get_timestamp(),
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
        file_used: list = [],
        temp_db: str = "",
        status: str = "",
        total_token: int = 0,
        completion_tokens: int = 0,
        prompt_tokens: int = 0,
    ) -> Dict[str, Any]:
        """Add a turn to a chatflow."""
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
        result = await self.db.chatflows.update_one(
            {"chatflow_id": chatflow_id, "is_delete": False},
            {
                "$push": {
                    "turns": turn,
                },
                "$set": {"last_modify_at": self._get_timestamp()},
            },
        )
        return {"status": "success" if result.modified_count > 0 else "failed"}

    async def delete_chatflow(
        self, chatflow_id: str, knowledge_base_repo=None
    ) -> dict:
        """
        Delete a chatflow and its associated temporary knowledge bases.

        Args:
            chatflow_id: Chatflow ID to delete
            knowledge_base_repo: Optional KnowledgeBaseRepository for deleting temp KBs
        """
        # Get chatflow document
        chatflow = await self.db.chatflows.find_one({"chatflow_id": chatflow_id})
        if not chatflow:
            return {"status": "failed", "message": "chatflow not found"}

        # Collect all associated temporary knowledge base IDs
        temp_dbs = []
        for turn in chatflow.get("turns", []):
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

        # Delete chatflow document
        delete_result = await self.db.chatflows.delete_one({"chatflow_id": chatflow_id})

        if delete_result.deleted_count == 1:
            return {
                "status": "success",
                "message": f"chatflow {chatflow_id} deleted",
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "chatflow not found"}

    async def delete_workflow_all_chatflow(
        self, workflow_id: str, knowledge_base_repo=None
    ) -> dict:
        """
        Delete all chatflows for a workflow and associated temporary knowledge bases.

        Args:
            workflow_id: Workflow ID to delete chatflows for
            knowledge_base_repo: Optional KnowledgeBaseRepository for deleting temp KBs
        """
        # Get all workflow chatflows
        chatflows = await self.db.chatflows.find({"workflow_id": workflow_id}).to_list(
            length=None
        )

        # Collect all temporary knowledge base IDs
        temp_dbs = []
        for conv in chatflows:
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

        # Delete all chatflow documents
        delete_result = await self.db.chatflows.delete_many({"workflow_id": workflow_id})

        if delete_result.deleted_count > 0:
            return {
                "status": "success",
                "deleted_count": delete_result.deleted_count,
                "knowledge_base_deletion": deletion_results,
            }
        return {"status": "failed", "message": "No chatflows found"}

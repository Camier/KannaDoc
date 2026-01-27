"""
Workflow Repository

Handles all operations related to workflows.
Lines 1379-1492 from original mongo.py
"""

from typing import Dict, Any, List
from pymongo.errors import DuplicateKeyError
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository


class WorkflowRepository(BaseRepository):
    """Repository for workflow operations."""

    async def update_workflow(
        self,
        username: str,
        workflow_id: str,
        workflow_name: str,
        workflow_config: dict,
        start_node: str = "node_start",
        global_variables: dict = None,
        nodes: list = None,
        edges: list = None,
    ):
        """Create or update a workflow."""
        # Handle mutable default arguments
        global_variables = global_variables if global_variables is not None else {}
        nodes = nodes if nodes is not None else []
        edges = edges if edges is not None else []

        current_time = self._get_timestamp()
        query = {"workflow_id": workflow_id, "username": username}
        update = {
            "$set": {
                "workflow_name": workflow_name,
                "workflow_config": workflow_config,
                "nodes": nodes,
                "edges": edges,
                "start_node": start_node,
                "global_variables": global_variables,
                "last_modify_at": current_time,
                "is_delete": False,
            },
            "$setOnInsert": {"created_at": current_time},
        }

        try:
            result = await self.db.workflows.update_one(query, update, upsert=True)
            if result.upserted_id is not None:
                return {
                    "status": "success",
                    "message": "Workflow created",
                    "id": workflow_id,
                }
            else:
                return {
                    "status": "success",
                    "message": "Workflow updated",
                    "id": workflow_id,
                }
        except DuplicateKeyError:
            logger.error(f"Workflow ID冲突: {workflow_id}")
            return {
                "status": "failed",
                "message": "Workflow ID已存在，请检查用户名和ID组合",
            }
        except Exception as e:
            logger.error(f"保存workflow失败: {str(e)}")
            return {"status": "error", "message": f"数据库错误: {str(e)}"}

    async def get_workflow(self, workflow_id: str):
        """Get complete workflow record by workflow_id."""
        workflow = await self.db.workflows.find_one(
            {"workflow_id": workflow_id, "is_delete": False}
        )
        return workflow if workflow else None

    async def get_workflows_by_user(self, username: str) -> List[Dict[str, Any]]:
        """Get all workflows for a user, sorted by time descending."""
        cursor = self.db.workflows.find(
            {"username": username, "is_delete": False}
        ).sort("last_modify_at", -1)
        return await cursor.to_list(length=self._paginate(None, max_limit=500))

    async def update_workflow_name(self, workflow_id: str, new_name: str) -> dict:
        """Update workflow name."""
        result = await self.db.workflows.update_one(
            {"workflow_id": workflow_id, "is_delete": False},
            {
                "$set": {
                    "workflow_name": new_name,
                    "last_modify_at": self._get_timestamp(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Workflow not found or update failed",
            }
        return {"status": "success"}

    async def delete_workflow(
        self, workflow_id: str, chatflow_repo=None
    ) -> dict:
        """
        Delete a workflow and its associated temporary knowledge bases.

        Args:
            workflow_id: Workflow ID to delete
            chatflow_repo: Optional ChatflowRepository for deleting associated chatflows
        """
        # Get workflow document
        workflow = await self.db.workflows.find_one({"workflow_id": workflow_id})
        if not workflow:
            return {"status": "failed", "message": "Workflow not found"}

        # Delete temporary knowledge bases
        deletion_results = []
        if chatflow_repo:
            result = await chatflow_repo.delete_workflow_all_chatflow(workflow_id)
            deletion_results.append(
                {"chatflow_delete_count": result.get("deleted_count", "0")}
            )

        # Delete workflow
        delete_result = await self.db.workflows.delete_one({"workflow_id": workflow_id})

        if delete_result.deleted_count == 1:
            return {
                "status": "success",
                "message": f"Workflow {workflow_id} deleted",
                "chatflow_deletion": deletion_results,
            }
        return {"status": "failed", "message": "Workflow not found"}

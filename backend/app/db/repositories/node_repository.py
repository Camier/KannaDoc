"""
Node Repository

Handles all operations related to custom nodes.
Lines 1494-1557 from original mongo.py
"""

from typing import Dict, Any, List, Union
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository


class NodeRepository(BaseRepository):
    """Repository for custom node operations."""

    async def update_custom_nodes(
        self,
        username: str,
        custom_node_name: str,
        custom_node: dict = None,
    ):
        """Update or create custom nodes for a user."""
        try:
            # Use update operators to implement upsert
            update_result = await self.db.nodes.update_one(
                {"username": username},
                {
                    "$set": {
                        f"custom_nodes.{custom_node_name}": custom_node
                    },
                    "$setOnInsert": {"username": username},
                },
                upsert=True,
            )
            return {"status": "success", "message": "Node saved"}
        except Exception as e:
            logger.error(f"保存Node失败: {str(e)}")
            return {"status": "failed", "message": f"数据库错误: {str(e)}"}

    async def get_custom_nodes(self, username: str) -> dict:
        """Get all custom nodes for a user."""
        try:
            # Query document by username
            result = await self.db.nodes.find_one({"username": username})
            # Return custom_nodes field if exists, otherwise return empty dict
            return result.get("custom_nodes", {}) if result else {}
        except Exception as e:
            logger.error(f"获取custom_nodes失败: {str(e)}")
            return {}

    async def delete_custom_nodes(
        self,
        username: str,
        custom_node_names: Union[str, List[str]],
    ) -> dict:
        """Delete custom nodes for a user."""
        try:
            # Normalize to list format
            if isinstance(custom_node_names, str):
                custom_node_names = [custom_node_names]

            # Build $unset operation field dictionary (MongoDB requires empty string values)
            unset_fields = {f"custom_nodes.{name}": "" for name in custom_node_names}

            # Execute update operation to delete specified fields
            update_result = await self.db.nodes.update_one(
                {"username": username},
                {"$unset": unset_fields},
            )

            # Return different messages based on whether modifications were made
            if update_result.modified_count > 0:
                return {"status": "success", "message": "Nodes deleted"}
            else:
                return {"status": "info", "message": "No nodes were deleted"}

        except Exception as e:
            logger.error(f"删除节点失败: {str(e)}")
            return {"status": "failed", "message": f"数据库错误: {str(e)}"}

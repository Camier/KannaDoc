from typing import Dict, Any, List, Optional, Union
from app.core.logging import logger
from app.utils.timezone import beijing_time_now
from app.core.config import settings
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from .chatflow import ChatflowRepository

class WorkflowRepository(BaseRepository):
    
    def __init__(self, db, chatflow_repo: Optional[ChatflowRepository] = None):
        super().__init__(db)
        self.chatflow_repo = chatflow_repo or ChatflowRepository(db)

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
        """创建或更新一个工作流"""

        # 处理可变默认参数
        global_variables = global_variables if global_variables is not None else {}
        nodes = nodes if nodes is not None else []
        edges = edges if edges is not None else []

        current_time = beijing_time_now()
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
        """获取指定 workflow_id 的完整workflow记录"""
        workflow = await self.db.workflows.find_one(
            {"workflow_id": workflow_id, "is_delete": False}
        )
        return workflow if workflow else None

    async def get_workflows_by_user(self, username: str):
        """按时间降序获取指定用户的所有workflow"""
        query = (
            {"is_delete": False}
            if settings.single_tenant_mode
            else {"username": username, "is_delete": False}
        )
        cursor = self.db.workflows.find(query).sort(
            "last_modify_at", -1
        )  # -1 表示降序排列
        return await cursor.to_list(length=100)  # 返回所有匹配的记录

    async def update_workflow_name(self, workflow_id: str, new_name: str) -> dict:
        result = await self.db.workflows.update_one(
            {"workflow_id": workflow_id, "is_delete": False},
            {
                "$set": {
                    "workflow_name": new_name,
                    "last_modify_at": beijing_time_now(),
                }
            },
        )
        if result.modified_count == 0:
            return {
                "status": "failed",
                "message": "Workflow not found or update failed",
            }
        return {"status": "success"}

    async def delete_workflow(self, workflow_id: str) -> dict:
        """根据 workflow_id 删除指定workflow，并删除关联的临时知识库"""
        # 获取对话文档
        workflow = await self.db.workflows.find_one({"workflow_id": workflow_id})
        if not workflow:
            return {"status": "failed", "message": "Workflow not found"}

        # 去重并删除临时知识库
        deletion_results = []
        result = await self.chatflow_repo.delete_workflow_all_chatflow(workflow_id)
        deletion_results.append(
            {"chatflow_delete_count": result.get("deleted_count", "0")}
        )

        # 删除workflow
        delete_result = await self.db.workflows.delete_one({"workflow_id": workflow_id})

        if delete_result.deleted_count == 1:
            return {
                "status": "success",
                "message": f"Workflow {workflow_id} deleted",
                "chatflow_deletion": deletion_results,
            }
        return {"status": "failed", "message": "Workflow not found"}

class NodeRepository(BaseRepository):
    
    async def update_custom_nodes(
        self,
        username: str,
        custom_node_name: str,
        custom_node: dict = None,
    ):
        try:
            # 使用更新操作符实现 upsert
            update_result = await self.db.nodes.update_one(
                {"username": username},  # 查询条件
                {
                    "$set": {
                        f"custom_nodes.{custom_node_name}": custom_node  # 动态字段名
                    },
                    "$setOnInsert": {"username": username},  # 仅在插入时设置的字段
                },
                upsert=True,  # 自动创建新文档
            )
            return {"status": "success", "message": "Node saved"}
        except Exception as e:
            logger.error(f"保存Node失败: {str(e)}")
            return {"status": "failed", "message": f"数据库错误: {str(e)}"}

    # 自定义节点查询方法
    async def get_custom_nodes(self, username: str) -> dict:
        try:
            # 根据用户名查询文档
            result = await self.db.nodes.find_one({"username": username})
            # 如果文档存在且包含custom_nodes字段则返回，否则返回空字典

            return result.get("custom_nodes", {}) if result else {}
        except Exception as e:
            logger.error(f"获取custom_nodes失败: {str(e)}")
            return {}

    async def delete_custom_nodes(
        self,
        username: str,
        custom_node_names: Union[str, List[str]],  # 支持字符串或列表类型
    ) -> dict:
        try:
            # 统一转换为列表格式，简化后续处理
            if isinstance(custom_node_names, str):
                custom_node_names = [custom_node_names]

            # 构建 $unset 操作的字段字典（MongoDB 要求字段值为空字符串）
            unset_fields = {f"custom_nodes.{name}": "" for name in custom_node_names}

            # 执行更新操作删除指定字段
            update_result = await self.db.nodes.update_one(
                {"username": username},  # 查询条件
                {"$unset": unset_fields},  # 批量删除字段
            )

            # 根据是否实际修改返回不同提示
            if update_result.modified_count > 0:
                return {"status": "success", "message": "Nodes deleted"}
            else:
                return {"status": "info", "message": "No nodes were deleted"}

        except Exception as e:
            logger.error(f"删除节点失败: {str(e)}")
            return {"status": "failed", "message": f"数据库错误: {str(e)}"}

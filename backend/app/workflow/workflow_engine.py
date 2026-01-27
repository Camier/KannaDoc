# workflow/workflow_engine.py
import asyncio
import json
import re
from typing import Dict, List, Any, Optional
import uuid
import docker

from app.db.redis import redis
from app.models.workflow import UserMessage
from app.utils.timezone import beijing_time_now
from app.workflow.mcp_tools import mcp_call_tools
from app.workflow.sandbox import CodeSandbox
from app.workflow.code_scanner import CodeScanner
from app.workflow.graph import TreeNode, WorkflowGraph
from app.workflow.llm_service import ChatService
from app.core.logging import logger
from app.core.circuit_breaker import llm_service_circuit, CircuitBreakerConfig
from app.workflow.utils import find_outermost_braces, replace_template
from datetime import datetime

# Import extracted components
from app.workflow.components import (
    MAX_CONTEXT_SIZE,
    MAX_CONTEXT_ENTRIES,
    PROVIDER_TIMEOUTS,
    LOOP_LIMITS,
    CHECKPOINT_CONFIG,
    WorkflowCheckpointManager,
    LLMClient,
)


class WorkflowCheckpointManager:
    """
    Enhanced checkpoint management for workflow recovery.
    Supports automatic checkpointing and rollback capabilities.
    """

    def __init__(self, task_id: str, engine: "WorkflowEngine"):
        self.task_id = task_id
        self.engine = engine
        self.checkpoint_count = 0
        self.last_checkpoint_node = None

    async def save_checkpoint(self, reason: str = "manual") -> dict:
        """
        Save a workflow checkpoint with metadata.

        Args:
            reason: Why checkpoint was created (manual, auto, loop, gate, error)

        Returns:
            Checkpoint metadata
        """
        import time

        checkpoint_id = f"{self.task_id}_{int(time.time())}"
        self.checkpoint_count += 1

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "task_id": self.task_id,
            "created_at": datetime.now().isoformat(),
            "reason": reason,
            "node": self.last_checkpoint_node,
            "checkpoint_number": self.checkpoint_count,
            "state": {
                "global_variables": dict(self.engine.global_variables),
                "execution_status": dict(self.engine.execution_status),
                "loop_index": dict(self.engine.loop_index),
                "context_snapshot": self._get_context_snapshot(),
            },
        }

        # Save to Redis with expiry
        redis_conn = await redis.get_task_connection()
        checkpoint_key = f"workflow:{self.task_id}:checkpoint:{checkpoint_id}"

        await redis_conn.setex(
            checkpoint_key,
            86400,  # 24 hour retention
            json.dumps(checkpoint),
        )

        # Add to checkpoint index
        await redis_conn.zadd(
            f"workflow:{self.task_id}:checkpoints",
            {checkpoint_id: self.checkpoint_count},
        )

        # Trim old checkpoints
        await self._trim_checkpoints(redis_conn)

        logger.info(
            f"Workflow {self.task_id}: Checkpoint #{self.checkpoint_count} saved "
            f"(reason={reason}, node={self.last_checkpoint_node})"
        )

        return checkpoint

    async def load_checkpoint(self, checkpoint_id: str = None) -> bool:
        """
        Load workflow from checkpoint.

        Args:
            checkpoint_id: Specific checkpoint to load, or latest if None

        Returns:
            True if loaded successfully
        """
        redis_conn = await redis.get_task_connection()

        # Get latest checkpoint if not specified
        if checkpoint_id is None:
            checkpoints = await redis_conn.zrevrange(
                f"workflow:{self.task_id}:checkpoints", 0, 0
            )
            if not checkpoints:
                logger.warning(f"Workflow {self.task_id}: No checkpoints found")
                return False
            checkpoint_id = checkpoints[0]

        checkpoint_key = f"workflow:{self.task_id}:checkpoint:{checkpoint_id}"
        data = await redis_conn.get(checkpoint_key)

        if not data:
            logger.error(f"Workflow {self.task_id}: Checkpoint {checkpoint_id} not found")
            return False

        checkpoint = json.loads(data)

        # Restore state
        self.engine.global_variables = checkpoint["state"]["global_variables"]
        self.engine.execution_status = checkpoint["state"]["execution_status"]
        self.engine.loop_index = checkpoint["state"]["loop_index"]

        logger.info(
            f"Workflow {self.task_id}: Restored from checkpoint {checkpoint_id} "
            f"(#{checkpoint['checkpoint_number']}, created={checkpoint['created_at']})"
        )

        return True

    async def rollback_to_checkpoint(self, checkpoint_id: str = None) -> bool:
        """
        Rollback workflow to a previous checkpoint.

        Args:
            checkpoint_id: Specific checkpoint to rollback to, or latest if None

        Returns:
            True if rollback successful
        """
        logger.warning(f"Workflow {self.task_id}: Rolling back to checkpoint...")
        success = await self.load_checkpoint(checkpoint_id)

        if success:
            # Clear execution state after rollback point
            redis_conn = await redis.get_task_connection()
            await redis_conn.xadd(
                f"workflow:events:{self.task_id}",
                {
                    "type": "workflow",
                    "status": "rollback",
                    "result": "",
                    "error": f"Rolled back to checkpoint",
                    "create_time": str(datetime.now()),
                },
            )

        return success

    def _get_context_snapshot(self) -> dict:
        """Get a lightweight snapshot of current context."""
        snapshot = {}
        for node_id, entries in self.engine.context.items():
            if entries:
                # Store only the most recent entry
                snapshot[node_id] = {
                    "last_result": entries[-1].get("result", "")[:200],
                    "entry_count": len(entries),
                }
        return snapshot

    async def _trim_checkpoints(self, redis_conn):
        """Keep only the most recent checkpoints."""
        max_checkpoints = CHECKPOINT_CONFIG["max_checkpoints"]
        await redis_conn.zremrangebyrank(
            f"workflow:{self.task_id}:checkpoints",
            0,
            -(max_checkpoints + 1),
        )

    async def list_checkpoints(self) -> list:
        """List all available checkpoints."""
        redis_conn = await redis.get_task_connection()
        checkpoint_ids = await redis_conn.zrevrange(
            f"workflow:{self.task_id}:checkpoints", 0, -1
        )

        checkpoints = []
        for cid in checkpoint_ids:
            key = f"workflow:{self.task_id}:checkpoint:{cid}"
            data = await redis_conn.get(key)
            if data:
                checkpoints.append(json.loads(data))

        return checkpoints

    async def should_checkpoint(self, node: TreeNode, node_type: str) -> bool:
        """
        Determine if a checkpoint should be created at this node.

        Args:
            node: Current node
            node_type: Node type

        Returns:
            True if checkpoint should be created
        """
        if not CHECKPOINT_CONFIG["enabled"]:
            return False

        self.last_checkpoint_node = node.node_id

        # Checkpoint at condition gates
        if node_type == "condition" and CHECKPOINT_CONFIG["on_condition_gate"]:
            return True

        # Checkpoint after loop iterations
        if node_type == "loop" and CHECKPOINT_CONFIG["on_loop_complete"]:
            # Check if this is a loop exit (node is in loop_parent.loop_last)
            if node.loop_parent and node in node.loop_parent.loop_last:
                return True

        # Checkpoint at regular intervals
        completed_count = sum(1 for v in self.engine.execution_status.values() if v)
        if completed_count > 0 and completed_count % CHECKPOINT_CONFIG["interval_nodes"] == 0:
            return True

        return False


def get_provider_timeout(model_name: str) -> int:
    """Get provider-specific timeout for a model."""
    model_lower = model_name.lower()
    for provider, timeout in PROVIDER_TIMEOUTS.items():
        if provider == "default":
            continue
        if provider in model_lower:
            return timeout
    return PROVIDER_TIMEOUTS["default"]


async def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
):
    """
    Execute function with exponential backoff retry.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Function result

    Raises:
        Exception: If all retries exhausted
    """
    import asyncio

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                # All retries exhausted
                raise

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = delay * 0.1  # 10% jitter
            import random
            actual_delay = delay + random.uniform(-jitter, jitter)

            logger.warning(
                f"Workflow LLM call failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                f"Retrying in {actual_delay:.2f}s..."
            )
            await asyncio.sleep(actual_delay)

    raise last_exception


class WorkflowEngine:
    def __init__(
        self,
        username: str,
        nodes: List[Dict],
        edges: List[Dict],
        global_variables,
        start_node="node_start",
        task_id: str = None,
        breakpoints=None,
        user_message="",
        parent_id="",
        temp_db_id="",
        chatflow_id="",
        docker_image_use="python-sandbox:latest",
        need_save_image="",
    ):
        self.nodes = nodes
        self.edges = edges
        self.start_node = start_node
        self.global_variables = global_variables
        self.context: Dict[str, Any] = {}
        self._total_context_entries = 0  # Track total entries for cleanup
        self.scanner = CodeScanner()
        self.graph = self.get_graph()
        self.execution_status = {node["id"]: False for node in self.nodes}
        # 延迟初始化沙箱
        self.sandbox: Optional[CodeSandbox] = None
        self.task_id = task_id  # Kafka任务id
        self.breakpoints = set(breakpoints or [])
        self.execution_stack = [self.graph[1]]  # 用栈结构保存执行状态
        self.break_workflow = False
        self.break_workflow_get_input = False
        self.skip_nodes = []
        self.loop_index = {}
        self.user_message = user_message
        self.parent_id = parent_id
        self.temp_db_id = temp_db_id
        self.chatflow_id = chatflow_id
        self.user_image_urls = []
        self.supply_info = ""  # mcp等工具调用产生的额外的llm输入信息
        self.docker_image_use = (
            "sandbox-" + username + "-" + docker_image_use
            if (docker_image_use and not docker_image_use == "python-sandbox:latest")
            else "python-sandbox:latest"
        )
        self.need_save_image = (
            "sandbox-" + username + "-" + need_save_image if need_save_image else ""
        )

        # Enhanced fault tolerance systems
        self.checkpoint_manager = WorkflowCheckpointManager(self.task_id, self)
        # QualityAssessmentEngine removed - unused, see scripts/archive/quality_assessment/

    async def __aenter__(self):
        # 创建并启动沙箱
        self.sandbox = CodeSandbox(self.docker_image_use)

        await self.sandbox.__aenter__()
        if not self.sandbox:
            raise ValueError(
                f"镜像'{'-'.join(self.docker_image_use.split('-')[2:])}'启动失败，请检查镜像是否存在"
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # 退出上下文时清理资源
        if self.sandbox:
            if self.need_save_image and not self.sandbox.failed:
                new_image = await self.sandbox.commit(
                    self.need_save_image.split(":")[0],
                    self.need_save_image.split(":")[1],
                )
                redis_conn = await redis.get_task_connection()
                await redis_conn.xadd(
                    f"workflow:events:{self.task_id}",  # 使用新的事件流键
                    {
                        "type": "workflow",
                        "status": "dockering",
                        "result": new_image,
                        "error": "",
                        "create_time": str(beijing_time_now()),
                    },
                )
                # 清理沙箱
            await self.sandbox.__aexit__(exc_type, exc, tb)

    async def save_state(self):
        """保存当前执行状态到Redis"""
        state = {
            "global_variables": self.global_variables,
            "execution_status": self.execution_status,
            "execution_stack": [n.node_id for n in self.execution_stack],
            "loop_index": self.loop_index,
            "context": self.context,
            "skip_nodes": self.skip_nodes,
            "nodes": self.nodes,  # 保存节点定义
            "edges": self.edges,  # 保存边定义
        }
        redis_conn = await redis.get_task_connection()
        await redis_conn.setex(
            f"workflow:{self.task_id}:state", 3600, json.dumps(state)
        )

    async def load_state(self):
        """从Redis加载执行状态"""
        redis_conn = await redis.get_task_connection()
        state = await redis_conn.get(f"workflow:{self.task_id}:state")
        if state:
            state = json.loads(state)
            self.global_variables = state["global_variables"]
            self.execution_status = state["execution_status"]
            self.loop_index = state["loop_index"]
            self.context = state["context"]
            # 重建执行栈
            self.execution_stack = [
                TreeNode.get_node(nid) for nid in state["execution_stack"]
            ]
            self.skip_nodes = state["skip_nodes"]
            return True
        return False

    async def _send_pause_event(self, node: TreeNode, chatInput: bool = False):
        redis_conn = await redis.get_task_connection()
        if chatInput and not self.breakpoints:
            status = "vlm_input"
        # input中断同时处于调试模式
        elif chatInput and self.breakpoints:
            status = "vlm_input_debug"
        else:
            status = "pause"
        await redis_conn.xadd(
            f"workflow:events:{self.task_id}",
            {
                "type": "node",
                "node": node.node_id,
                "status": status,
                "result": "",
                "error": "",
                "variables": json.dumps(self.global_variables),
                "create_time": str(beijing_time_now()),
            },
        )
        # 刷新过期时间
        pipeline = redis_conn.pipeline()
        pipeline.expire(f"workflow:{self.task_id}", 3600)
        pipeline.expire(f"workflow:{self.task_id}:nodes", 3600)
        pipeline.expire(f"workflow:events:{self.task_id}", 3600)
        await pipeline.execute()

    def _cleanup_context_if_needed(self):
        """Clean up context dictionary to prevent memory leaks in long-running workflows."""
        if self._total_context_entries > MAX_CONTEXT_ENTRIES:
            # Remove oldest entries from each node's context until under limit
            entries_to_remove = self._total_context_entries - (MAX_CONTEXT_ENTRIES // 2)
            for node_id in list(self.context.keys()):
                node_context = self.context[node_id]
                if len(node_context) > MAX_CONTEXT_SIZE:
                    # Keep only the most recent entries
                    remove_count = min(len(node_context) - MAX_CONTEXT_SIZE, entries_to_remove)
                    self.context[node_id] = node_context[remove_count:]
                    entries_to_remove -= remove_count
                    self._total_context_entries -= remove_count
                if entries_to_remove <= 0:
                    break
            logger.info(f"Workflow {self.task_id}: Cleaned up context, total entries: {self._total_context_entries}")

    def get_graph(self):
        try:
            self.graph = WorkflowGraph(self.nodes, self.edges, self.start_node)
            root = self.graph.root
            msg = "工作流验证通过"
            return (True, root, msg)
        except ValueError as e:
            msg = f"工作流验证失败: {str(e)}"
            return (False, [], msg)

    def safe_eval(self, expr: str, node_name: str, node_id: str) -> bool:
        """安全执行条件表达式

        SECURITY: Restricted builtins to prevent code injection attacks.
        Only safe types and operators are available in the eval context.
        """
        # 扫描表达式代码
        scan_result = self.scanner.scan_code(expr)
        if not scan_result["safe"]:
            raise ValueError(
                f"{node_id}:节点{node_name}: 不安全的表达式: {expr}, 问题: {scan_result['issues']}"
            )

        # 限制执行环境，仅允许访问context变量
        try:
            def _coerce_value(value):
                """Safely coerce string values to their appropriate types."""
                if isinstance(value, str):
                    if value == "":
                        return ""
                    # SECURITY: Do NOT use eval() here - it's a code injection risk
                    # Only parse literal values that are safe
                    value_lower = value.lower()
                    if value_lower == "true":
                        return True
                    elif value_lower == "false":
                        return False
                    elif value_lower == "null":
                        return None
                    # Try to parse as number (int or float)
                    try:
                        if "." in value:
                            return float(value)
                        return int(value)
                    except ValueError:
                        pass
                    # Return as string if no conversion applies
                    return value
                return value

            # SECURITY: Enable strict builtins restriction to prevent code injection
            # Only allows safe operations on provided variables
            return eval(
                expr,
                {"__builtins__": {}},  # SECURITY: Disable all built-in functions
                {
                    k: _coerce_value(v) for k, v in self.global_variables.items()
                },  # 暴露context到表达式
            )
        except Exception as e:
            raise ValueError(f"节点{node_name}: 表达式执行错误: {expr}, 错误: {str(e)}")

    async def handle_condition(self, node: TreeNode) -> TreeNode:
        conditions = node.data.get("conditions", [])
        matched = []
        condition_child = []
        condition_pass = []
        child_pass = []
        for idx, cond in conditions.items():
            try:
                if self.safe_eval(cond, node.data["name"], node.node_id):
                    matched.append(int(idx))
                    condition_pass.append(str(idx))
            except Exception as e:
                raise ValueError(
                    f"{node.node_id}: 节点{node.data['name']}: 条件表达式错误: {cond} \n {e}"
                )

        if len(matched) == 0:
            # raise ValueError(f"节点 {node.node_id} 条件表达式错误, 找不到出口")
            pass

        for child in node.children:
            if child.condition in matched:
                condition_child.append(child)
                child_pass.append(str(child.condition))
            else:
                self.skip_nodes.append(child.node_id)

        if len(child_pass) == 0:
            result_connection_index = "No Connection Passed!"
        else:
            result_connection_index = "Passed Connection Index: " + " ".join(child_pass)
        if len(condition_pass) == 0:
            result_condition_index = ("No Condition Passed!",)
        else:
            result_condition_index = (
                "Passed Condition Index: " + " ".join(condition_pass),
            )
        if not node.node_id in self.context:
            self.context[node.node_id] = [
                {
                    "result": result_connection_index,
                    "condition_child": result_condition_index,
                }
            ]
            self._total_context_entries += 1
        else:
            self.context[node.node_id].append(
                {
                    "result": result_connection_index,
                    "condition_child": result_condition_index,
                }
            )
            self._total_context_entries += 1
        self._cleanup_context_if_needed()

        return condition_child

    async def _set_loop_node_execution_status(
        self, node: TreeNode, status: bool = False
    ):
        self.execution_status[node.node_id] = status
        await self._update_node_status(node.node_id, status)
        for child in node.children:
            await self._set_loop_node_execution_status(child, status)

    async def handle_loop(self, node: TreeNode):
        if not node.node_id in self.loop_index:
            self.loop_index[node.node_id] = 0
        if len(node.loop_last) == 0:
            raise ValueError(
                f"{node.node_id}: 节点{node.data['name']}: 循环节点没有loop_next出口"
            )
        loop_type = node.data["loopType"]
        loop_info = node.loop_info
        if len(loop_info) != 1:
            raise ValueError(
                f"{node.node_id}: 节点{node.data['name']}: 循环节点只能有一个loop_body入口"
            )

        loop_node = loop_info[0]
        if loop_type == "count":
            maxCount = node.data["maxCount"]
            # while node.loop_index < int(maxCount):
            # 执行状态设为false保证可以循环
            if self.loop_index[node.node_id] < int(maxCount):
                await self._set_loop_node_execution_status(loop_node)
                await self.execute_workflow(loop_node)
            else:
                self.execution_status[node.node_id] = True
                await self._update_node_status(node.node_id, True)
                for child in node.children:
                    await self.execute_workflow(child)
                return

        elif loop_type == "condition":
            condition = node.data["condition"]
            if condition:
                if self.safe_eval(condition, node.data["name"], node.node_id):
                    logger.info(
                        f"工作流 {self.task_id} ->节点 {node.node_id} 通过条件判断终止"
                    )
                    self.execution_status[node.node_id] = True
                    await self._update_node_status(node.node_id, True)
                    for child in node.children:
                        await self.execute_workflow(child)
                    return

            if self.loop_index[node.node_id] < LOOP_LIMITS["condition"]:
                await self._set_loop_node_execution_status(loop_node)
                await self.execute_workflow(loop_node)
                # if self.safe_eval(condition, node.data["name"], node.node_id):
                #     break
        else:
            raise ValueError(f"{node.node_id}: 节点{node.data['name']}: 未知的循环类型")

    async def execute_workflow(self, node: TreeNode):
        """
        递归运行节点
        """
        logger.info(f"工作流 {self.task_id} 执行节点{node.node_id} 开始运行")
        await self.check_cancellation()

        if node.node_id not in self.execution_status:
            logger.error(f"工作流 {self.task_id} 找不到开始节点！")
            raise ValueError("'Start Node' no found!")

        if self.execution_status[node.node_id]:
            logger.info(f"工作流 {self.task_id} 节点 {node.node_id} 已经运行过了")
            return
        # 等待父节点执行完
        for parent in node.parents:
            if not self.execution_status[parent.node_id]:
                return

        # 检查condition的子节点是否不满足条件跳过
        if node.node_id in self.skip_nodes:
            self.execution_status[node.node_id] = True
            # tasks = []
            for child in node.children:
                self.skip_nodes.append(child.node_id)
                await self.execute_workflow(child)
            #     task = asyncio.create_task(self.execute_workflow(child))
            #     tasks.append(task)
            # await asyncio.wait(tasks)
            if node.loop_parent:
                if node in node.loop_parent.loop_last:
                    if all(
                        self.execution_status[last_loop_node.node_id]
                        for last_loop_node in node.loop_parent.loop_last
                    ):
                        self.skip_nodes = [
                            node_id
                            for node_id in self.skip_nodes
                            if not any(
                                node_id == node.node_id
                                for node in node.loop_parent.loop_children
                            )
                        ]
                        self.loop_index[node.loop_parent.node_id] += 1

                        # Checkpoint after loop iteration completes
                        if CHECKPOINT_CONFIG["on_loop_complete"]:
                            await self.checkpoint_manager.save_checkpoint(reason="loop_complete")

                        await self.execute_workflow(node.loop_parent)
            return

        # 检查暂停点
        if node.node_id in self.breakpoints:
            if node.debug_skip:
                node.debug_skip = False
            else:
                self.execution_stack.append(node)
                await self._send_pause_event(node)
                self.break_workflow = True
                return

        await self._update_node_status(node.node_id, True, True)

        if node.node_type == "loop":
            await self.handle_loop(node)
            if node.loop_parent:
                if node in node.loop_parent.loop_last:
                    if all(
                        self.execution_status[last_loop_node.node_id]
                        for last_loop_node in node.loop_parent.loop_last
                    ):
                        self.loop_index[node.node_id] = 0
                        self.loop_index[node.loop_parent.node_id] += 1

                        # Checkpoint after loop iteration completes
                        if CHECKPOINT_CONFIG["on_loop_complete"]:
                            await self.checkpoint_manager.save_checkpoint(reason="loop_complete")

                        self.skip_nodes = [
                            node_id
                            for node_id in self.skip_nodes
                            if not any(
                                node_id == node.node_id
                                for node in node.loop_parent.loop_children
                            )
                        ]
                        await self.execute_workflow(node.loop_parent)

        elif node.node_type == "condition":
            pointer_nodes = await self.handle_condition(node)
            self.execution_status[node.node_id] = True
            await self._update_node_status(node.node_id, True)

            # Auto-checkpoint after condition gates for recovery
            if await self.checkpoint_manager.should_checkpoint(node, "condition"):
                await self.checkpoint_manager.save_checkpoint(reason="gate")

            # 异步执行子节点
            # tasks = []
            # to do check
            # for child in pointer_nodes:
            for child in node.children:
                await self.execute_workflow(child)
            #     task = asyncio.create_task(self.execute_workflow(child))
            #     tasks.append(task)
            # await asyncio.wait(tasks)
        else:
            # Create checkpoint before executing node for rollback capability
            await self.checkpoint_manager.save_checkpoint(reason="before_node")

            try:
                result = await self.execute_node(node)
                if not result:
                    return
                self.execution_status[node.node_id] = True
                await self._update_node_status(node.node_id, True)

                # Auto-checkpoint after key nodes
                if await self.checkpoint_manager.should_checkpoint(node, "node"):
                    await self.checkpoint_manager.save_checkpoint(reason="after_node")

            except Exception as e:
                # Attempt rollback on error
                logger.error(
                    f"Workflow {self.task_id}: Node {node.node_id} failed: {e}. "
                    f"Attempting rollback..."
                )
                rollback_success = await self.checkpoint_manager.rollback_to_checkpoint()

                if rollback_success:
                    logger.info(f"Workflow {self.task_id}: Rollback successful")
                    # Re-raise after rollback to notify caller
                    raise ValueError(
                        f"Node {node.node_id} failed and rolled back: {str(e)}"
                    )
                else:
                    logger.error(f"Workflow {self.task_id}: Rollback failed")
                    raise

            # 异步执行子节点
            # tasks = []
            for child in node.children:
                await self.execute_workflow(child)
            #     task = asyncio.create_task(self.execute_workflow(child))
            #     tasks.append(task)
            # await asyncio.wait(tasks)
            if node.loop_parent:
                if node in node.loop_parent.loop_last:
                    if all(
                        self.execution_status[last_loop_node.node_id]
                        for last_loop_node in node.loop_parent.loop_last
                    ):
                        self.loop_index[node.loop_parent.node_id] += 1

                        # Checkpoint after loop iteration completes
                        if CHECKPOINT_CONFIG["on_loop_complete"]:
                            await self.checkpoint_manager.save_checkpoint(reason="loop_complete")

                        self.skip_nodes = [
                            node_id
                            for node_id in self.skip_nodes
                            if not any(
                                node_id == node.node_id
                                for node in node.loop_parent.loop_children
                            )
                        ]
                        await self.execute_workflow(node.loop_parent)

    async def _update_node_status(
        self, node_id: str, status: bool, running: bool = False, error: str = ""
    ):
        """更新Redis中节点状态"""
        if self.task_id:
            redis_conn = await redis.get_task_connection()
            await redis_conn.hset(
                f"workflow:{self.task_id}:nodes", node_id, str(int(status))
            )
            # 添加类型标识
            # 发送事件到专用Stream
            if running:
                node_status = "running"
            else:
                node_status = str(int(status))
            await redis_conn.xadd(
                f"workflow:events:{self.task_id}",  # 使用新的事件流键
                {
                    "type": "node",
                    "node": node_id,
                    "status": node_status,
                    "result": json.dumps(self.context.get(node_id, "")),
                    "error": error,
                    "variables": json.dumps(self.global_variables),
                    "create_time": str(beijing_time_now()),
                },
            )
            # 刷新过期时间
            pipeline = redis_conn.pipeline()
            pipeline.expire(f"workflow:{self.task_id}", 3600)
            pipeline.expire(f"workflow:{self.task_id}:nodes", 3600)
            pipeline.expire(f"workflow:events:{self.task_id}", 3600)
            await pipeline.execute()

    async def execute_node(self, node: TreeNode):
        if node.node_type == "code":
            # 执行代码节点
            code = node.data.get("code", "")

            inputs = self.global_variables  # get_node_inputs(node, context)

            try:
                # 1. 代码扫描
                scan_result = self.scanner.scan_code(code)
                if not scan_result["safe"]:
                    raise ValueError(
                        f"{node.node_id}: 节点{node.data['name']}: 代码安全扫描未通过: {scan_result['issues']}"
                    )

                # 2. 沙箱执行
                result = await self.sandbox.execute(
                    code=code,
                    inputs=inputs,
                    pip=node.data.get("pip", None),
                    image_url=node.data.get("imageUrl", ""),
                    remove=node.data.get("remove", False),
                    timeout=node.data.get("timeout", 3600),
                )
                output = result["result"].split("####Global variable updated####")
                code_output = output[0]
                if len(output) > 1:
                    new_global_variables_list = output[1].split("\n\n")[0]
                    updates = {}
                    for equation in new_global_variables_list.split("\n")[1:]:
                        if " = " not in equation:
                            continue
                        key, value = equation.split(" = ", 1)
                        updates[key] = value
                    if updates:
                        self.global_variables.update(updates)
                if not node.node_id in self.context:
                    self.context[node.node_id] = [{"result": code_output}]
                    self._total_context_entries += 1
                else:
                    self.context[node.node_id].append({"result": code_output})
                    self._total_context_entries += 1
                self._cleanup_context_if_needed()
                return True
            except docker.errors.ContainerError as e:
                # logger.error(f"容器执行错误: {e.stderr}")
                raise ValueError(
                    f"{node.node_id}: 节点{node.data['name']}: 容器执行错误: {e.stderr}"
                )  # HTTPException(status_code=400, detail=e.stderr)
            except json.JSONDecodeError:
                raise ValueError(
                    f"{node.node_id}: 节点{node.data['name']}: 输出格式无效,非json格式"
                )  # HTTPException(status_code=400, detail="输出格式无效")
        elif node.node_type == "vlm":
            message_id = str(uuid.uuid4())
            try:
                if node.data["isChatflowInput"]:
                    if node.input_skip:
                        node.input_skip = False
                        vlm_input = self.user_message
                        temp_db_id = self.temp_db_id
                    else:
                        self.execution_stack.append(node)
                        await self._send_pause_event(node, True)
                        self.break_workflow_get_input = True
                        return False
                else:
                    vlm_input = node.data["vlmInput"]
                    temp_db_id = ""
                vlm_input = replace_template(vlm_input, self.global_variables)
                system_prompt = replace_template(
                    node.data["prompt"], self.global_variables
                )

                ##### mcp section #####
                mcp_tools_for_call = {}
                mcp_servers: dict = node.data["mcpUse"]
                if mcp_servers:
                    load_ai_messgae = json.dumps(
                        {
                            "type": "text",
                            "data": "#### Starting MCP call, LLM is selecting tools...  \n",
                            "message_id": message_id,
                        }
                    )
                    await self._send_ai_chunk_event(
                        node.node_id, message_id, load_ai_messgae, "mcp"
                    )
                    logger.info(f"MCP:工作流{self.task_id}开始mcp调用")
                    for mcp_server_name, mcp_server_tools in mcp_servers.items():
                        mcp_server_url = mcp_server_tools.get("mcpServerUrl")
                        mcp_tools = mcp_server_tools.get("mcpTools")
                        mcp_headers = mcp_server_tools.get("headers", None)
                        mcp_timeout = mcp_server_tools.get("timeout", 5)
                        mcp_sse_read_timeout = mcp_server_tools.get(
                            "sseReadTimeout", 60 * 5
                        )
                        for mcp_tool in mcp_tools:
                            mcp_tool["url"] = mcp_server_url
                            mcp_tools_for_call[mcp_tool["name"]] = mcp_tool
                    mcp_prompt = f"""
You are an expert in selecting function calls. Please choose the most appropriate function call based on the user's question and provide the required parameters. Output in JSON format: {{"function_name": function name, "params": parameters}}. Do not include any other content. If the user's question is unrelated to functions, output {{"function_name":""}}.
Here is the JSON function list: {json.dumps(mcp_tools_for_call)}"""
                    mcp_user_message = UserMessage(
                        conversation_id=self.chatflow_id,
                        parent_id="",
                        user_message=vlm_input,
                        temp_db_id=self.temp_db_id,
                    )
                    # 获取流式生成器（使用带熔断和重试的LLM调用）
                    mcp_stream_generator = await self._llm_call_with_retry(
                        user_message_content=mcp_user_message,
                        model_config=node.data["modelConfig"],
                        message_id=message_id,
                        system_prompt=mcp_prompt,
                        save_to_db=False,
                        user_image_urls=[],
                        quote_variables=self.global_variables,
                    )
                    mcp_full_response = []
                    mcp_chunks = []
                    async for chunk in mcp_stream_generator:
                        await self._send_ai_chunk_event(
                            node.node_id, message_id, chunk, "mcp"
                        )
                        mcp_chunks.append(json.loads(chunk))
                    for chunk in mcp_chunks:
                        if chunk.get("type") == "text":
                            mcp_full_response.append(chunk.get("data"))
                    mcp_full_response_json = "".join(mcp_full_response)
                    mcp_outermost_braces_string_list = find_outermost_braces(
                        mcp_full_response_json
                    )
                    try:
                        mcp_outermost_braces_string = mcp_outermost_braces_string_list[
                            -1
                        ]
                        mcp_outermost_braces_dict = json.loads(
                            mcp_outermost_braces_string
                        )
                        function_name = mcp_outermost_braces_dict.get("function_name")
                        if function_name:
                            params = mcp_outermost_braces_dict.get("params")
                            try:
                                result = await mcp_call_tools(
                                    mcp_tools_for_call[function_name]["url"],
                                    function_name,
                                    params,
                                    headers=mcp_headers,
                                    timeout=mcp_timeout,
                                    sse_read_timeout=mcp_sse_read_timeout,
                                )
                                self.supply_info = f"\nPlease answer the question based on these results: {result}"
                                logger.info("MCP:工作流{self.task_id}mcp调用成功")
                                load_ai_messgae = json.dumps(
                                    {
                                        "type": "text",
                                        "data": f"  \n#### MCP call succeeded, returned result:  \n{result}  \n",
                                        "message_id": message_id,
                                    }
                                )
                                await self._send_ai_chunk_event(
                                    node.node_id, message_id, load_ai_messgae, "mcp"
                                )
                            except Exception as e:
                                load_ai_messgae = json.dumps(
                                    {
                                        "type": "text",
                                        "data": f"  \n#### MCP call for function {function_name} with parameters: {params} failed  \n",
                                        "message_id": message_id,
                                    }
                                )
                                await self._send_ai_chunk_event(
                                    node.node_id, message_id, load_ai_messgae, "mcp"
                                )
                                logger.error(
                                    f"MCP:工作流{self.task_id}函数{function_name},参数：{params}的MCP调用失败：{e}"
                                )
                        else:
                            load_ai_messgae = json.dumps(
                                {
                                    "type": "text",
                                    "data": f"  \n#### No suitable MCP call tool found.  \n",
                                    "message_id": message_id,
                                }
                            )
                            await self._send_ai_chunk_event(
                                node.node_id, message_id, load_ai_messgae, "mcp"
                            )
                            logger.info(
                                f"MCP:工作流{self.task_id}未找到合适的MCP调用工具。"
                            )
                    except Exception as e:
                        load_ai_messgae = json.dumps(
                            {
                                "type": "text",
                                "data": f"  \n#### No valid JSON output parsed, please optimize the backend MCP prompt.  \n",
                                "message_id": message_id,
                            }
                        )
                        await self._send_ai_chunk_event(
                            node.node_id, message_id, load_ai_messgae, "mcp"
                        )
                        logger.info(
                            f"MCP:工作流{self.task_id}的MCP调用未解析到json输出：{e}"
                        )
                ##### mcp section #####

                load_ai_messgae = json.dumps(
                    {"type": "text", "data": "", "message_id": message_id}
                )
                await self._send_ai_chunk_event(
                    node.node_id, message_id, load_ai_messgae
                )
                user_message = UserMessage(
                    conversation_id=self.chatflow_id,
                    parent_id=self.parent_id if node.data["useChatHistory"] else "",
                    user_message=vlm_input,
                    temp_db_id=temp_db_id,
                )
                # 获取流式生成器（使用带熔断和重试的LLM调用）
                stream_generator = await self._llm_call_with_retry(
                    user_message_content=user_message,
                    model_config=node.data["modelConfig"],
                    message_id=message_id,
                    system_prompt=system_prompt,
                    save_to_db=True if node.data["isChatflowOutput"] else False,
                    user_image_urls=self.user_image_urls,
                    supply_info=self.supply_info,
                    quote_variables=self.global_variables,
                )
                full_response = []
                chunks = []
                async for chunk in stream_generator:
                    # 发送每个数据块到Redis
                    await self._send_ai_chunk_event(node.node_id, message_id, chunk)
                    # if chunk.get("type") == "text":
                    chunks.append(json.loads(chunk))
                for chunk in chunks:
                    if chunk.get("type") == "text":
                        full_response.append(chunk.get("data"))
                    if chunk.get("type") == "user_images":
                        if node.data["isChatflowInput"]:
                            self.user_image_urls = chunk.get("data")
                full_response_json = "".join(full_response)
                outermost_braces_string_list = find_outermost_braces(full_response_json)
                for outermost_braces_string in outermost_braces_string_list:
                    try:
                        outermost_braces_dict = json.loads(outermost_braces_string)
                        for k, v in outermost_braces_dict.items():
                            if k in self.global_variables:
                                self.global_variables[k] = repr(v)
                    except Exception as e:
                        logger.info(f"LLM:工作流{self.task_id}未解析到json输出：{e}")
                if node.data["chatflowOutputVariable"]:
                    self.global_variables[node.data["chatflowOutputVariable"]] = repr(
                        "".join(full_response)
                    )
                # 以节点ID为键存储完整结果
                if not node.node_id in self.context:
                    self.context[node.node_id] = [{"result": "Message generated!"}]
                    self._total_context_entries += 1
                else:
                    self.context[node.node_id].append({"result": "Message generated!"})
                    self._total_context_entries += 1
                self._cleanup_context_if_needed()
                return True
            except Exception as e:
                # 错误处理
                raise ValueError(f"{node.node_id}:节点{node.data['name']}: {str(e)}")
        else:
            return True

    async def _send_ai_chunk_event(
        self, node_id: str, message_id: str, chunk: str, tool: str = ""
    ):
        if tool:
            message_type = tool
        else:
            message_type = "ai_chunk"
        redis_conn = await redis.get_task_connection()
        event_data = {
            "type": message_type,
            "node_id": node_id,
            "message_id": message_id,
            "data": chunk,
            "create_time": str(beijing_time_now()),
        }
        await redis_conn.xadd(f"workflow:events:{self.task_id}", event_data)

    @llm_service_circuit
    async def _llm_call_with_circuit_breaker(
        self,
        user_message_content,
        model_config: dict,
        message_id: str,
        system_prompt: str,
        save_to_db: bool,
        user_image_urls: list,
        supply_info: str = "",
        quote_variables: dict = None,
    ):
        """
        LLM call wrapped with circuit breaker protection.
        This method is decorated with @llm_service_circuit for fault tolerance.
        """
        # Extract model name to determine timeout
        model_name = model_config.get("model_name", "")
        timeout = get_provider_timeout(model_name)

        logger.info(
            f"Workflow LLM call: model={model_name}, timeout={timeout}s, "
            f"node={message_id}"
        )

        # Create and return the stream generator
        return ChatService.create_chat_stream(
            user_message_content=user_message_content,
            model_config=model_config,
            message_id=message_id,
            system_prompt=system_prompt,
            save_to_db=save_to_db,
            user_image_urls=user_image_urls,
            supply_info=supply_info,
            quote_variables=quote_variables or {},
        )

    async def _llm_call_with_retry(
        self,
        user_message_content,
        model_config: dict,
        message_id: str,
        system_prompt: str,
        save_to_db: bool,
        user_image_urls: list,
        supply_info: str = "",
        quote_variables: dict = None,
    ):
        """
        LLM call with both circuit breaker and retry logic.
        Combines fault tolerance with exponential backoff for transient failures.
        """
        async def _do_call():
            return await self._llm_call_with_circuit_breaker(
                user_message_content=user_message_content,
                model_config=model_config,
                message_id=message_id,
                system_prompt=system_prompt,
                save_to_db=save_to_db,
                user_image_urls=user_image_urls,
                supply_info=supply_info,
                quote_variables=quote_variables,
            )

        return await retry_with_backoff(_do_call, max_retries=3)

    async def start(self, debug_resume=False, input_resume=False):
        """迭代式执行方法"""
        run_times = len(self.execution_stack)
        for i in range(run_times):
            current_node = self.execution_stack.pop(0)
            if debug_resume:
                current_node.debug_skip = True
            if input_resume:
                if current_node.node_id in self.breakpoints:
                    current_node.debug_skip = True
                current_node.input_skip = True
            await self.execute_workflow(current_node)

    async def check_cancellation(self):
        """检查取消状态"""
        redis_conn = await redis.get_task_connection()
        status = await redis_conn.hget(f"workflow:{self.task_id}:operator", "status")
        if status == b"canceling" or status == "canceling":
            logger.error("Workflow canceled by user！")
            await self.cleanup()
            raise ValueError("Workflow canceled")

    async def cleanup(self):
        """清理资源"""
        # 1. 停止沙箱容器
        if self.sandbox:
            await self.sandbox.close()

        # 2. 更新Redis状态
        redis_conn = await redis.get_task_connection()
        await redis_conn.hset(
            f"workflow:{self.task_id}",
            mapping={"status": "canceled", "end_time": str(beijing_time_now())},
        )

        # 发送取消事件
        await redis_conn.xadd(
            f"workflow:events:{self.task_id}",
            {
                "type": "workflow",
                "status": "canceled",
                "result": "",
                "error": "Workflow canceled by user",
                "create_time": str(beijing_time_now()),
            },
        )

        # 3. 清理执行状态
        self.execution_stack.clear()
        self.skip_nodes.clear()

# workflow/workflow_engine.py
import asyncio
import json
from typing import Dict, List, Any, Optional
import docker

from app.db.redis import redis
from app.workflow.sandbox import CodeSandbox
from app.workflow.code_scanner import CodeScanner
from app.workflow.graph import TreeNode, WorkflowGraph


class WorkflowEngine:
    def __init__(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        global_variables,
        start_node="node_start",
        task_id: str = None,
    ):
        self.nodes = nodes
        self.edges = edges
        self.start_node = start_node
        self.global_variables = global_variables
        self.context: Dict[str, Any] = {}
        self.scanner = CodeScanner()
        self.graph = self.get_graph()
        self.execution_status = {node["id"]: False for node in self.nodes}
        # 延迟初始化沙箱
        self.sandbox: Optional[CodeSandbox] = None
        self.task_id = task_id  # Kafka任务id

    async def __aenter__(self):
        # 创建并启动沙箱
        self.sandbox = CodeSandbox()
        await self.sandbox.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # 退出上下文时清理资源
        if self.sandbox:
            # 清理沙箱
            await self.sandbox.__aexit__(exc_type, exc, tb)

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
        """安全执行条件表达式"""
        # 扫描表达式代码
        scan_result = self.scanner.scan_code(expr)
        if not scan_result["safe"]:
            raise ValueError(
                f"{node_id}:节点{node_name}: 不安全的表达式: {expr}, 问题: {scan_result['issues']}"
            )

        # 限制执行环境，仅允许访问context变量
        try:
            return eval(
                expr,
                # {"__builtins__": {int}},  # 禁用内置函数
                {
                    k: (v if v == "" else eval(v))
                    for k, v in self.global_variables.items()
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
                if self.safe_eval(cond, node.data['name'], node.node_id):
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
            for m in matched:
                if child.condition == m:
                    condition_child.append(child)
                    child_pass.append(str(m))
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
        else:
            self.context[node.node_id].append(
                {
                    "result": result_connection_index,
                    "condition_child": result_condition_index,
                }
            )

        return condition_child

    async def _set_loop_node_execution_status(
        self, node: TreeNode, status: bool = False
    ):
        self.execution_status[node.node_id] = status
        await self._update_node_status(node.node_id, status)
        for child in node.children:
            await self._set_loop_node_execution_status(child, status)

    async def handle_loop(self, node: TreeNode):
        loop_type = node.data["loopType"]
        loop_info = node.loop_info
        if loop_info:
            loop_node = loop_info[0]
            if len(loop_info) > 1:
                raise ValueError(
                    f"{node.node_id}: 节点{node.data['name']}: 循环节点只能有一个loop_body入口"
                )
            if loop_type == "count":
                maxCount = node.data["maxCount"]
                for i in range(maxCount):
                    # 执行状态设为false保证可以循环
                    await self._set_loop_node_execution_status(loop_node)
                    await self.execute_workflow(loop_node)
            elif loop_type == "condition":
                condition = node.data["condition"]
                for i in range(100):
                    await self._set_loop_node_execution_status(loop_node)
                    await self.execute_workflow(loop_node, condition)
                    if self.safe_eval(condition, node.data['name'], node.node_id):
                        break
            else:
                raise ValueError(f"{node.node_id}: 节点{node.data['name']}: 未知的循环类型")

    async def execute_workflow(self, node: TreeNode, condition: str = ""):
        """
        递归运行节点
        """

        if condition:
            if self.safe_eval(condition, node.data['name'], node.node_id):
                # print(f"节点 {node.node_id} 通过条件判断终止")
                return
        if self.execution_status[node.node_id]:
            # print(f"节点 {node.node_id} 已经运行过了")
            return
        # 等待父节点执行完
        for parent in node.parents:
            if not self.execution_status[parent.node_id]:
                # print(f"节点 {node.node_id} 的父节点 {parent.node_id} 还未运行")
                return

        if node.node_type == "loop":
            await self.handle_loop(node)
            self.execution_status[node.node_id] = True
            await self._update_node_status(node.node_id, True)
            for child in node.children:
                await self.execute_workflow(child, condition)
        elif node.node_type == "condition":
            pointer_nodes = await self.handle_condition(node)
            self.execution_status[node.node_id] = True
            await self._update_node_status(node.node_id, True)
            # 异步执行子节点
            tasks = []
            for child in pointer_nodes:
                await self.execute_workflow(child, condition)
            #     task = asyncio.create_task(self.execute_workflow(child))
            #     tasks.append(task)
            # await asyncio.wait(tasks)
        else:
            await self.execute_node(node)
            self.execution_status[node.node_id] = True
            await self._update_node_status(node.node_id, True)
            # 异步执行子节点
            tasks = []
            for child in node.children:
                await self.execute_workflow(child, condition)
            #     task = asyncio.create_task(self.execute_workflow(child))
            #     tasks.append(task)
            # await asyncio.wait(tasks)

    async def _update_node_status(self, node_id: str, status: bool):
        """更新Redis中节点状态"""
        if self.task_id:
            redis_conn = await redis.get_task_connection()
            await redis_conn.hset(
                f"workflow:{self.task_id}:nodes", node_id, str(int(status))
            )
            # 添加类型标识
            # 发送事件到专用Stream
            await redis_conn.xadd(
                f"workflow:events:{self.task_id}",  # 使用新的事件流键
                {
                    "type": "node",
                    "node": node_id,
                    "status": str(int(status)),
                    "result": json.dumps(self.context.get(node_id, "")),
                    "error": "",
                },
            )
            # 刷新过期时间
            await redis_conn.expire(f"workflow:{self.task_id}", 3600)
            await redis_conn.expire(f"workflow:{self.task_id}:nodes", 3600)

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
                    timeout=node.data.get("timeout", 60),
                )
                output = result["result"].split("####Global variable updated####")
                code_output = output[0]
                if len(output) > 1:
                    new_global_variables_list = output[1].split("\n\n")[0]
                    self.global_variables = {
                        equation.split(" = ")[0]: equation.split(" = ")[1]
                        for equation in new_global_variables_list.split("\n")[1:]
                    }
            except docker.errors.ContainerError as e:
                # logger.error(f"容器执行错误: {e.stderr}")
                raise ValueError(
                    f"{node.node_id}: 节点{node.data['name']}: 容器执行错误: {e.stderr}"
                )  # HTTPException(status_code=400, detail=e.stderr)
            except json.JSONDecodeError:
                raise ValueError(
                    f"{node.node_id}: 节点{node.data['name']}: 输出格式无效,非json格式"
                )  # HTTPException(status_code=400, detail="输出格式无效")
            if not node.node_id in self.context:
                self.context[node.node_id] = [result]
            else:
                self.context[node.node_id].append(result)
        elif node.node_type == "ai_function":
            result = {"advice": f"模拟调用函数{node.data['function_def']['name']}"}
            # 以节点ID为键存储完整结果
            if not node.node_id in self.context:
                self.context[node.node_id] = [result]
            else:
                self.context[node.node_id].append(result)
        else:
            pass

    async def start(self):
        await self.execute_workflow(self.graph[1])

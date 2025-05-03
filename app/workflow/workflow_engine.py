# workflow/workflow_engine.py
import json
from typing import Dict, List, Any
import docker

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
    ):
        self.nodes = nodes
        self.edges = edges
        self.start_node = start_node
        self.global_variables = global_variables
        self.context: Dict[str, Any] = {}
        self.sandbox = CodeSandbox()
        self.scanner = CodeScanner()
        self.graph = self.get_graph()
        self.execution_status = {node["id"]: False for node in self.nodes}

    def get_graph(self):
        try:
            self.graph = WorkflowGraph(self.nodes, self.edges, self.start_node)
            root = self.graph.root
            msg = "工作流验证通过"
            return (True, root, msg)
        except ValueError as e:
            msg = f"工作流验证失败: {str(e)}"
            return (False, [], msg)

    def safe_eval(self, expr: str, node_id: str) -> bool:
        """安全执行条件表达式"""
        # 扫描表达式代码
        scan_result = self.scanner.scan_code(expr)
        if not scan_result["safe"]:
            raise ValueError(
                f"节点{node_id}: 不安全的表达式: {expr}, 问题: {scan_result['issues']}"
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
            raise ValueError(f"节点{node_id}: 表达式执行错误: {expr}, 错误: {str(e)}")

    async def handle_condition(self, node: TreeNode) -> TreeNode:
        conditions = node.data.get("conditions", [])
        matched = []
        condition_child = []
        condition_pass = []
        child_pass = []
        for idx, cond in conditions.items():
            try:
                if self.safe_eval(cond, node.node_id):
                    matched.append(int(idx))
                    condition_pass.append(str(idx))
            except Exception as e:
                raise ValueError(
                    f"节点 {node.node_id} 条件表达式错误: {cond}, 错误: {e}"
                )

        if len(matched) == 0:
            # raise ValueError(f"节点 {node.node_id} 条件表达式错误, 找不到出口")
            pass

        for child in node.children:
            for m in matched:
                if child.condition == m:
                    condition_child.append(child)
                    child_pass.append(str(matched))
        if len(child_pass) == 0:
            result_connection_index = "No Connection Passed!"
        else:
            result_connection_index = "Passed Connection Index: " + " ".join(child_pass)
        if len(condition_pass) == 0:
            result_condition_index = "No Condition Passed!",
        else:
            result_condition_index = "Passed Condition Index: " + " ".join(condition_pass),
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
        for child in node.children:
            await self._set_loop_node_execution_status(child, status)

    async def handle_loop(self, node: TreeNode):
        loop_type = node.data["loopType"]
        loop_info = node.loop_info
        if loop_info:
            loop_node = loop_info[0]
            if len(loop_info) > 1:
                raise ValueError("循环节点只能有一个loop_body入口")
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
                    if self.safe_eval(condition, node.node_id):
                        break
            else:
                raise ValueError(f"未知的循环类型: {node.node_id}")

    async def execute_workflow(self, node: TreeNode, condition: str = ""):
        """
        递归运行节点
        """

        if condition:
            if self.safe_eval(condition, node.node_id):
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
            for child in node.children:
                await self.execute_workflow(child, condition)
        elif node.node_type == "condition":
            pointer_nodes = await self.handle_condition(node)
            self.execution_status[node.node_id] = True
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
            # 异步执行子节点
            tasks = []
            for child in node.children:
                await self.execute_workflow(child, condition)
            #     task = asyncio.create_task(self.execute_workflow(child))
            #     tasks.append(task)
            # await asyncio.wait(tasks)

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
                        f"节点{node.node_id}: 代码安全扫描未通过: {scan_result['issues']}"
                    )

                # 2. 沙箱执行
                result = await self.sandbox.execute(
                    code=code, inputs=inputs, timeout=node.data.get("timeout", 10)
                )
                output = result["result"].split("####Global variable updated####")
                code_output = output[0]
                if len(output) > 1:
                    new_global_variables_list = output[1]
                    self.global_variables = {
                        equation.split(" = ")[0]: equation.split(" = ")[1]
                        for equation in new_global_variables_list.split("\n")[1:]
                    }
            except docker.errors.ContainerError as e:
                # logger.error(f"容器执行错误: {e.stderr}")
                raise ValueError(
                    f"容器执行错误: {e.stderr}"
                )  # HTTPException(status_code=400, detail=e.stderr)
            except json.JSONDecodeError:
                raise ValueError(
                    f"输出格式无效,非json格式"
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

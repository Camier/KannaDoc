# workflow/executors/code_node_executor.py
import docker
from typing import Dict, Any

from app.workflow.graph import TreeNode
from app.workflow.executors.base_executor import BaseExecutor, NodeResult
from app.workflow.code_scanner import CodeScanner
from app.core.logging import logger


class CodeNodeExecutor(BaseExecutor):
    """Executor for code execution nodes"""

    def __init__(self, *args, scanner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scanner = scanner or CodeScanner()

    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute code node in sandboxed environment.
        """
        code = node.data.get("code", "")
        inputs = self.global_variables

        try:
            # 1. Code security scanning
            scan_result = self.scanner.scan_code(code)
            if not scan_result["safe"]:
                error_msg = (
                    f"{node.node_id}: 节点{node.data['name']}: "
                    f"代码安全扫描未通过: {scan_result['issues']}"
                )
                return NodeResult(success=False, error=error_msg)

            # 2. Sandbox execution
            if not self.sandbox:
                return NodeResult(
                    success=False, error="Sandbox not initialized for code execution"
                )

            result = await self.sandbox.execute(
                code=code,
                inputs=inputs,
                pip=node.data.get("pip", None),
                image_url=node.data.get("imageUrl", ""),
                remove=node.data.get("remove", False),
                timeout=node.data.get("timeout", 3600),
            )

            # 3. Parse output and extract updated variables
            output = result["result"].split("####Global variable updated####")
            code_output = output[0]

            updated_variables = {}
            if len(output) > 1:
                new_global_variables_list = output[1].split("\n\n")[0]
                for equation in new_global_variables_list.split("\n")[1:]:
                    if " = " not in equation:
                        continue
                    key, value = equation.split(" = ", 1)
                    updated_variables[key] = value
                    self.global_variables[key] = value

            # 4. Store context
            self._add_to_context(node.node_id, code_output)

            return NodeResult(
                success=True, output=code_output, updated_variables=updated_variables
            )

        except docker.errors.ContainerError as e:
            error_msg = (
                f"{node.node_id}: 节点{node.data['name']}: 容器执行错误: {e.stderr}"
            )
            return NodeResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"{node.node_id}: 节点{node.data['name']}: 执行错误: {str(e)}"
            return NodeResult(success=False, error=error_msg)

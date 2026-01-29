# workflow/executors/condition_executor.py
from typing import Dict, Any, List
from simpleeval import simple_eval, InvalidExpression

from app.workflow.graph import TreeNode
from app.workflow.executors.base_executor import BaseExecutor, NodeResult
from app.workflow.code_scanner import CodeScanner


class ConditionExecutor(BaseExecutor):
    """Executor for conditional routing nodes"""

    def __init__(self, *args, scanner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scanner = scanner or CodeScanner()

    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute condition node and return matching child nodes.
        """
        conditions = node.data.get("conditions", {})
        matched = []
        condition_pass = []
        child_pass = []

        # Evaluate each condition
        for idx, cond in conditions.items():
            try:
                if self._safe_eval(cond, node.data["name"], node.node_id):
                    matched.append(int(idx))
                    condition_pass.append(str(idx))
            except Exception as e:
                error_msg = (
                    f"{node.node_id}: 节点{node.data['name']}: "
                    f"条件表达式错误: {cond} \n {e}"
                )
                return NodeResult(success=False, error=error_msg)

        # Determine which children to execute
        condition_child = []
        for child in node.children:
            if child.condition in matched:
                condition_child.append(child)
                child_pass.append(str(child.condition))

        # Build result info
        if len(child_pass) == 0:
            result_connection_index = "No Connection Passed!"
        else:
            result_connection_index = "Passed Connection Index: " + " ".join(child_pass)

        if len(condition_pass) == 0:
            result_condition_index = ("No Condition Passed!",)
        else:
            result_condition_index = "Passed Condition Index: " + " ".join(
                condition_pass
            )

        # Store context
        context_data = {
            "result": result_connection_index,
            "condition_child": result_condition_index,
        }
        self._add_to_context(node.node_id, context_data)

        return NodeResult(
            success=True,
            output={
                "matched_children": condition_child,
                "skip_children": [
                    child for child in node.children if child.condition not in matched
                ],
            },
        )

    def _safe_eval(self, expr: str, node_name: str, node_id: str) -> bool:
        """
        Safely evaluate condition expression using simpleeval.
        Replaces eval() for security.
        """
        # Scan expression code
        scan_result = self.scanner.scan_code(expr)
        if not scan_result["safe"]:
            raise ValueError(
                f"{node_id}:节点{node_name}: 不安全的表达式: {expr}, "
                f"问题: {scan_result['issues']}"
            )

        try:
            # Coerce string values to appropriate types
            def _coerce_value(value):
                if isinstance(value, str):
                    if value == "":
                        return ""
                    try:
                        # Try to evaluate as Python literal
                        return eval(value)
                    except Exception:
                        return value
                return value

            # Prepare variables with coercion
            eval_vars = {
                k: _coerce_value(v) for k, v in self.global_variables.items()
            }

            # Use simpleeval for safe evaluation
            result = simple_eval(expr, names=eval_vars)
            return bool(result)

        except InvalidExpression as e:
            raise ValueError(
                f"节点{node_name}: 表达式语法错误: {expr}, 错误: {str(e)}"
            )
        except Exception as e:
            raise ValueError(
                f"节点{node_name}: 表达式执行错误: {expr}, 错误: {str(e)}"
            )

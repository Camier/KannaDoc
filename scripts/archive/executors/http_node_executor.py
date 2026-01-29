# workflow/executors/http_node_executor.py
import httpx
from typing import Dict, Any

from app.workflow.graph import TreeNode
from app.workflow.executors.base_executor import BaseExecutor, NodeResult
from app.workflow.utils import replace_template
from app.core.logging import logger


class HTTPNodeExecutor(BaseExecutor):
    """Executor for HTTP request nodes"""

    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute HTTP request node.
        Supports GET, POST, PUT, DELETE, PATCH methods.
        """
        try:
            # Get request configuration
            method = node.data.get("method", "GET").upper()
            url = node.data.get("url", "")
            headers = node.data.get("headers", {})
            body = node.data.get("body", {})
            timeout = node.data.get("timeout", 30)

            # Replace template variables
            url = replace_template(url, self.global_variables)
            headers = self._replace_dict_templates(headers, self.global_variables)
            body = self._replace_dict_templates(body, self.global_variables)

            # Execute HTTP request
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=body)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=body)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=body)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                elif method == "PATCH":
                    response = await client.patch(url, headers=headers, json=body)
                else:
                    return NodeResult(
                        success=False, error=f"Unsupported HTTP method: {method}"
                    )

                # Parse response
                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                }

                # Try to parse JSON response
                try:
                    result["json"] = response.json()
                except Exception:
                    pass  # Response is not JSON

                # Store response in global variable if configured
                output_variable = node.data.get("outputVariable")
                if output_variable:
                    self.global_variables[output_variable] = str(result)

                # Store context
                self._add_to_context(node.node_id, result)

                return NodeResult(success=True, output=result)

        except httpx.TimeoutException:
            error_msg = f"{node.node_id}: HTTP请求超时: {url}"
            return NodeResult(success=False, error=error_msg)
        except httpx.HTTPError as e:
            error_msg = f"{node.node_id}: HTTP请求错误: {str(e)}"
            return NodeResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"{node.node_id}: 节点{node.data['name']}: {str(e)}"
            return NodeResult(success=False, error=error_msg)

    def _replace_dict_templates(
        self, data: Dict[str, Any], variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Replace template variables in dictionary values"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = replace_template(value, variables)
            elif isinstance(value, dict):
                result[key] = self._replace_dict_templates(value, variables)
            elif isinstance(value, list):
                result[key] = [
                    replace_template(item, variables) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

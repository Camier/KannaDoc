# workflow/executors/vlm_node_executor.py
import json
import uuid
from typing import Dict, Any

from app.workflow.graph import TreeNode
from app.workflow.executors.base_executor import BaseExecutor, NodeResult
from app.core.llm import ChatService
from app.models.workflow import UserMessage
from app.workflow.mcp_tools import mcp_call_tools
from app.workflow.utils import find_outermost_braces, replace_template
from app.core.logging import logger
from app.workflow.components.llm_client import LLMClient


class VLMNodeExecutor(BaseExecutor):
    """Executor for VLM (Vision Language Model) nodes"""

    def __init__(
        self,
        global_variables: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        chatflow_id: str,
        parent_id: str,
        temp_db_id: str,
        user_message: str,
        user_image_urls: list,
        send_event_callback,
        sandbox=None,
        llm_client=None,
    ):
        super().__init__(global_variables, context, sandbox, task_id)
        self.chatflow_id = chatflow_id
        self.parent_id = parent_id
        self.temp_db_id = temp_db_id
        self.user_message = user_message
        self.user_image_urls = user_image_urls
        self.send_event_callback = send_event_callback
        self.supply_info = ""

        # Import LLMClient to avoid circular dependency
        from app.workflow.components import LLMClient

        self.llm_client = llm_client or LLMClient()

    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute VLM node with MCP tool support and streaming response.
        """
        message_id = str(uuid.uuid4())

        try:
            # Handle input collection
            vlm_input, temp_db_id = await self._get_vlm_input(node)

            # Replace template variables
            vlm_input = replace_template(vlm_input, self.global_variables)
            system_prompt = replace_template(node.data["prompt"], self.global_variables)

            # Execute MCP tool calls if configured
            await self._execute_mcp_tools(node, vlm_input, message_id)

            # Execute main VLM chat
            await self._send_initial_event(node.node_id, message_id)
            full_response = await self._execute_vlm_chat(
                node, vlm_input, system_prompt, temp_db_id, message_id
            )

            # Parse and update variables from response
            self._update_variables_from_response(node, full_response)

            # Store output variable if configured
            self._store_output_variable(node, full_response)

            # Store context
            self._add_to_context(node.node_id, "Message generated!")

            return NodeResult(success=True, output="Message generated!")

        except Exception as e:
            return NodeResult(success=False, error=str(e))

    async def _get_vlm_input(self, node: TreeNode):
        """Get VLM input, handling chatflow input nodes"""
        if node.data["isChatflowInput"]:
            if node.input_skip:
                node.input_skip = False
                return self.user_message, self.temp_db_id
            else:
                # Signal that we need user input
                return None, None  # Caller should handle this
        else:
            return node.data["vlmInput"], ""

    async def _execute_mcp_tools(self, node: TreeNode, vlm_input: str, message_id: str):
        """Execute MCP tool calls if configured"""
        mcp_servers: dict = node.data.get("mcpUse", {})
        if not mcp_servers:
            return

        mcp_tools_for_call = {}
        mcp_headers = None
        mcp_timeout = 5
        mcp_sse_read_timeout = 300

        # Collect MCP tools
        for mcp_server_name, mcp_server_tools in mcp_servers.items():
            mcp_server_url = mcp_server_tools.get("mcpServerUrl")
            mcp_tools = mcp_server_tools.get("mcpTools")
            mcp_headers = mcp_server_tools.get("headers", None)
            mcp_timeout = mcp_server_tools.get("timeout", 5)
            mcp_sse_read_timeout = mcp_server_tools.get("sseReadTimeout", 60 * 5)

            for mcp_tool in mcp_tools:
                mcp_tool["url"] = mcp_server_url
                mcp_tools_for_call[mcp_tool["name"]] = mcp_tool

        # Use LLM to select tool
        mcp_prompt = f"""
You are an expert in selecting function calls. Please choose the most appropriate function call based on the user's question and provide the required parameters. Output in JSON format: {{"function_name": function name, "params": parameters}}. Do not include any other content. If the user's question is unrelated to functions, output {{"function_name":""}}.
Here is the JSON function list: {json.dumps(mcp_tools_for_call)}"""

        await self._send_mcp_start_event(node.node_id, message_id)
        logger.info(f"MCP:工作流{self.task_id}开始mcp调用")

        # Get tool selection from LLM
        mcp_user_message = UserMessage(
            conversation_id=self.chatflow_id,
            parent_id="",
            user_message=vlm_input,
            temp_db_id=self.temp_db_id,
        )

        mcp_stream_generator = ChatService.create_chat_stream(
            user_message_content=mcp_user_message,
            model_config=node.data["modelConfig"],
            message_id=message_id,
            system_prompt=mcp_prompt,
            save_to_db=False,
            user_image_urls=[],
            quote_variables=self.global_variables,
            is_workflow=True,
        )

        mcp_full_response = []
        mcp_chunks = []
        async for chunk in mcp_stream_generator:
            await self.send_event_callback(node.node_id, message_id, chunk, "mcp")
            mcp_chunks.append(json.loads(chunk))

        for chunk in mcp_chunks:
            if chunk.get("type") == "text":
                mcp_full_response.append(chunk.get("data"))

        # Parse and execute tool
        await self._parse_and_execute_mcp_tool(
            node,
            message_id,
            mcp_full_response,
            mcp_tools_for_call,
            mcp_headers,
            mcp_timeout,
            mcp_sse_read_timeout,
        )

    async def _send_mcp_start_event(self, node_id: str, message_id: str):
        """Send MCP start event"""
        load_ai_message = json.dumps(
            {
                "type": "text",
                "data": "#### Starting MCP call, LLM is selecting tools...  \n",
                "message_id": message_id,
            }
        )
        await self.send_event_callback(node_id, message_id, load_ai_message, "mcp")

    async def _parse_and_execute_mcp_tool(
        self,
        node: TreeNode,
        message_id: str,
        mcp_full_response: list,
        mcp_tools_for_call: dict,
        mcp_headers,
        mcp_timeout: int,
        mcp_sse_read_timeout: int,
    ):
        """Parse LLM response and execute MCP tool"""
        mcp_full_response_json = "".join(mcp_full_response)
        mcp_outermost_braces_string_list = find_outermost_braces(mcp_full_response_json)

        try:
            mcp_outermost_braces_string = mcp_outermost_braces_string_list[-1]
            mcp_outermost_braces_dict = json.loads(mcp_outermost_braces_string)
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
                    self.supply_info = (
                        f"\nPlease answer the question based on these results: {result}"
                    )
                    logger.info(f"MCP:工作流{self.task_id}mcp调用成功")

                    load_ai_message = json.dumps(
                        {
                            "type": "text",
                            "data": f"  \n#### MCP call succeeded, returned result:  \n{result}  \n",
                            "message_id": message_id,
                        }
                    )
                    await self.send_event_callback(
                        node.node_id, message_id, load_ai_message, "mcp"
                    )
                except Exception as e:
                    load_ai_message = json.dumps(
                        {
                            "type": "text",
                            "data": f"  \n#### MCP call for function {function_name} with parameters: {params} failed  \n",
                            "message_id": message_id,
                        }
                    )
                    await self.send_event_callback(
                        node.node_id, message_id, load_ai_message, "mcp"
                    )
                    logger.error(
                        f"MCP:工作流{self.task_id}函数{function_name},参数：{params}的MCP调用失败：{e}"
                    )
            else:
                load_ai_message = json.dumps(
                    {
                        "type": "text",
                        "data": f"  \n#### No suitable MCP call tool found.  \n",
                        "message_id": message_id,
                    }
                )
                await self.send_event_callback(
                    node.node_id, message_id, load_ai_message, "mcp"
                )
                logger.info(f"MCP:工作流{self.task_id}未找到合适的MCP调用工具。")
        except Exception as e:
            load_ai_message = json.dumps(
                {
                    "type": "text",
                    "data": f"  \n#### No valid JSON output parsed, please optimize the backend MCP prompt.  \n",
                    "message_id": message_id,
                }
            )
            await self.send_event_callback(
                node.node_id, message_id, load_ai_message, "mcp"
            )
            logger.info(f"MCP:工作流{self.task_id}的MCP调用未解析到json输出：{e}")

    async def _send_initial_event(self, node_id: str, message_id: str):
        """Send initial AI chunk event"""
        load_ai_message = json.dumps(
            {"type": "text", "data": "", "message_id": message_id}
        )
        await self.send_event_callback(node_id, message_id, load_ai_message)

    async def _execute_vlm_chat(
        self,
        node: TreeNode,
        vlm_input: str,
        system_prompt: str,
        temp_db_id: str,
        message_id: str,
    ) -> str:
        """Execute main VLM chat and return full response"""
        user_message = UserMessage(
            conversation_id=self.chatflow_id,
            parent_id=self.parent_id if node.data["useChatHistory"] else "",
            user_message=vlm_input,
            temp_db_id=temp_db_id,
        )

        # Use LLMClient with retry and circuit breaker
        stream_generator = await self.llm_client.call_with_retry(
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
            await self.send_event_callback(node.node_id, message_id, chunk)
            chunks.append(json.loads(chunk))

        for chunk in chunks:
            if chunk.get("type") == "text":
                full_response.append(chunk.get("data"))
            if chunk.get("type") == "user_images":
                if node.data["isChatflowInput"]:
                    self.user_image_urls = chunk.get("data")

        return "".join(full_response)

    def _update_variables_from_response(self, node: TreeNode, full_response: str):
        """Parse JSON from response and update global variables"""
        outermost_braces_string_list = find_outermost_braces(full_response)
        for outermost_braces_string in outermost_braces_string_list:
            try:
                outermost_braces_dict = json.loads(outermost_braces_string)
                for k, v in outermost_braces_dict.items():
                    if k in self.global_variables:
                        self.global_variables[k] = repr(v)
            except Exception as e:
                logger.info(f"LLM:工作流{self.task_id}未解析到json输出：{e}")

    def _store_output_variable(self, node: TreeNode, full_response: str):
        """Store output variable if configured"""
        if node.data.get("chatflowOutputVariable"):
            self.global_variables[node.data["chatflowOutputVariable"]] = repr(
                full_response
            )

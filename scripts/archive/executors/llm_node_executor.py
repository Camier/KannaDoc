# workflow/executors/llm_node_executor.py
import json
import uuid
from typing import Dict, Any

from app.workflow.graph import TreeNode
from app.workflow.executors.base_executor import BaseExecutor, NodeResult
from app.core.llm import ChatService
from app.models.workflow import UserMessage
from app.workflow.utils import find_outermost_braces, replace_template
from app.core.logging import logger
from app.workflow.components import LLMClient


class LLMNodeExecutor(BaseExecutor):
    """Executor for LLM (text-only) nodes"""

    def __init__(
        self,
        global_variables: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        chatflow_id: str,
        parent_id: str,
        temp_db_id: str,
        user_message: str,
        send_event_callback,
        sandbox=None,
        llm_client=None,
    ):
        super().__init__(global_variables, context, sandbox, task_id)
        self.chatflow_id = chatflow_id
        self.parent_id = parent_id
        self.temp_db_id = temp_db_id
        self.user_message = user_message
        self.send_event_callback = send_event_callback

        # Import LLMClient to avoid circular dependency
        from app.workflow.components.llm_client import LLMClient

        self.llm_client = llm_client or LLMClient()

    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute LLM node with streaming response.
        LLM nodes are similar to VLM nodes but don't handle images.
        """
        from app.workflow.utils import find_outermost_braces

        message_id = str(uuid.uuid4())

        try:
            # Get input
            llm_input = node.data.get("llmInput", "")
            llm_input = replace_template(llm_input, self.global_variables)

            # Get system prompt
            system_prompt = replace_template(
                node.data.get("prompt", ""), self.global_variables
            )

            # Send initial event
            load_ai_message = json.dumps(
                {"type": "text", "data": "", "message_id": message_id}
            )
            await self.send_event_callback(node.node_id, message_id, load_ai_message)

            # Create user message
            user_message = UserMessage(
                conversation_id=self.chatflow_id,
                parent_id=self.parent_id
                if node.data.get("useChatHistory", False)
                else "",
                user_message=llm_input,
                temp_db_id=self.temp_db_id,
            )

            # Execute LLM chat with retry and circuit breaker
            stream_generator = await self.llm_client.call_with_retry(
                user_message_content=user_message,
                model_config=node.data["modelConfig"],
                message_id=message_id,
                system_prompt=system_prompt,
                save_to_db=node.data.get("isChatflowOutput", False),
                user_image_urls=[],
                supply_info="",
                quote_variables=self.global_variables,
            )

            # Collect response
            full_response = []
            chunks = []
            async for chunk in stream_generator:
                await self.send_event_callback(node.node_id, message_id, chunk)
                chunks.append(json.loads(chunk))

            for chunk in chunks:
                if chunk.get("type") == "text":
                    full_response.append(chunk.get("data"))

            full_response_json = "".join(full_response)

            # Parse and update variables from response
            outermost_braces_string_list = find_outermost_braces(full_response_json)
            for outermost_braces_string in outermost_braces_string_list:
                try:
                    outermost_braces_dict = json.loads(outermost_braces_string)
                    for k, v in outermost_braces_dict.items():
                        if k in self.global_variables:
                            self.global_variables[k] = repr(v)
                except Exception as e:
                    logger.info(f"LLM:工作流{self.task_id}未解析到json输出：{e}")

            # Store output variable if configured
            if node.data.get("chatflowOutputVariable"):
                self.global_variables[node.data["chatflowOutputVariable"]] = repr(
                    full_response_json
                )

            # Store context
            self._add_to_context(node.node_id, "Message generated!")

            return NodeResult(success=True, output="Message generated!")

        except Exception as e:
            return NodeResult(success=False, error=str(e))

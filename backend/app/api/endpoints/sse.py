import asyncio
import json
import re
import aioredis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.core.security import get_current_user, verify_username_match
from app.db.redis import redis
from app.models.conversation import UserMessage
from app.models.workflow import UserMessage as WorkflowMessage
from app.models.user import User
from app.models.workflow import LLMInputOnce
from app.rag.llm_service import ChatService
from app.workflow.llm_service import ChatService as VLMService
import uuid

from app.workflow.mcp_tools import mcp_call_tools

router = APIRouter()


# 创建新会话
@router.post("/chat", response_model=dict)
async def chat_stream(
    user_message: UserMessage,
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(
        current_user, user_message.conversation_id.split("_")[0]
    )

    message_id = str(uuid.uuid4())  # 生成 UUIDv4

    return StreamingResponse(
        ChatService.create_chat_stream(user_message, message_id),
        media_type="text/event-stream",
        headers={"conversation-id": user_message.conversation_id},
    )


# SSE进度查询接口
@router.get("/task/{username}/{task_id}")
async def get_task_progress(
    task_id: str,
    username: str,
    current_user: User = Depends(get_current_user),
):

    # 验证当前用户是否与要删除的用户名匹配
    await verify_username_match(current_user, username)
    redis_connection = await redis.get_task_connection()

    async def event_generator():
        retries = 5
        while retries > 0:
            task_data = await redis_connection.hgetall(f"task:{task_id}")
            if not task_data:
                retries -= 1
                await asyncio.sleep(1)
                continue

            status = task_data.get("status", "unknown")
            total = int(task_data.get("total", 0))
            processed = int(task_data.get("processed", 0))
            message = task_data.get("message", "")

            payload = json.dumps(
                {
                    "event": "progress",
                    "status": status,
                    "progress": f"{(processed/total)*100:.1f}" if total > 0 else 0,
                    "processed": processed,
                    "total": total,
                    "message": message,
                }
            )
            yield f"{payload}"  # 保持SSE事件标准分隔符
            if status in ["completed", "failed"]:
                break

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


from fastapi import Depends, Query
from aioredis import Redis, ResponseError


@router.get("/workflow/{username}/{task_id}")
async def workflow_sse(
    task_id: str,
    username: str,
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, username)

    def _parse_message(parsed_msg: dict) -> dict:
        if parsed_msg.get("type") == "node":
            return {
                "event": "node",
                "node": {
                    "id": parsed_msg["node"],
                    "status": (
                        parsed_msg["status"]
                        if parsed_msg["status"]
                        in ["pause", "running", "vlm_input", "vlm_input_debug"]
                        else parsed_msg["status"] == "1"
                    ),
                    "result": parsed_msg.get("result"),
                    "error": parsed_msg.get("error"),
                    "variables": parsed_msg.get("variables"),
                    "create_time": parsed_msg.get("create_time"),
                },
            }
        elif parsed_msg.get("type") == "workflow":
            return {
                "event": "workflow",
                "workflow": {
                    "status": parsed_msg["status"],
                    "result": parsed_msg.get("result"),
                    "error": parsed_msg.get("error"),
                    "create_time": parsed_msg.get("create_time"),
                },
            }
        elif parsed_msg.get("type") == "ai_chunk":
            return {
                "event": "ai_chunk",
                "ai_chunk": {
                    "id": parsed_msg.get("node_id"),
                    "message_id": parsed_msg.get("message_id"),
                    "result": parsed_msg.get("data"),
                    "create_time": parsed_msg.get("create_time"),
                },
            }
        elif parsed_msg.get("type") == "mcp":
            return {
                "event": "mcp",
                "ai_chunk": {
                    "id": parsed_msg.get("node_id"),
                    "message_id": parsed_msg.get("message_id"),
                    "result": parsed_msg.get("data"),
                    "create_time": parsed_msg.get("create_time"),
                },
            }

    async def event_stream():
        redis_conn: Redis = await redis.get_task_connection()
        event_stream_key = f"workflow:events:{task_id}"
        workflow_key = f"workflow:{task_id}"
        consumer_group = "workflow_group"
        consumer_name = "sse_consumer"  # 可固定或动态生成（如客户端ID）

        # 初始化 Consumer Group（仅需创建一次）
        try:
            await redis_conn.xgroup_create(
                event_stream_key, consumer_group, id="0", mkstream=True
            )
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        # 初始状态检查（避免处理已完成的流程）
        workflow_status = await redis_conn.hget(workflow_key, "status")
        if workflow_status and workflow_status in (
            "completed",
            "failed",
            "pause",
            "canceled",
            "vlm_input",
        ):
            yield {
                "data": json.dumps(
                    {
                        "event": "workflow",
                        "workflow": {
                            "status": workflow_status,
                            "result": await redis_conn.hget(workflow_key, "result"),
                            "error": await redis_conn.hget(workflow_key, "error"),
                        },
                    }
                )
            }
            return

        while True:
            try:
                # 从 Stream 中读取未确认的消息
                messages = await redis_conn.xreadgroup(
                    groupname=consumer_group,
                    consumername=consumer_name,
                    streams={event_stream_key: ">"},  # ">" 表示只读新消息
                    count=10,
                    block=5000,
                    noack=False,  # 需要手动确认消息
                )
            except ResponseError as e:
                if "NOGROUP" in str(e):
                    # 组不存在时重新创建（防止意外删除）
                    await redis_conn.xgroup_create(
                        event_stream_key, consumer_group, id="0", mkstream=True
                    )
                    continue
                raise

            # 无新消息时继续等待
            if not messages:
                continue

            for stream_name, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    # 解析消息内容
                    parsed_msg = {k: v for k, v in msg_data.items()}
                    response_data = _parse_message(parsed_msg)

                    # 返回事件数据
                    if response_data:
                        yield {"data": json.dumps(response_data)}

                    # 消息处理完成后确认（ACK）
                    await redis_conn.xack(event_stream_key, consumer_group, msg_id)

                    # 如果工作流终止，结束连接
                    if response_data.get("event") == "workflow" and parsed_msg[
                        "status"
                    ] in ("completed", "failed", "pause", "canceled", "vlm_input"):
                        return

    return EventSourceResponse(event_stream())


# 创建workflow llm模型
@router.post("/llm/once", response_model=dict)
async def chat_stream(
    llm_input: LLMInputOnce,
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, llm_input.username)
    supply_info = ""
    message_id = str(uuid.uuid4())  # 生成 UUIDv4
    def render_template(template: str, data: dict) -> str:
        """
        将模板中的 {{ variable }} 替换为字典中对应的字符串值
        :param template: 包含 {{ 变量 }} 的模板字符串
        :param data: 包含键值对的字典
        :return: 替换后的字符串
        """
        pattern = re.compile(r"\{\{\s*(.*?)\s*\}\}")  # 自动处理变量名前后空格
        return pattern.sub(lambda m: str(data.get(m.group(1), "")), template)
    vlm_input = render_template(llm_input.user_message, llm_input.global_variables)

    ##### mcp section #####
    mcp_tools_for_call = {}
    mcp_servers: dict = llm_input.mcp_use
    if mcp_servers:
        for mcp_server_name, mcp_server_tools in mcp_servers.items():
            mcp_server_url = mcp_server_tools.get("mcpServerUrl")
            mcp_tools = mcp_server_tools.get("mcpTools")
            for mcp_tool in mcp_tools:
                mcp_tool["url"] = mcp_server_url
                mcp_tools_for_call[mcp_tool["name"]] = mcp_tool
        mcp_prompt = f"""
你是一个选择函数调用的专家，请根据用户提问帮用户选择最合适的一个函数调用，并给出函数所需的参数，以{{"function_name":函数名，"params":参数}}的json格式输出，如果用户提问与函数无关，请输出{{"function_name":""}}
这是json格式的函数列表：{json.dumps(mcp_tools_for_call)}"""
        mcp_user_message = WorkflowMessage(
            conversation_id="",
            parent_id="",
            user_message=vlm_input,
            temp_db_id="",
        )
        # 获取流式生成器（假设返回结构化数据块）
        mcp_stream_generator = VLMService.create_chat_stream(
            user_message_content=mcp_user_message,
            model_config=llm_input.llm_model_config,
            message_id=message_id,
            system_prompt=mcp_prompt,
            save_to_db=False,
            user_image_urls=[],
        )
        mcp_full_response = []
        mcp_chunks = []
        async for chunk in mcp_stream_generator:
            mcp_chunks.append(json.loads(chunk))
        for chunk in mcp_chunks:
            if chunk.get("type") == "text":
                mcp_full_response.append(chunk.get("data"))
        try:
            mcp_full_response_json = json.loads("".join(mcp_full_response))
            function_name = mcp_full_response_json.get("function_name")
            if function_name:
                params = mcp_full_response_json.get("params")
                try:
                    result = await mcp_call_tools(
                        mcp_tools_for_call[function_name]["url"],
                        function_name,
                        params,
                    )
                    supply_info = f"\n请根据这些结果回答问题{result}"
                except Exception as e:
                    pass
            else:
                pass
        except Exception as e:
            pass
    ##### mcp section #####

    user_message = WorkflowMessage(
        conversation_id="",
        parent_id="",
        user_message=vlm_input + supply_info,
        temp_db_id="",
    )

    return EventSourceResponse(
        VLMService.create_chat_stream(
            user_message,
            llm_input.llm_model_config,
            message_id,
            llm_input.system_prompt,
        ),
        media_type="text/event-stream",
        headers={"message-id": message_id},
    )

# services/chat_service.py
import asyncio
import json
from typing import AsyncGenerator
from app.db.mongo import get_mongo
from app.models.conversation import UserMessage
from openai import AsyncOpenAI

from app.rag.mesage import find_depth_parent_mesage
from app.core.logging import logger
from app.db.vector_db import vector_db_client
from app.rag.get_embedding import get_embeddings_from_httpx
from app.rag.utils import replace_image_content, sort_and_filter
from app.rag.provider_client import get_llm_client
from app.core.circuit_breaker import llm_service_circuit


class ChatService:
    @staticmethod
    def _normalize_multivector(emb):
        """
        Returns List[List[float]] shaped (n_tokens, dim)
        Accepts:
          - List[List[float]]                     -> as-is
          - List[ List[List[float]] ] with len=1  -> emb[0]
          - List[float]                           -> [emb]
        """
        if not isinstance(emb, list):
            raise TypeError(f"Unexpected embedding type: {type(emb)}")

        if len(emb) == 0:
            return []

        # Case: list-of-embeddings for each input text, single input
        if (
            len(emb) == 1
            and isinstance(emb[0], list)
            and emb[0]
            and isinstance(emb[0][0], list)
        ):
            emb = emb[0]

        # Case: single vector
        if emb and isinstance(emb[0], (float, int)):
            return [[float(x) for x in emb]]

        # Case: multivector
        if emb and isinstance(emb[0], list):
            return [[float(x) for x in v] for v in emb]

        raise TypeError("Unexpected embedding structure")

    @staticmethod
    async def create_chat_stream(
        user_message_content: UserMessage, message_id: str
    ) -> AsyncGenerator[str, None]:
        """创建聊天流并处理存储逻辑"""
        db = await get_mongo()

        # 获取system prompt
        model_config = await db.get_conversation_model_config(
            user_message_content.conversation_id
        )

        model_name = model_config["model_name"]
        model_url = model_config["model_url"]
        api_key = model_config["api_key"]
        base_used = model_config["base_used"]

        system_prompt = model_config["system_prompt"]
        if len(system_prompt) > 1048576:
            system_prompt = system_prompt[0:1048576]

        temperature = model_config["temperature"]
        if temperature < 0 and not temperature == -1:
            temperature = 0
        elif temperature > 1:
            temperature = 1
        else:
            pass

        max_length = model_config["max_length"]
        if max_length < 1024 and not max_length == -1:
            max_length = 1024
        elif max_length > 1048576:
            max_length = 1048576
        else:
            pass

        top_P = model_config["top_P"]
        if top_P < 0 and not top_P == -1:
            top_P = 0
        elif top_P > 1:
            top_P = 1
        else:
            pass

        top_K = model_config["top_K"]
        if top_K == -1:
            top_K = 3
        elif top_K < 1:
            top_K = 1
        elif top_K > 30:
            top_K = 30
        else:
            pass

        score_threshold = model_config["score_threshold"]
        if score_threshold == -1:
            score_threshold = 10
        elif score_threshold < 0:
            score_threshold = 0
        elif score_threshold > 20:
            score_threshold = 20
        else:
            pass

        if not system_prompt:
            messages = []
        else:
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            # "text": "You are LAYRA, developed by Li Wei(李威), a multimodal RAG tool built on ColQwen and Qwen2.5-VL-72B. The retrieval process relies entirely on vision, enabling accurate recognition of tables, images, and documents in various formats. All outputs in Markdown format.",
                            "text": system_prompt,
                        }
                    ],
                }
            ]
            logger.info(
                f"chat '{user_message_content.conversation_id} uses system prompt {system_prompt}'"
            )

        history_messages = await find_depth_parent_mesage(
            user_message_content.conversation_id,
            user_message_content.parent_id,
            MAX_PARENT_DEPTH=5,
        )

        for i in range(len(history_messages), 0, -1):
            messages.append(history_messages[i - 1])

        # 处理用户上传的文件
        content = []
        bases = []
        if user_message_content.temp_db:
            bases.append({"baseId": user_message_content.temp_db})

        # 搜索知识库匹配内容

        bases.extend(base_used)
        file_used = []
        if bases:
            result_score = []
            query_embedding = await get_embeddings_from_httpx(
                [user_message_content.user_message], endpoint="embed_text"
            )
            query_vecs = ChatService._normalize_multivector(query_embedding)
            for base in bases:
                collection_name = f"colqwen{base['baseId'].replace('-', '_')}"
                # Remove redundant check_collection - search will fail gracefully if collection doesn't exist
                try:
                    scores = vector_db_client.search(
                        collection_name, data=query_vecs, topk=top_K
                    )
                    for score in scores:
                        score.update({"collection_name": collection_name})
                    result_score.extend(scores)
                except Exception as e:
                    logger.debug(f"Collection {collection_name} not accessible or empty: {e}")
            sorted_score = sort_and_filter(result_score, min_score=score_threshold)
            if len(sorted_score) >= top_K:
                cut_score = sorted_score[:top_K]
            else:
                cut_score = sorted_score

            # 获取minio name并转成base64
            for score in cut_score:
                """
                根据 file_id 和 image_id 获取：
                - knowledge_db_id
                - filename
                - 文件的 minio_filename 和 minio_url
                - 图片的 minio_filename 和 minio_url
                """
                file_and_image_info = await db.get_file_and_image_info(
                    score["file_id"], score["image_id"]
                )
                if not file_and_image_info["status"] == "success":
                    vector_db_client.delete_files(
                        score["collection_name"], [score["file_id"]]
                    )
                    logger.warning(
                        f"file_id: {score['file_id']} not found or corresponding image does not exist; deleting Milvus vectors"
                    )
                else:
                    file_used.append(
                        {
                            "score": score["score"],
                            "knowledge_db_id": file_and_image_info["knowledge_db_id"],
                            "file_name": file_and_image_info["file_name"],
                            "image_url": file_and_image_info["image_minio_url"],
                            "file_url": file_and_image_info["file_minio_url"],
                        }
                    )
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": file_and_image_info["image_minio_filename"],
                        }
                    )

        # 用户输入
        content.append(
            {
                "type": "text",
                "text": user_message_content.user_message,
            },
        )

        user_message = {
            "role": "user",
            "content": content,
        }
        messages.append(user_message)
        send_messages = await replace_image_content(messages)

        # DeepSeek Safety: Strip images if model is text-only
        if "deepseek" in model_name.lower():
            logger.info(
                f"Model {model_name} detected as DeepSeek. Stripping image content for compatibility."
            )
            for msg in send_messages:
                if isinstance(msg.get("content"), list):
                    msg["content"] = [
                        item
                        for item in msg["content"]
                        if item.get("type") != "image_url"
                    ]

        is_aborted = False  # 标记是否中断
        thinking_content = []
        full_response = []
        total_token = 0
        completion_tokens = 0
        prompt_tokens = 0
        client = None
        try:
            # Use provider client for direct API access (no LiteLLM proxy)
            # If model_url is provided (legacy), use it; otherwise auto-detect provider
            if model_url and model_url.startswith("http"):
                # Legacy: explicit URL provided (could be LiteLLM or direct)
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=model_url,
                )
            else:
                # New: auto-detect provider from model name
                client = get_llm_client(model_name, api_key=api_key)

            # 调用OpenAI API
            # 动态构建参数字典
            optional_args = {}

            # Provider-specific parameter handling
            # DeepSeek reasoning models don't support temperature/top_p
            is_deepseek_reasoner = (
                "deepseek" in model_name.lower() and
                ("reasoner" in model_name.lower() or "r1" in model_name.lower())
            )

            if is_deepseek_reasoner:
                # DeepSeek reasoning mode: remove unsupported parameters
                logger.info(
                    f"DeepSeek reasoning model detected ({model_name}). "
                    f"Temperature and top_p are not supported in reasoning mode."
                )
                # Use max_completion_tokens instead of max_tokens for reasoning models
                if max_length != -1:
                    optional_args["max_completion_tokens"] = max_length
            else:
                # Standard parameters for non-reasoning models
                if temperature != -1:
                    optional_args["temperature"] = temperature
                if max_length != -1:
                    optional_args["max_tokens"] = max_length
                if top_P != -1:
                    optional_args["top_p"] = top_P

            # 带条件参数的API调用
            response = await client.chat.completions.create(
                model=model_name,
                messages=send_messages,
                stream=True,
                stream_options={"include_usage": True},
                **optional_args,  # 展开条件参数
            )

            file_used_payload = json.dumps(
                {
                    "type": "file_used",
                    "data": file_used,  # 这里直接使用已构建的 file_used 列表
                    "message_id": message_id,
                    "model_name": model_name,
                }
            )
            yield f"data: {file_used_payload}\n\n"

            # 处理流响应
            async for chunk in response:  # 直接迭代异步生成器
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    # 思考
                    if (
                        hasattr(delta, "reasoning_content")
                        and delta.reasoning_content != None
                    ):
                        if not thinking_content:
                            thinking_content.append("<think>")
                        # 用JSON封装内容，自动处理换行符等特殊字符
                        payload = json.dumps(
                            {
                                "type": "thinking",
                                "data": delta.reasoning_content,
                                "message_id": message_id,
                            }
                        )
                        thinking_content.append(delta.reasoning_content)
                        yield f"data: {payload}\n\n"  # 保持SSE事件标准分隔符
                    # 回答
                    content = delta.content if delta else None
                    if content:
                        if not full_response and thinking_content:
                            thinking_content.append("</think>")
                            full_response.extend(thinking_content)
                        # 用JSON封装内容，自动处理换行符等特殊字符
                        payload = json.dumps(
                            {"type": "text", "data": content, "message_id": message_id}
                        )
                        full_response.append(content)
                        yield f"data: {payload}\n\n"  # 保持SSE事件标准分隔符
                else:
                    # token消耗
                    if hasattr(chunk, "usage") and chunk.usage != None:
                        total_token = chunk.usage.total_tokens
                        completion_tokens = chunk.usage.completion_tokens
                        prompt_tokens = chunk.usage.prompt_tokens
                        # 用JSON封装内容，自动处理换行符等特殊字符
                        payload = json.dumps(
                            {
                                "type": "token",
                                "total_token": total_token,
                                "completion_tokens": completion_tokens,
                                "prompt_tokens": prompt_tokens,
                                "message_id": message_id,
                            }
                        )
                        yield f"data: {payload}\n\n"  # 保持SSE事件标准分隔符
        except asyncio.CancelledError as e:
            logger.info("Request was cancelled by client")
            # 标记为中断状态
            is_aborted = True
            # 构建中断提示信息
            if not full_response and thinking_content:
                full_response.extend(thinking_content)
            full_response.append(" ⚠️ Abort By User")
            raise e  # 重新抛出异常以便上层处理
        except Exception as e:
            logger.error(f"Error during OpenAI API call: {str(e)}")
            # 构建错误提示信息
            if not full_response and thinking_content:
                full_response.extend(thinking_content)
            full_response.append(
                f"""⚠️ **Error occurred**:
 ```LLM_Error
{str(e)}
 ```"""
            )
            raise e  # 重新抛出异常以便上层处理
        finally:
            logger.info(
                f"Closing OpenAI client for conversation {user_message_content.conversation_id}"
            )
            if client:
                await client.close()

            # 只有在有响应内容时才保存
            if not full_response:
                full_response.append(
                    f"""⚠️ **Error occurred**:
 ```LLM_Error
 No message received from AI
 ```"""
                )
            ai_message = {"role": "assistant", "content": "".join(full_response)}

            # SECURITY FIX: Properly await database operation instead of fire-and-forget
            # Fire-and-forget tasks can cause silent failures and data loss
            await db.add_turn(
                conversation_id=user_message_content.conversation_id,
                message_id=message_id,
                parent_message_id=user_message_content.parent_id,
                user_message=user_message,
                temp_db=user_message_content.temp_db,
                ai_message=ai_message,
                file_used=file_used,
                status="aborted" if is_aborted else "completed",
                total_token=total_token,
                completion_tokens=completion_tokens,
                prompt_tokens=prompt_tokens,
            )
            logger.info(
                f"Save conversation {user_message_content.conversation_id} to mongodb"
            )

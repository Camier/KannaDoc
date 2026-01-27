"""
Unified ChatService for both RAG-based chat and workflow LLM nodes.

This service consolidates two previously separate implementations:
- backend/app/rag/llm_service.py (417 lines) - Used for /api/v1/chat endpoints
- backend/app/workflow/llm_service.py (415 lines) - Used for workflow LLM nodes

Key differences merged:
- RAG mode: Fetches model_config from database via conversation_id
- Workflow mode: Receives model_config as parameter (for node configuration)
- Workflow mode has additional parameters: history_depth, save_to_db, user_image_urls,
  supply_info, quote_variables

Common utilities are shared via app.core.embeddings (normalize_multivector).
"""
import asyncio
import json
from typing import AsyncGenerator, Optional, Dict, Any, List
from openai import AsyncOpenAI

from app.db.mongo import get_mongo
from app.core.logging import logger
from app.db.vector_db import vector_db_client
from app.rag.get_embedding import get_embeddings_from_httpx
from app.rag.utils import replace_image_content, sort_and_filter
from app.rag.mesage import find_depth_parent_mesage
from app.rag.provider_client import get_llm_client
from app.core.embeddings import normalize_multivector


class ChatService:
    """
    Unified LLM chat service supporting both RAG and workflow modes.

    The service automatically detects the mode based on parameters:
    - RAG mode: model_config is None, fetched from DB via conversation_id
    - Workflow mode: model_config is provided as parameter
    """

    @staticmethod
    def _validate_and_normalize_param(value: Any, param_name: str, validator) -> Any:
        """Validate and normalize a parameter value."""
        return validator(value)

    @staticmethod
    def _normalize_temperature(temperature: float) -> float:
        """Normalize temperature parameter."""
        if temperature < 0 and not temperature == -1:
            return 0
        elif temperature > 1:
            return 1
        return temperature

    @staticmethod
    def _normalize_max_length(max_length: int) -> int:
        """Normalize max_length parameter."""
        if max_length < 1024 and not max_length == -1:
            return 1024
        elif max_length > 1048576:
            return 1048576
        return max_length

    @staticmethod
    def _normalize_top_p(top_p: float) -> float:
        """Normalize top_p parameter."""
        if top_p < 0 and not top_p == -1:
            return 0
        elif top_p > 1:
            return 1
        return top_p

    @staticmethod
    def _normalize_top_k(top_k: int) -> int:
        """Normalize top_k parameter."""
        if top_k == -1:
            return 3
        elif top_k < 1:
            return 1
        elif top_k > 30:
            return 30
        return top_k

    @staticmethod
    def _normalize_score_threshold(score_threshold: float) -> float:
        """Normalize score_threshold parameter."""
        if score_threshold == -1:
            return 10
        elif score_threshold < 0:
            return 0
        elif score_threshold > 20:
            return 20
        return score_threshold

    @staticmethod
    async def create_chat_stream(
        user_message_content,  # Union[UserMessage from conversation or workflow]
        model_config: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        history_depth: int = 5,
        save_to_db: bool = False,
        user_image_urls: List = [],
        supply_info: str = "",
        quote_variables: Dict = {},
        is_workflow: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Create chat stream with unified RAG and workflow support.

        Args:
            user_message_content: User message object (different types for RAG vs workflow)
            model_config: Optional model config dict (workflow mode). If None, fetched from DB.
            message_id: Message ID for tracking
            system_prompt: Optional system prompt override (workflow mode)
            history_depth: How many parent messages to include (workflow mode)
            save_to_db: Whether to save to database (workflow mode)
            user_image_urls: User-provided image URLs (workflow mode)
            supply_info: Additional context from MCP/tools (workflow mode)
            quote_variables: Template variable replacement dict (workflow mode)
            is_workflow: True if called from workflow, False for RAG chat

        Yields:
            str: SSE-formatted JSON chunks with type markers (text, thinking, file_used, token)
        """
        db = await get_mongo()

        # Stream/session state
        is_aborted = False
        had_error = False
        thinking_content = []
        full_response = []
        total_token = 0
        completion_tokens = 0
        prompt_tokens = 0
        client = None
        file_used: list = []

        # Determine mode and fetch config if needed
        if is_workflow:
            # Workflow mode: model_config and system_prompt provided
            if not model_config:
                raise ValueError("Workflow mode requires model_config parameter")
            if not message_id:
                raise ValueError("Workflow mode requires message_id parameter")

            model_name = model_config["model_name"]
            model_url = model_config["model_url"]
            api_key = model_config["api_key"]
            base_used = model_config["base_used"]

            # Use provided system_prompt or empty
            if system_prompt is None:
                system_prompt = ""
        else:
            # RAG mode: fetch config from database
            if not message_id:
                raise ValueError("RAG mode requires message_id parameter")

            model_config = await db.get_conversation_model_config(
                user_message_content.conversation_id
            )
            if not model_config:
                raise ValueError(
                    "Conversation not found or model config missing. "
                    "Create the conversation and configure its model settings first."
                )

            model_name = model_config.get("model_name")
            model_url = model_config.get("model_url")
            api_key = model_config.get("api_key")
            base_used = model_config.get("base_used") or []
            system_prompt = model_config.get("system_prompt") or ""

        if not model_name:
            raise ValueError("Invalid model config: missing model_name")

        # Truncate system prompt if too long
        if len(system_prompt) > 1048576:
            system_prompt = system_prompt[0:1048576]

        # Normalize and validate parameters
        temperature = ChatService._normalize_temperature(model_config.get("temperature", -1) if not is_workflow else model_config["temperature"])
        max_length = ChatService._normalize_max_length(model_config.get("max_length", -1) if not is_workflow else model_config["max_length"])
        top_P = ChatService._normalize_top_p(model_config.get("top_P", -1) if not is_workflow else model_config["top_P"])
        top_K = ChatService._normalize_top_k(model_config.get("top_K", -1) if not is_workflow else model_config["top_K"])
        score_threshold = ChatService._normalize_score_threshold(model_config.get("score_threshold", -1) if not is_workflow else model_config["score_threshold"])

        # Build messages array
        if not system_prompt:
            messages = []
        else:
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}],
                }
            ]
            logger.info(f"chat '{user_message_content.conversation_id if not is_workflow else message_id} uses system prompt'")

        # Handle history based on mode
        if is_workflow and user_message_content.parent_id:
            logger.info(f"{user_message_content.conversation_id} chatflow memory enabled, fetching parent nodes...")
            history_messages = await find_depth_parent_mesage(
                user_message_content.conversation_id,
                user_message_content.parent_id,
                MAX_PARENT_DEPTH=history_depth,
                chatflow=True,
            )
            for i in range(len(history_messages), 0, -1):
                messages.append(history_messages[i - 1])
        elif not is_workflow:
            # RAG mode always fetches history
            history_messages = await find_depth_parent_mesage(
                user_message_content.conversation_id,
                user_message_content.parent_id,
                MAX_PARENT_DEPTH=5,
            )
            for i in range(len(history_messages), 0, -1):
                messages.append(history_messages[i - 1])

        # Process user uploaded files and RAG retrieval
        content = []
        bases = []
        user_images = []

        # Handle temp_db_id (standardized field name)
        temp_db_id = user_message_content.temp_db_id
        if temp_db_id:
            bases.append({"baseId": temp_db_id})

        bases.extend(base_used)

        if bases:
            result_score = []

            # Retrieval is best-effort: if embedding/search fails, continue without RAG context
            query_vecs = []
            try:
                query_embedding = await get_embeddings_from_httpx(
                    [user_message_content.user_message], endpoint="embed_text"
                )
                query_vecs = normalize_multivector(query_embedding)
            except Exception as e:
                logger.warning(f"RAG retrieval skipped (embedding failed): {e}")

            if query_vecs:
                for base in bases:
                    collection_name = f"colqwen{base['baseId'].replace('-', '_')}"
                    try:
                        if is_workflow:
                            # Workflow mode: check collection first
                            if vector_db_client.check_collection(collection_name):
                                scores = vector_db_client.search(
                                    collection_name, data=query_vecs, topk=top_K
                                )
                                for score in scores:
                                    score.update({"collection_name": collection_name})
                                result_score.extend(scores)
                        else:
                            # RAG mode: direct search with exception handling
                            scores = vector_db_client.search(
                                collection_name, data=query_vecs, topk=top_K
                            )
                            for score in scores:
                                score.update({"collection_name": collection_name})
                            result_score.extend(scores)
                    except Exception as e:
                        if is_workflow:
                            # Workflow mode logs but doesn't add to results
                            logger.debug(f"Collection {collection_name} check failed: {e}")
                        else:
                            # RAG mode logs and continues
                            logger.debug(
                                f"Collection {collection_name} not accessible or empty: {e}"
                            )

                sorted_score = sort_and_filter(result_score, min_score=score_threshold)
                cut_score = sorted_score[:top_K]

                # Get minio names and convert to base64
                for score in cut_score:
                    file_and_image_info = await db.get_file_and_image_info(
                        score["file_id"], score["image_id"]
                    )
                    if not file_and_image_info["status"] == "success":
                        if is_workflow:
                            # Workflow mode: delete orphaned vectors
                            vector_db_client.delete_files(
                                score["collection_name"], [score["file_id"]]
                            )
                            logger.warning(
                                f"file_id: {score['file_id']} not found or corresponding image does not exist; deleting Milvus vectors"
                            )
                        else:
                            # RAG mode: just log warning
                            logger.warning(
                                "RAG hit skipped (metadata mismatch): "
                                f"collection={score.get('collection_name')} "
                                f"file_id={score.get('file_id')} "
                                f"image_id={score.get('image_id')} "
                                f"page_number={score.get('page_number')}"
                            )
                        continue

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
                    # Track images for workflow mode
                    user_images.append(
                        {
                            "type": "image_url",
                            "image_url": file_and_image_info["image_minio_filename"],
                        }
                    )

        # Build user message content
        user_text = user_message_content.user_message
        if is_workflow and supply_info:
            user_text += supply_info

        content.append({"type": "text", "text": user_text})
        user_message = {"role": "user", "content": content}
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

        # Build API call parameters
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

        # Call API with streaming
        response = await client.chat.completions.create(
            model=model_name,
            messages=send_messages,
            stream=True,
            stream_options={"include_usage": True},
            **optional_args,
        )

        # Send file_used payload
        file_used_payload = json.dumps(
            {
                "type": "file_used",
                "data": file_used,
                "message_id": message_id,
                "model_name": model_name,
            }
        )

        if is_workflow:
            # Workflow mode: yield without SSE wrapper
            yield f"{file_used_payload}"

            # Also send user_images in workflow mode
            user_images_payload = json.dumps(
                {
                    "type": "user_images",
                    "data": user_images,
                    "message_id": message_id,
                    "model_name": model_name,
                }
            )
            yield f"{user_images_payload}"
        else:
            # RAG mode: wrap in SSE format
            yield f"data: {file_used_payload}\n\n"

        # Process streaming response
        try:
            async for chunk in response:
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # Handle reasoning content (thinking)
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                        if not thinking_content:
                            thinking_content.append("</think>")
                        payload = json.dumps(
                            {
                                "type": "thinking",
                                "data": delta.reasoning_content,
                                "message_id": message_id,
                            }
                        )
                        thinking_content.append(delta.reasoning_content)
                        if is_workflow:
                            yield f"{payload}"
                        else:
                            yield f"data: {payload}\n\n"

                    # Handle regular content
                    content = delta.content if delta else None
                    if content:
                        if not full_response and thinking_content:
                            thinking_content.append("</think>")
                            full_response.extend(thinking_content)
                        payload = json.dumps(
                            {"type": "text", "data": content, "message_id": message_id}
                        )
                        full_response.append(content)
                        if is_workflow:
                            yield f"{payload}"
                        else:
                            yield f"data: {payload}\n\n"
                else:
                    # Handle token usage
                    if hasattr(chunk, "usage") and chunk.usage is not None:
                        total_token = chunk.usage.total_tokens
                        completion_tokens = chunk.usage.completion_tokens
                        prompt_tokens = chunk.usage.prompt_tokens
                        payload = json.dumps(
                            {
                                "type": "token",
                                "total_token": total_token,
                                "completion_tokens": completion_tokens,
                                "prompt_tokens": prompt_tokens,
                                "message_id": message_id,
                            }
                        )
                        if is_workflow:
                            yield f"{payload}"
                        else:
                            yield f"data: {payload}\n\n"

            if not full_response:
                raise RuntimeError("No message received from AI")

        except asyncio.CancelledError:
            logger.info("Request was cancelled by client")
            is_aborted = True
            if not full_response and thinking_content:
                full_response.extend(thinking_content)
            full_response.append(" ⚠️ Abort By User")
            raise

        except Exception as e:
            had_error = True
            logger.error(f"Error during chat stream: {str(e)}")
            if not full_response and thinking_content:
                full_response.extend(thinking_content)
            err_msg = f"""⚠️ **Error occurred**:
 ```LLM_Error
{str(e)}
 ```"""
            full_response.append(err_msg)

            # Send error to frontend
            payload = json.dumps(
                {"type": "text", "data": err_msg, "message_id": message_id}
            )
            if is_workflow:
                yield f"{payload}"
            else:
                yield f"data: {payload}\n\n"

        finally:
            logger.info(
                f"Closing OpenAI client for conversation {user_message_content.conversation_id}"
            )
            if client:
                try:
                    await client.close()
                except Exception as close_error:
                    logger.debug(f"Failed to close OpenAI client cleanly: {close_error}")

            # Handle empty response
            if not full_response:
                had_error = True
                full_response.append(
                    f"""⚠️ **Error occurred**:
 ```LLM_Error
 No message received from AI
 ```"""
                )

            # Save to database based on mode
            if is_workflow and save_to_db:
                # Workflow mode: optional saving with template replacement
                from app.workflow.utils import replace_template

                ai_response = "".join(full_response)
                if quote_variables:
                    ai_response = replace_template(ai_response, quote_variables)
                ai_message = {"role": "assistant", "content": ai_response}

                # Use provided user_image_urls or fall back to retrieved images
                if not user_image_urls:
                    user_image_urls = user_images

                user_chatflow_input = {"role": "user", "content": user_image_urls}

                logger.info(
                    f"chatflow {user_message_content.conversation_id} saving to mongodb..."
                )
                await db.chatflow_add_turn(
                    chatflow_id=user_message_content.conversation_id,
                    message_id=message_id,
                    parent_message_id=user_message_content.parent_id,
                    user_message=user_chatflow_input,
                    temp_db=user_message_content.temp_db_id,
                    ai_message=ai_message,
                    file_used=file_used,
                    status="",
                    total_token=total_token,
                    completion_tokens=completion_tokens,
                    prompt_tokens=prompt_tokens,
                )
            elif not is_workflow:
                # RAG mode: always save
                ai_message = {"role": "assistant", "content": "".join(full_response)}
                try:
                    await db.add_turn(
                        conversation_id=user_message_content.conversation_id,
                        message_id=message_id,
                        parent_message_id=user_message_content.parent_id,
                        user_message=user_message,
                        temp_db=user_message_content.temp_db_id,
                        ai_message=ai_message,
                        file_used=file_used,
                        status=(
                            "aborted"
                            if is_aborted
                            else ("failed" if had_error else "completed")
                        ),
                        total_token=total_token,
                        completion_tokens=completion_tokens,
                        prompt_tokens=prompt_tokens,
                    )
                except Exception as db_error:
                    logger.error(
                        f"Failed to persist chat turn for conversation {user_message_content.conversation_id}: {db_error}"
                    )
                logger.info(
                    f"Save conversation {user_message_content.conversation_id} to mongodb"
                )

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
import time
from typing import AsyncGenerator, Optional, Dict, Any, List, cast
from openai import AsyncOpenAI  # type: ignore[import-not-found]

from app.db.repositories.repository_manager import get_repository_manager
from app.core.logging import logger
from app.core.circuit_breaker import llm_service_circuit
from app.db.vector_db import vector_db_client
from app.rag.get_embedding import get_embeddings_from_httpx, get_sparse_embeddings
from app.rag.utils import replace_image_content, sort_and_filter
from app.rag.mesage import find_depth_parent_mesage
from app.rag.provider_client import get_llm_client, ProviderClient
from app.core.config import settings
from app.core.embeddings import normalize_multivector, downsample_multivector


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
    @llm_service_circuit
    async def create_chat_stream(
        user_message_content,  # Union[UserMessage from conversation or workflow]
        model_config: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        history_depth: int = 5,
        save_to_db: bool = False,
        user_image_urls: Optional[List] = None,
        supply_info: str = "",
        quote_variables: Optional[Dict] = None,
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
        repo_manager = await get_repository_manager()

        # Avoid mutable default argument pitfalls.
        user_image_urls = user_image_urls or []
        quote_variables = quote_variables or {}

        t0 = time.perf_counter()
        t_embed_s = 0.0
        t_search_s = 0.0
        t_meta_s = 0.0
        t_minio_s = 0.0
        rag_hits = 0

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

            model_config = (
                await repo_manager.conversation.get_conversation_model_config(
                    user_message_content.conversation_id
                )
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
        temperature = ChatService._normalize_temperature(
            model_config.get("temperature", -1)
            if not is_workflow
            else model_config["temperature"]
        )
        max_length = ChatService._normalize_max_length(
            model_config.get("max_length", -1)
            if not is_workflow
            else model_config["max_length"]
        )
        top_P = ChatService._normalize_top_p(
            model_config.get("top_P", -1) if not is_workflow else model_config["top_P"]
        )
        top_K = ChatService._normalize_top_k(
            model_config.get("top_K", -1) if not is_workflow else model_config["top_K"]
        )
        score_threshold = ChatService._normalize_score_threshold(
            model_config.get("score_threshold", -1)
            if not is_workflow
            else model_config["score_threshold"]
        )

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
            logger.info(
                f"chat '{user_message_content.conversation_id if not is_workflow else message_id} uses system prompt'"
            )

        # Handle history based on mode
        if is_workflow and user_message_content.parent_id:
            logger.info(
                f"{user_message_content.conversation_id} chatflow memory enabled, fetching parent nodes..."
            )
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
        nq_before = 0
        nq_after = 0

        # Handle temp_db_id (standardized field name)
        temp_db_id = getattr(user_message_content, "temp_db_id", "") or getattr(
            user_message_content, "temp_db", ""
        )
        if temp_db_id:
            bases.append({"baseId": temp_db_id})

        bases.extend(base_used)

        if bases:
            result_score = []

            # Safeguard RAG block to ensure chat continues even if retrieval fails
            try:
                # Retrieval is best-effort: if embedding/search fails, continue without RAG context
                query_vecs = []
                try:
                    t_start = time.perf_counter()
                    query_embedding = await get_embeddings_from_httpx(
                        [user_message_content.user_message], endpoint="embed_text"
                    )
                    query_vecs = normalize_multivector(query_embedding)
                    nq_before = len(query_vecs)
                    query_vecs = downsample_multivector(
                        query_vecs, settings.rag_max_query_vecs
                    )
                    nq_after = len(query_vecs)
                    t_embed_s += time.perf_counter() - t_start
                except Exception as e:
                    logger.warning(f"RAG retrieval skipped (embedding failed): {e}")

                # Generate sparse embeddings for hybrid search
                sparse_vecs = []
                if settings.rag_hybrid_enabled and query_vecs:
                    try:
                        sparse_result = await get_sparse_embeddings(
                            [user_message_content.user_message]
                        )
                        if sparse_result and len(sparse_result) > 0:
                            # Replicate single sparse vector to match dense vector count
                            sparse_vecs = [sparse_result[0]] * len(query_vecs)
                    except Exception as e:
                        logger.warning(
                            f"Sparse embedding failed, falling back to dense-only: {e}"
                        )

                if query_vecs:
                    # Prepare search data - use hybrid format if sparse vectors available
                    search_data = (
                        {"dense_vecs": query_vecs, "sparse_vecs": sparse_vecs}
                        if sparse_vecs
                        else query_vecs
                    )
                    for base in bases:
                        collection_name = f"colqwen{base['baseId'].replace('-', '_')}"
                        try:
                            t_start = time.perf_counter()
                            if is_workflow:
                                # Workflow mode: check collection first
                                if vector_db_client.check_collection(collection_name):
                                    scores = vector_db_client.search(
                                        collection_name, data=search_data, topk=top_K
                                    )
                                    for score in scores:
                                        score.update(
                                            {"collection_name": collection_name}
                                        )
                                    result_score.extend(scores)
                            else:
                                # RAG mode: direct search with exception handling
                                scores = vector_db_client.search(
                                    collection_name, data=search_data, topk=top_K
                                )
                                for score in scores:
                                    score.update({"collection_name": collection_name})
                                result_score.extend(scores)
                            t_search_s += time.perf_counter() - t_start
                        except Exception as e:
                            if is_workflow:
                                # Workflow mode logs but doesn't add to results
                                logger.debug(
                                    f"Collection {collection_name} check failed: {e}"
                                )
                            else:
                                # RAG mode logs and continues
                                logger.debug(
                                    f"Collection {collection_name} not accessible or empty: {e}"
                                )

                    sorted_score = sort_and_filter(
                        result_score, min_score=score_threshold
                    )
                    cut_score = sorted_score[:top_K]

                    # Batch fetch metadata (eliminates N+1 query pattern)
                    if cut_score:
                        t_start = time.perf_counter()
                        file_image_pairs = [
                            (score["file_id"], score["image_id"]) for score in cut_score
                        ]
                        file_infos = await repo_manager.file.get_files_and_images_batch(
                            file_image_pairs
                        )
                        t_meta_s += time.perf_counter() - t_start

                        for score, file_and_image_info in zip(cut_score, file_infos):
                            if file_and_image_info.get("status") != "success":
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
                                    "knowledge_db_id": file_and_image_info[
                                        "knowledge_db_id"
                                    ],
                                    "file_name": file_and_image_info["file_name"],
                                    "image_url": file_and_image_info["image_minio_url"],
                                    "file_url": file_and_image_info["file_minio_url"],
                                }
                            )
                            content.append(
                                {
                                    "type": "image_url",
                                    "image_url": file_and_image_info[
                                        "image_minio_filename"
                                    ],
                                }
                            )
                            user_images.append(
                                {
                                    "type": "image_url",
                                    "image_url": file_and_image_info[
                                        "image_minio_filename"
                                    ],
                                }
                            )
                            rag_hits += 1
            except Exception as e:
                logger.error(
                    f"Critical error in RAG retrieval block: {e}", exc_info=True
                )
                # Continue chat execution without RAG context instead of crashing
                pass

        # Build user message content
        user_text = user_message_content.user_message
        if is_workflow and supply_info:
            user_text += supply_info

        content.append({"type": "text", "text": user_text})
        user_message = {"role": "user", "content": content}
        messages.append(user_message)

        # DeepSeek Safety: Strip images if model is text-only.
        # Also avoid expensive MinIO->base64 conversion when images will be removed anyway.
        if "deepseek" in model_name.lower():
            logger.info(
                f"Model {model_name} detected as DeepSeek. Stripping image content for compatibility."
            )
            send_messages = messages
            for msg in send_messages:
                if isinstance(msg.get("content"), list):
                    msg["content"] = [
                        item
                        for item in msg["content"]
                        if item.get("type") != "image_url"
                    ]
        else:
            t_start = time.perf_counter()
            send_messages = await replace_image_content(messages)
            t_minio_s += time.perf_counter() - t_start

        # One-line timing log for retrieval stages (best-effort).
        if bases:
            logger.info(
                "RAG timings "
                f"embed_s={t_embed_s:.3f} "
                f"search_s={t_search_s:.3f} "
                f"meta_s={t_meta_s:.3f} "
                f"minio_s={t_minio_s:.3f} "
                f"nq_before={nq_before} "
                f"nq_after={nq_after} "
                f"hits={rag_hits} "
                f"total_s={(time.perf_counter() - t0):.3f} "
                f"mode={'workflow' if is_workflow else 'rag'}"
            )

        # Use provider client for direct API access (no LiteLLM proxy)
        # If model_url is provided (legacy), use it; otherwise auto-detect provider
        try:
            if model_url and model_url.startswith("http"):
                # Legacy: explicit URL provided (could be LiteLLM or direct)
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=model_url,
                )
            else:
                # New: auto-detect provider from model name
                client = get_llm_client(model_name, api_key=api_key)
        except Exception as e:
            logger.error(f"Error creating LLM client: {str(e)}")
            err_msg = f"""⚠️ **Configuration Error**:
```LLM_Error
{str(e)}
```"""
            payload = json.dumps(
                {"type": "text", "data": err_msg, "message_id": message_id}
            )
            if is_workflow:
                yield f"{payload}"
            else:
                yield f"data: {payload}\n\n"
            return

        # Build API call parameters
        optional_args = {}

        # Provider-specific parameter handling
        # DeepSeek reasoning models don't support temperature/top_p
        is_deepseek_reasoner = "deepseek" in model_name.lower() and (
            "reasoner" in model_name.lower() or "r1" in model_name.lower()
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

        # Detect provider to handle auto-detection cases (where model_url is None)
        detected_provider = ProviderClient.get_provider_for_model(model_name)

        logger.info(
            f"DEBUG: model_name={model_name}, detected_provider={detected_provider}, model_url={model_url}"
        )

        # Zhipu API doesn't support stream_options parameter
        if model_url:
            is_zhipu = "glm" in model_name.lower() or "zhipu" in model_url.lower()
        else:
            # Strictly identify Zhipu/Z.ai providers to suppress stream_options
            # Sending stream_options to Zhipu causes API errors/empty responses
            is_zhipu = detected_provider in ("zhipu", "zhipu-coding", "zai")

        # Z.ai requires uppercase model names (GLM-4.7, not glm-4.7)
        if model_url:
            is_zai = "z.ai" in model_url.lower()
        else:
            is_zai = detected_provider == "zai"

        api_model_name = model_name
        if is_zai and model_name.lower().startswith("glm"):
            # Convert glm-4.7 -> GLM-4.7, glm-4.7-flash -> GLM-4.7-Flash
            parts = model_name.split("-")
            api_model_name = parts[0].upper()  # GLM
            if len(parts) > 1:
                api_model_name += "-" + parts[1]  # GLM-4.7
            if len(parts) > 2:
                api_model_name += "-" + parts[2].capitalize()  # GLM-4.7-Flash

        logger.info(
            f"DEBUG: is_zhipu={is_zhipu}, is_zai={is_zai}, api_model_name={api_model_name}"
        )

        stream_kwargs: Dict[str, Any] = {"stream": True}
        if not is_zhipu:
            stream_kwargs["stream_options"] = {"include_usage": True}

        logger.info(f"DEBUG: stream_kwargs={stream_kwargs}")

        stream_kwargs: Dict[str, Any] = {"stream": True}
        if not is_zhipu:
            stream_kwargs["stream_options"] = {"include_usage": True}

        # Call API with streaming
        try:
            response = await client.chat.completions.create(
                model=api_model_name,
                messages=send_messages,
                **stream_kwargs,
                **optional_args,
            )
        except Exception as e:
            logger.error(f"Error initializing chat stream: {str(e)}")
            err_msg = f"""⚠️ **Error occurred during initialization**:
```LLM_Error
{str(e)}
```"""
            payload = json.dumps(
                {"type": "text", "data": err_msg, "message_id": message_id}
            )
            if is_workflow:
                yield f"{payload}"
            else:
                yield f"data: {payload}\n\n"
            return

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
                    if (
                        hasattr(delta, "reasoning_content")
                        and delta.reasoning_content is not None
                    ):
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
                    logger.debug(
                        f"Failed to close OpenAI client cleanly: {close_error}"
                    )

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
                await repo_manager.chatflow.chatflow_add_turn(
                    chatflow_id=user_message_content.conversation_id,
                    message_id=message_id,
                    parent_message_id=user_message_content.parent_id,
                    user_message=cast(Any, user_chatflow_input),
                    temp_db=user_message_content.temp_db_id,
                    ai_message=cast(Any, ai_message),
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
                    await repo_manager.conversation.add_turn(
                        conversation_id=user_message_content.conversation_id,
                        message_id=message_id,
                        parent_message_id=user_message_content.parent_id,
                        user_message=cast(Any, user_message),
                        temp_db=user_message_content.temp_db_id,
                        ai_message=cast(Any, ai_message),
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

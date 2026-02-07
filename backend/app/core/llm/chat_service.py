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
from urllib.parse import urlencode
from openai import AsyncOpenAI  # type: ignore[import-not-found]

from app.db.repositories.repository_manager import get_repository_manager
from app.core.logging import logger
from app.core.circuit_breaker import llm_service_circuit
from app.db.vector_db import vector_db_client
from app.rag.get_embedding import get_embeddings_from_httpx, get_sparse_embeddings
from app.rag.utils import replace_image_content, sort_and_filter
from app.rag.message import find_depth_parent_mesage
from app.rag.provider_client import (
    get_llm_client,
    ProviderClient,
    resolve_api_model_name,
)
from app.core.config import settings
from app.core.embeddings import normalize_multivector, downsample_multivector
from app.utils.ids import to_milvus_collection_name


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
        """Normalize temperature parameter.

        Note: -1 is a sentinel value meaning "use provider default".
        When -1 is passed, it's preserved and typically handled by the
        LLM client to omit the parameter from the API request.
        """
        if temperature < 0 and not temperature == -1:
            return 0
        # Pydantic validator allows up to 2.0; keep ChatService consistent.
        elif temperature > 2:
            return 2
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
        top_k_cap = int(getattr(settings, "rag_top_k_cap", 120))

        if top_k == -1:
            # Thesis default: -1 means "use environment default", not "tiny recall".
            normalized = int(getattr(settings, "rag_default_top_k", 50))
        elif top_k < 1:
            normalized = 1
        elif top_k > top_k_cap:
            normalized = top_k_cap
        else:
            normalized = top_k

        # Thesis sparse/dual modes need enough breadth to diversify across files/pages.
        retrieval_mode = getattr(settings, "rag_retrieval_mode", "dense")
        if retrieval_mode == "dense" and getattr(settings, "rag_hybrid_enabled", False):
            retrieval_mode = "hybrid"
        if retrieval_mode in ["sparse_then_rerank", "dual_then_rerank"]:
            min_k = int(getattr(settings, "rag_search_limit_min", 50))
            if normalized < min_k:
                normalized = min_k

        if normalized > top_k_cap:
            normalized = top_k_cap
        return normalized

    @staticmethod
    def _normalize_score_threshold(score_threshold: float) -> float:
        """Normalize score_threshold parameter."""
        if score_threshold == -1:
            # Thesis default: treat -1 as "no filter" (environment-tunable).
            return float(getattr(settings, "rag_default_score_threshold", 0.0))
        elif score_threshold < 0:
            return 0
        elif score_threshold > 20:
            return 20
        return score_threshold

    @staticmethod
    def _is_system_model(model_config: Optional[Dict[str, Any]]) -> bool:
        model_id = str((model_config or {}).get("model_id") or "")
        return model_id.startswith("system_")

    @staticmethod
    def _resolve_effective_provider(
        *,
        provider: Optional[str],
        model_url: Optional[str],
        model_name: str,
    ) -> Optional[str]:
        """Resolve the effective provider for provider-specific behavior.

        Rationale:
        - If the user provides an explicit provider, trust it.
        - If the user provides an explicit OpenAI-compatible model_url, do NOT apply
          provider-specific special-cases based on the model name alone. That avoids
          breaking proxied/self-hosted endpoints (e.g., a proxy serving a model named
          "deepseek-reasoner" but still supporting standard temperature/top_p).
        - Otherwise, fall back to provider detection by model name.
        """
        p = (provider or "").strip().lower() or None
        if p:
            return p
        if model_url and str(model_url).startswith("http"):
            return None
        return ProviderClient.get_provider_for_model(model_name)

    @staticmethod
    def _tuned_generation_defaults(
        provider: Optional[str],
        model_name: str,
    ) -> dict[str, Any]:
        """Provider-aware defaults for "academic/RAG" chat generation.

        These defaults are ONLY applied for system_* models (see below) when the stored
        config uses the -1 sentinel (meaning "provider default").

        Goals:
        - Lower hallucination risk
        - Stable, sober academic tone
        - Avoid overspecifying params that some providers might not support
        """
        provider_l = (provider or "").strip().lower()
        model_l = (model_name or "").strip().lower()

        # Conservative defaults; callers decide which fields to apply.
        # Note: we intentionally do NOT force top_p by default to reduce the chance of
        # provider incompatibility. Temperature alone typically achieves the main goal.
        defaults: dict[str, Any] = {
            "temperature": 0.2,
            "max_tokens": 4096,
            "top_p": -1,
        }

        # Slight tweaks for smaller/faster models: cap output to reduce runaway.
        if any(x in model_l for x in ["flash", "lite"]):
            defaults["max_tokens"] = 3072

        # DeepSeek reasoning models are handled separately (no temperature/top_p).
        if provider_l == "deepseek" and ("reasoner" in model_l):
            defaults["max_tokens"] = 4096

        return defaults

    @staticmethod
    def _is_deepseek_reasoner_model(
        model_name: str,
        provider: Optional[str],
    ) -> bool:
        """DeepSeek reasoner detection must be provider-aware.

        Example bug we avoid:
        - model_name="deepseek-r1" served via provider="ollama-cloud" should NOT be treated
          as the official DeepSeek reasoner API.
        """
        provider_l = (provider or "").strip().lower()
        model_l = (model_name or "").strip().lower()
        if provider_l != "deepseek":
            return False
        # Official DeepSeek API uses deepseek-reasoner. Keep matching strict.
        return model_l == "deepseek-reasoner" or ("deepseek" in model_l and "reasoner" in model_l)

    @staticmethod
    def _build_optional_openai_args(
        *,
        model_name: str,
        provider: Optional[str],
        temperature: float,
        max_length: int,
        top_p: float,
    ) -> dict[str, Any]:
        """Translate normalized config -> OpenAI-compatible request kwargs."""
        optional_args: dict[str, Any] = {}
        provider_l = (provider or "").strip().lower()
        model_l = (model_name or "").strip().lower()

        # In this repo, Claude/Gemini models are typically accessed via "antigravity"
        # behind the OpenAI-compatible CLIProxyAPI provider ("cliproxyapi").
        # There is no standalone "anthropic" provider id.
        is_claude_via_cliproxyapi = provider_l == "cliproxyapi" and "claude" in model_l

        is_deepseek_reasoner = ChatService._is_deepseek_reasoner_model(
            model_name=model_name,
            provider=provider,
        )

        if is_deepseek_reasoner:
            # DeepSeek reasoning mode: remove unsupported parameters
            logger.info(
                f"DeepSeek reasoning model detected ({model_name}). "
                f"Temperature and top_p are not supported in reasoning mode."
            )
            if max_length != -1:
                # DeepSeek's OpenAI-compatible Chat Completions API uses max_tokens.
                optional_args["max_tokens"] = max_length
            return optional_args

        # Provider-aware bounds: some OpenAI-compatible providers document a narrower
        # temperature range than the OpenAI API (0..2). We clamp only when provider is
        # explicit (or detected and trusted) to avoid breaking arbitrary proxies.
        if temperature != -1:
            if provider_l == "minimax":
                # MiniMax docs use a strict (0, 1] temperature range (0.0 may be rejected).
                temperature = max(0.01, min(float(temperature), 1.0))
            elif provider_l == "zai":
                # Z.ai docs use [0, 1] for temperature.
                temperature = max(0.0, min(float(temperature), 1.0))
            if is_claude_via_cliproxyapi:
                temperature = max(0.0, min(float(temperature), 1.0))

        if temperature != -1:
            optional_args["temperature"] = temperature
        if max_length != -1:
            optional_args["max_tokens"] = max_length
        if top_p != -1:
            # Provider-aware bounds: some OpenAI-compatible providers document a stricter
            # lower bound than OpenAI's [0, 1]. We only clamp when provider is explicit
            # (or detected and trusted) to avoid breaking arbitrary proxies.
            if provider_l == "minimax":
                # MiniMax docs often specify (0, 1]; avoid sending 0.0.
                top_p = max(0.01, min(float(top_p), 1.0))
            elif provider_l == "zai":
                # Z.ai docs specify top_p in [0.01, 1].
                top_p = max(0.01, min(float(top_p), 1.0))

            # Anthropic recommends adjusting *either* temperature or top_p (not both),
            # and some Claude variants may reject requests that specify both.
            # In this stack, we apply the conservative rule to Claude models proxied via CLIProxyAPI.
            if is_claude_via_cliproxyapi and temperature != -1:
                logger.info(
                    "Claude via CLIProxyAPI: dropping top_p because temperature is set (compat)."
                )
            else:
                optional_args["top_p"] = top_p
        return optional_args

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

            # Validate required keys exist in workflow model_config
            required_keys = ["model_name", "model_url", "api_key", "base_used"]
            missing_keys = [k for k in required_keys if k not in model_config]
            if missing_keys:
                raise ValueError(
                    f"Workflow model_config missing required keys: {missing_keys}"
                )

            model_name = model_config["model_name"]
            model_url = model_config["model_url"]
            api_key = model_config["api_key"]
            provider = model_config.get("provider")
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
            provider = model_config.get("provider")
            base_used = model_config.get("base_used") or []
            system_prompt = model_config.get("system_prompt") or ""

        if not model_name:
            raise ValueError("Invalid model config: missing model_name")

        system_prompt = cast(str, system_prompt or "")

        # Truncate system prompt if too long
        if len(system_prompt) > 1048576:
            system_prompt = system_prompt[0:1048576]

        # Normalize parameters (with thesis-specific tuned defaults for system_* models).
        effective_provider = ChatService._resolve_effective_provider(
            provider=provider,
            model_url=model_url,
            model_name=model_name,
        )
        is_system_model = ChatService._is_system_model(model_config)

        if is_workflow:
            temp_raw = model_config["temperature"]
            max_len_raw = model_config["max_length"]
            top_p_raw = model_config["top_P"]
        else:
            temp_raw = model_config.get("temperature", -1)
            max_len_raw = model_config.get("max_length", -1)
            top_p_raw = model_config.get("top_P", -1)

        if is_system_model:
            tuned = ChatService._tuned_generation_defaults(
                provider=effective_provider,
                model_name=model_name,
            )
            if temp_raw == -1:
                temp_raw = float(tuned.get("temperature", 0.2))
            if max_len_raw == -1:
                max_len_raw = int(tuned.get("max_tokens", 4096))
            # Only apply top_p if we explicitly set it to a non-sentinel value.
            tuned_top_p = tuned.get("top_p", -1)
            if top_p_raw == -1 and isinstance(tuned_top_p, (int, float)) and tuned_top_p != -1:
                top_p_raw = float(tuned_top_p)

        temperature = ChatService._normalize_temperature(float(temp_raw))
        max_length = ChatService._normalize_max_length(int(max_len_raw))
        top_P = ChatService._normalize_top_p(float(top_p_raw))
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
        distinct_files = 0
        distinct_pages = 0

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
                retrieval_mode = getattr(settings, "rag_retrieval_mode", "dense")
                # Backward compatibility: older deployments only used rag_hybrid_enabled.
                if retrieval_mode == "dense" and getattr(
                    settings, "rag_hybrid_enabled", False
                ):
                    retrieval_mode = "hybrid"

                sparse_vecs = []
                sparse_query = None
                if query_vecs and retrieval_mode in [
                    "hybrid",
                    "sparse_then_rerank",
                    "dual_then_rerank",
                ]:
                    try:
                        sparse_result = await get_sparse_embeddings(
                            [user_message_content.user_message]
                        )
                        if sparse_result and len(sparse_result) > 0:
                            sparse_query = sparse_result[0]
                            if retrieval_mode == "hybrid":
                                # Hybrid search uses a per-token query list, so we replicate the single sparse vector.
                                sparse_vecs = [sparse_query] * len(query_vecs)
                    except Exception as e:
                        logger.warning(
                            f"Sparse embedding failed, falling back to dense-only: {e}"
                        )

                if query_vecs:
                    # Prepare search data based on retrieval mode.
                    # - dense: query_vecs only
                    # - hybrid: dense_vecs + sparse_vecs (length-matched)
                    # - sparse_then_rerank: sparse recall on page-level collection -> exact MaxSim rerank on patch collection
                    # - dual_then_rerank: sparse page recall + dense patch recall -> fuse candidates -> exact MaxSim rerank
                    if (
                        retrieval_mode in ["sparse_then_rerank", "dual_then_rerank"]
                        and sparse_query
                    ):
                        search_data = {
                            "mode": retrieval_mode,
                            "dense_vecs": query_vecs,
                            "sparse_query": sparse_query,
                        }
                    elif sparse_vecs:
                        search_data = {
                            "dense_vecs": query_vecs,
                            "sparse_vecs": sparse_vecs,
                        }
                    else:
                        search_data = query_vecs

                    for base in bases:
                        collection_name = to_milvus_collection_name(base["baseId"])
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
                    distinct_files = len(
                        {str(s.get("file_id")) for s in cut_score if s.get("file_id") is not None}
                    )
                    distinct_pages = len(
                        {
                            (str(s.get("file_id")), int(s.get("page_number")))
                            for s in cut_score
                            if s.get("file_id") is not None and s.get("page_number") is not None
                        }
                    )

                    # Batch fetch metadata (eliminates N+1 query pattern)
                    if cut_score:
                        t_start = time.perf_counter()
                        # In some deployments (notably thesis), Mongo may not contain file/image metadata yet.
                        # We still want to leverage extracted text for RAG, so we prefetch page previews
                        # from the page-level sparse collection (if present) for fallback context.
                        previews_by_collection: dict[
                            str, dict[tuple[str, int], str]
                        ] = {}
                        try:
                            pairs_by_collection: dict[str, list[tuple[str, int]]] = {}
                            seen: set[tuple[str, str, int]] = set()
                            for s in cut_score:
                                coll = s.get("collection_name") or ""
                                fid = s.get("file_id")
                                pn = s.get("page_number")
                                if not coll or fid is None or pn is None:
                                    continue
                                try:
                                    pn_i = int(pn)
                                except Exception:
                                    continue
                                key = (coll, str(fid), pn_i)
                                if key in seen:
                                    continue
                                seen.add(key)
                                pairs_by_collection.setdefault(coll, []).append(
                                    (str(fid), pn_i)
                                )

                            for coll, pairs in pairs_by_collection.items():
                                previews_by_collection[coll] = (
                                    vector_db_client.get_page_previews(coll, pairs)
                                    or {}
                                )
                        except Exception:
                            previews_by_collection = {}

                        file_image_pairs = [
                            (score["file_id"], score["image_id"]) for score in cut_score
                        ]
                        file_infos = await repo_manager.file.get_files_and_images_batch(
                            file_image_pairs
                        )
                        t_meta_s += time.perf_counter() - t_start

                        fallback_text_used = 0
                        fallback_text_cap = min(
                            int(getattr(settings, "rag_fallback_text_cap", 20)),
                            int(top_K) if top_K and top_K > 0 else int(getattr(settings, "rag_fallback_text_cap", 20)),
                        )

                        for score, file_and_image_info in zip(cut_score, file_infos):
                            if file_and_image_info.get("status") != "success":
                                logger.warning(
                                    "RAG hit skipped (metadata mismatch): "
                                    f"collection={score.get('collection_name')} "
                                    f"file_id={score.get('file_id')} "
                                    f"image_id={score.get('image_id')} "
                                    f"page_number={score.get('page_number')}"
                                )

                                # Thesis fallback: use extracted page text (if available) and generate
                                # browser-viewable reference URLs from local PDFs.
                                if fallback_text_used < fallback_text_cap:
                                    try:
                                        coll = score.get("collection_name") or ""
                                        fid = str(score.get("file_id") or "")
                                        pn = int(score.get("page_number") or 0)
                                        preview = (
                                            previews_by_collection.get(coll, {}).get((fid, pn))
                                            or ""
                                        )
                                        if preview:
                                            filename = score.get("filename") or fid
                                            # Use relative URLs so this works behind nginx reverse proxy
                                            # regardless of SERVER_IP (local dev vs deployed domain).
                                            api_base = settings.api_version_url
                                            thesis_pdf_url = (
                                                f"{api_base}/thesis/pdf?"
                                                + urlencode({"file_id": fid})
                                            )
                                            thesis_image_url = (
                                                f"{api_base}/thesis/page-image?"
                                                + urlencode(
                                                    {"file_id": fid, "page_number": pn, "dpi": 150}
                                                )
                                            )

                                            # Provide structured citation metadata for the UI.
                                            file_used.append(
                                                {
                                                    "score": score.get("score", 0.0),
                                                    # No Mongo knowledge_db_id in this environment; keep stable ID.
                                                    "knowledge_db_id": coll or "thesis",
                                                    "file_name": filename,
                                                    "file_id": fid,
                                                    "page_number": pn,
                                                    "image_id": score.get("image_id"),
                                                    "text_preview": preview[:1200],
                                                    "image_url": thesis_image_url,
                                                    "file_url": thesis_pdf_url,
                                                }
                                            )

                                            # Keep the injected text small to avoid blowing up prompt tokens.
                                            injected = preview[:1200]
                                            content.append(
                                                {
                                                    "type": "text",
                                                    "text": (
                                                        f"[RAG Source] {filename} (page {pn})\n"
                                                        f"{injected}"
                                                    ),
                                                }
                                            )
                                            rag_hits += 1
                                            fallback_text_used += 1
                                    except Exception:
                                        pass
                                continue

                            # Optional: attach extracted text preview (if available) even when Mongo matches.
                            try:
                                coll = score.get("collection_name") or ""
                                fid = str(score.get("file_id") or "")
                                pn = int(score.get("page_number") or 0)
                                preview = (
                                    previews_by_collection.get(coll, {}).get((fid, pn)) or ""
                                )
                            except Exception:
                                preview = ""

                            file_used.append(
                                {
                                    "score": score["score"],
                                    "knowledge_db_id": file_and_image_info[
                                        "knowledge_db_id"
                                    ],
                                    "file_name": file_and_image_info["file_name"],
                                    "file_id": score.get("file_id"),
                                    "page_number": score.get("page_number"),
                                    "image_id": score.get("image_id"),
                                    "text_preview": preview[:1200] if preview else "",
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
                f"top_K={top_K} "
                f"score_threshold={score_threshold} "
                f"retrieval_mode={getattr(settings, 'rag_retrieval_mode', 'dense')} "
                f"distinct_files={distinct_files} "
                f"distinct_pages={distinct_pages} "
                f"total_s={(time.perf_counter() - t0):.3f} "
                f"mode={'workflow' if is_workflow else 'rag'}"
            )

        # Emit retrieval evidence early (before provider/client init).
        #
        # Rationale:
        # - For RAG debugging, clients need `file_used` even when the LLM provider
        #   is misconfigured or temporarily unavailable.
        # - This makes the pipeline observable end-to-end without depending on the
        #   LLM call succeeding.
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
                # New: auto-detect provider from model name (or use explicit provider)
                client = get_llm_client(model_name, api_key=api_key, provider=provider)
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
        optional_args = ChatService._build_optional_openai_args(
            model_name=model_name,
            provider=effective_provider,
            temperature=temperature,
            max_length=max_length,
            top_p=top_P,
        )

        # Detect provider to handle auto-detection cases (where model_url is None)
        detected_provider = ProviderClient.get_provider_for_model(model_name)
        provider_for_stream = effective_provider or detected_provider

        # Fail fast if provider detection fails and no explicit URL provided
        if not detected_provider and not model_url:
            supported = ProviderClient.get_all_providers()
            raise ValueError(
                f"Cannot detect provider for model '{model_name}'. "
                f"Either use a known model name or provide an explicit model_url. "
                f"Supported providers: {supported}"
            )

        logger.debug(
            f"model_name={model_name}, detected_provider={detected_provider}, model_url={model_url}"
        )

        # Zhipu API doesn't support stream_options parameter
        if model_url:
            is_zhipu = "glm" in model_name.lower() or "zhipu" in model_url.lower()
        else:
            # Strictly identify Zhipu/Z.ai providers to suppress stream_options
            # Sending stream_options to Zhipu causes API errors/empty responses
            is_zhipu = provider_for_stream in ("zhipu", "zhipu-coding", "zai")

        # Z.ai accepts lowercase model names (glm-4.7-flash)
        if model_url:
            is_zai = "z.ai" in model_url.lower()
        else:
            is_zai = provider_for_stream == "zai"

        # Map legacy/alias model name for provider API calls
        api_model_name = resolve_api_model_name(model_name)

        logger.debug(
            f"is_zhipu={is_zhipu}, is_zai={is_zai}, api_model_name={api_model_name}"
        )

        stream_kwargs: Dict[str, Any] = {"stream": True}
        if not is_zhipu:
            stream_kwargs["stream_options"] = {"include_usage": True}

        logger.debug(f"stream_kwargs={stream_kwargs}")

        # Call API with streaming
        try:
            response = await client.chat.completions.create(
                model=api_model_name,
                messages=cast(Any, send_messages),  # type: ignore[arg-type]
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

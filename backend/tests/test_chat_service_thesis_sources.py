import json

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sparse_dual_modes_enforce_min_top_k_for_chat_rag():
    """In thesis sparse/dual modes, tiny top_K values cause '2 sources only'.

    ChatService should mirror the search-preview endpoint behavior by enforcing
    a minimum retrieval breadth (settings.rag_search_limit_min) when
    retrieval_mode is sparse_then_rerank or dual_then_rerank.
    """
    from unittest.mock import AsyncMock, patch

    from app.core.config import settings
    from app.core.llm.chat_service import ChatService
    from app.models.shared import UserMessage

    user_msg = UserMessage(
        conversation_id="conv_1",
        parent_id="",
        user_message="introduction",
        temp_db_id="",
    )

    # Explicitly low top_K to verify we bump it up in sparse/dual modes.
    model_config = {
        "model_name": "deepseek-chat",
        "model_url": "",
        "api_key": "fake_key_for_test_only",
        "base_used": [{"baseId": "thesis_dummy"}],
        "provider": "deepseek",
        "system_prompt": "",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": 2,
        "score_threshold": -1,
    }

    class _FakeFileRepo:
        async def get_files_and_images_batch(self, pairs):
            return [{"status": "failed"} for _ in pairs]

    class _FakeRepoManager:
        file = _FakeFileRepo()

    async def _fake_get_repo_manager():
        return _FakeRepoManager()

    called = {"topk": None}

    def _fake_search(collection_name, data=None, topk=None, **kwargs):
        called["topk"] = topk
        # Return a couple of minimal "page-level" hits.
        return [
            {"score": 1.0, "file_id": "f1", "page_number": 1, "image_id": "i1"},
            {"score": 0.9, "file_id": "f2", "page_number": 2, "image_id": "i2"},
        ]

    with patch.object(settings, "rag_retrieval_mode", "dual_then_rerank"), patch.object(
        settings, "rag_search_limit_min", 50
    ), patch.object(settings, "rag_top_k_cap", 120), patch(
        "app.core.llm.chat_service.get_repository_manager",
        new=_fake_get_repo_manager,
    ), patch(
        "app.core.llm.chat_service.get_embeddings_from_httpx",
        new=AsyncMock(return_value=[[0.0] * 128]),
    ), patch(
        "app.core.llm.chat_service.get_sparse_embeddings",
        new=AsyncMock(return_value=[{1: 1.0}]),
    ), patch(
        "app.core.llm.chat_service.vector_db_client.search",
        new=_fake_search,
    ), patch(
        "app.core.llm.chat_service.vector_db_client.get_page_previews",
        new=lambda *_args, **_kwargs: {},
    ), patch(
        "app.core.llm.chat_service.get_llm_client",
        side_effect=ValueError("provider init failed"),
    ):
        gen = ChatService.create_chat_stream(
            user_msg,
            model_config=model_config,
            message_id="msg_1",
            is_workflow=True,
        )

        first = await gen.__anext__()
        msg1 = json.loads(first)
        assert msg1["type"] == "file_used"
        assert called["topk"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_thesis_fallback_emits_file_used_even_without_text_preview():
    """Even if Mongo metadata and sparse page previews are missing, emit References.

    This ensures the frontend can still render the References section (page image + PDF URL),
    which is required for debugging and for thesis deployments without Mongo-side file metadata.
    """
    from unittest.mock import AsyncMock, patch

    from app.core.config import settings
    from app.core.llm.chat_service import ChatService
    from app.models.shared import UserMessage

    user_msg = UserMessage(
        conversation_id="conv_1",
        parent_id="",
        user_message="introduction",
        temp_db_id="",
    )

    model_config = {
        "model_name": "deepseek-chat",
        "model_url": "",
        "api_key": "fake_key_for_test_only",
        "base_used": [{"baseId": "thesis_dummy"}],
        "provider": "deepseek",
        "system_prompt": "",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": 2,
        "score_threshold": -1,
    }

    class _FakeFileRepo:
        async def get_files_and_images_batch(self, pairs):
            return [{"status": "failed"} for _ in pairs]

    class _FakeRepoManager:
        file = _FakeFileRepo()

    async def _fake_get_repo_manager():
        return _FakeRepoManager()

    def _fake_search(collection_name, data=None, topk=None, **kwargs):
        return [
            {"score": 1.0, "file_id": "f1", "page_number": 1, "image_id": "i1"},
            {"score": 0.9, "file_id": "f2", "page_number": 2, "image_id": "i2"},
        ]

    with patch.object(settings, "rag_retrieval_mode", "dual_then_rerank"), patch.object(
        settings, "rag_search_limit_min", 50
    ), patch.object(
        settings, "api_version_url", "/api/v1"
    ), patch(
        "app.core.llm.chat_service.get_repository_manager",
        new=_fake_get_repo_manager,
    ), patch(
        "app.core.llm.chat_service.get_embeddings_from_httpx",
        new=AsyncMock(return_value=[[0.0] * 128]),
    ), patch(
        "app.core.llm.chat_service.get_sparse_embeddings",
        new=AsyncMock(return_value=[{1: 1.0}]),
    ), patch(
        "app.core.llm.chat_service.vector_db_client.search",
        new=_fake_search,
    ), patch(
        "app.core.llm.chat_service.vector_db_client.get_page_previews",
        new=lambda *_args, **_kwargs: {},
    ), patch(
        "app.core.llm.chat_service.get_llm_client",
        side_effect=ValueError("provider init failed"),
    ):
        gen = ChatService.create_chat_stream(
            user_msg,
            model_config=model_config,
            message_id="msg_1",
            is_workflow=True,
        )

        first = await gen.__anext__()
        msg1 = json.loads(first)
        assert msg1["type"] == "file_used"
        assert isinstance(msg1.get("data"), list)
        assert len(msg1["data"]) >= 1

        item = msg1["data"][0]
        assert item.get("file_id")
        assert int(item.get("page_number") or 0) > 0
        assert item.get("image_url", "").startswith("/api/v1/thesis/page-image?")
        assert item.get("file_url", "").startswith("/api/v1/thesis/pdf?")
        assert item.get("text_preview", "") == ""


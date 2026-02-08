import json

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_file_used_emitted_before_llm_client_init():
    """file_used must be emitted even when the LLM provider/client init fails.

    This keeps the thesis RAG pipeline debuggable end-to-end without relying on
    provider availability/keys.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.core.llm.chat_service import ChatService
    from app.models.shared import UserMessage

    # Arrange: workflow mode avoids DB model_config lookup.
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
        "system_prompt": "",
        "temperature": -1,
        "max_length": -1,
        "top_P": -1,
        "top_K": 2,
        "score_threshold": -1,
    }

    # Stub repositories: metadata lookup fails to force thesis fallback path.
    class _FakeFileRepo:
        async def get_files_and_images_batch(self, pairs):
            return [{"status": "failed"} for _ in pairs]

    class _FakeRepoManager:
        file = _FakeFileRepo()

    async def _fake_get_repo_manager():
        return _FakeRepoManager()

    # Patch vector search and page previews.
    def _fake_search(*args, **kwargs):
        # Minimal vector hit list (already page-level)
        return [
            {"score": 1.0, "file_id": "f1", "page_number": 1, "image_id": "i1"},
            {"score": 0.9, "file_id": "f2", "page_number": 2, "image_id": "i2"},
        ]

    def _fake_get_page_previews(collection_name, pairs):
        return {(fid, pn): f"preview {fid} {pn}" for fid, pn in pairs}

    # Build a mock that replaces the entire vector_db_client proxy object.
    # Patching individual attributes on the proxy triggers __getattr__ → Milvus init.
    mock_vdb = MagicMock()
    mock_vdb.search = _fake_search
    mock_vdb.get_page_previews = _fake_get_page_previews

    with (
        patch(
            "app.core.llm.chat_service.get_repository_manager",
            new=_fake_get_repo_manager,
        ),
        patch(
            "app.core.llm.chat_service.get_embeddings_from_httpx",
            new=AsyncMock(return_value=[[0.0] * 128]),
        ),
        patch(
            "app.core.llm.chat_service.get_sparse_embeddings",
            new=AsyncMock(return_value=[{1: 1.0}]),
        ),
        patch(
            "app.core.llm.chat_service.vector_db_client",
            new=mock_vdb,
        ),
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
        assert len(msg1["data"]) > 0

        second = await gen.__anext__()
        msg2 = json.loads(second)
        assert msg2["type"] in ("user_images", "text")

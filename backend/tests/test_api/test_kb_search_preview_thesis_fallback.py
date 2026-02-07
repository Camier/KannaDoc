import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.unit
class TestKbSearchPreviewThesisFallback:
    @pytest.mark.asyncio
    async def test_search_preview_thesis_falls_back_to_page_image_url_when_metadata_missing(
        self, client, monkeypatch
    ):
        """
        Thesis KBs can have Milvus `file_id` values that do not exist in Mongo.
        In that case, search-preview must still return an image URL usable by the UI.
        """
        pytest.importorskip("fastapi")

        from app.main import app
        from app.api.endpoints import knowledge_base as kb_ep
        from app.db.repositories.repository_manager import get_repository_manager

        fake_repo_manager = SimpleNamespace(
            knowledge_base=SimpleNamespace(
                get_knowledge_base_by_id=AsyncMock(return_value={"_id": "thesis_test"})
            ),
            file=SimpleNamespace(
                # Pretend Mongo metadata lookup failed for this result.
                get_files_and_images_batch=AsyncMock(return_value=[{"status": "failed"}])
            ),
        )

        async def override_repo_manager():
            return fake_repo_manager

        app.dependency_overrides[get_repository_manager] = override_repo_manager
        try:
            monkeypatch.setattr(
                kb_ep,
                "get_embeddings_from_httpx",
                AsyncMock(return_value=[[[0.0, 1.0, 0.0, 0.0]]]),
            )
            monkeypatch.setattr(
                kb_ep,
                "get_sparse_embeddings",
                AsyncMock(return_value=[{1: 0.1}]),
            )

            kb_ep.vector_db_client.check_collection = MagicMock(return_value=True)
            kb_ep.vector_db_client.load_collection = MagicMock()

            search_mock = MagicMock(
                return_value=[
                    {
                        "file_id": "1998 - al. - Depression in Parkinsons disease an EEG frequency analysis study",
                        "page_number": 1,
                        "image_id": "patch_debug_1",
                        "score": 12.3,
                    }
                ]
            )
            kb_ep.vector_db_client.search = search_mock

            resp = await client.post(
                "/api/v1/kb/knowledge-base/thesis_test/search-preview",
                json={"query": "test", "top_k": 10, "retrieval_mode": "dual_then_rerank"},
            )
            assert resp.status_code == 200

            payload = resp.json()
            assert payload["total_results"] == 1

            # In sparse/dual modes, search-preview normalizes top_k up to the thesis minimum (default 50).
            assert search_mock.call_args.kwargs["topk"] == 50

            item = payload["results"][0]
            assert item["filename"].startswith("1998 - al.")
            assert item["minio_url"].startswith("/api/v1/thesis/page-image?")
            assert "page_number=1" in item["minio_url"]
            assert "dpi=150" in item["minio_url"]
        finally:
            app.dependency_overrides.pop(get_repository_manager, None)


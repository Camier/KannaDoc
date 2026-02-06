"""Tests for evaluation API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytest.importorskip("fastapi")

from fastapi import HTTPException
pytestmark = pytest.mark.integration


class TestCreateDatasetEndpoint:
    """Tests for POST /api/v1/eval/datasets"""

    @pytest.fixture
    def mock_mongo(self):
        mongo = MagicMock()
        mongo.db = MagicMock()
        return mongo

    @pytest.mark.asyncio
    async def test_create_dataset_success(self, mock_mongo):
        from app.api.endpoints.eval import (
            create_evaluation_dataset,
            CreateDatasetRequest,
        )

        request = CreateDatasetRequest(
            name="test-dataset",
            kb_id="kb-123",
            query_count=10,
            label_with_llm=False,
        )

        mock_dataset = MagicMock()
        mock_dataset.id = "ds-456"
        mock_dataset.name = "test-dataset"
        mock_dataset.kb_id = "kb-123"
        mock_dataset.queries = [MagicMock() for _ in range(10)]
        mock_dataset.created_at = MagicMock()
        mock_dataset.created_at.isoformat.return_value = "2026-02-06T12:00:00"

        with patch(
            "app.api.endpoints.eval.generate_queries_from_corpus",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = [{"query_text": f"q{i}"} for i in range(10)]
            with patch(
                "app.api.endpoints.eval.get_mongo", new_callable=AsyncMock
            ) as mock_get_mongo:
                mock_get_mongo.return_value = mock_mongo
                with patch(
                    "app.api.endpoints.eval.create_dataset", new_callable=AsyncMock
                ) as mock_create:
                    mock_create.return_value = mock_dataset

                    result = await create_evaluation_dataset(request)

                    assert result.id == "ds-456"
                    assert result.name == "test-dataset"
                    assert result.query_count == 10

    @pytest.mark.asyncio
    async def test_create_dataset_empty_kb_returns_400(self, mock_mongo):
        from app.api.endpoints.eval import (
            create_evaluation_dataset,
            CreateDatasetRequest,
        )

        request = CreateDatasetRequest(
            name="test-dataset",
            kb_id="empty-kb",
            query_count=10,
        )

        with patch(
            "app.api.endpoints.eval.generate_queries_from_corpus",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = []

            with pytest.raises(HTTPException) as exc_info:
                await create_evaluation_dataset(request)

            assert exc_info.value.status_code == 400
            assert "No documents found" in str(exc_info.value.detail)


class TestGetDatasetsEndpoint:
    """Tests for GET /api/v1/eval/datasets"""

    @pytest.mark.asyncio
    async def test_list_datasets_success(self):
        from app.api.endpoints.eval import get_datasets

        mock_dataset = MagicMock()
        mock_dataset.id = "ds-123"
        mock_dataset.name = "test"
        mock_dataset.kb_id = "kb-1"
        mock_dataset.queries = []
        mock_dataset.created_at.isoformat.return_value = "2026-02-06T12:00:00"

        mock_mongo = MagicMock()
        mock_mongo.db = MagicMock()

        with patch(
            "app.api.endpoints.eval.get_mongo", new_callable=AsyncMock
        ) as mock_get_mongo:
            mock_get_mongo.return_value = mock_mongo
            with patch(
                "app.api.endpoints.eval.list_datasets", new_callable=AsyncMock
            ) as mock_list:
                mock_list.return_value = [mock_dataset]

                result = await get_datasets(kb_id="kb-1")

                assert len(result.datasets) == 1
                assert result.datasets[0].id == "ds-123"


class TestGetDatasetDetailsEndpoint:
    """Tests for GET /api/v1/eval/datasets/{dataset_id}"""

    @pytest.mark.asyncio
    async def test_get_dataset_not_found_returns_404(self):
        from app.api.endpoints.eval import get_dataset_details

        mock_mongo = MagicMock()
        mock_mongo.db = MagicMock()

        with patch(
            "app.api.endpoints.eval.get_mongo", new_callable=AsyncMock
        ) as mock_get_mongo:
            mock_get_mongo.return_value = mock_mongo
            with patch(
                "app.api.endpoints.eval.get_dataset", new_callable=AsyncMock
            ) as mock_get:
                mock_get.return_value = None

                with pytest.raises(HTTPException) as exc_info:
                    await get_dataset_details("nonexistent-id")

                assert exc_info.value.status_code == 404


class TestExecuteEvaluationEndpoint:
    """Tests for POST /api/v1/eval/run"""

    @pytest.mark.asyncio
    async def test_run_evaluation_success(self):
        from app.api.endpoints.eval import execute_evaluation, RunEvaluationRequest

        request = RunEvaluationRequest(
            dataset_id="ds-123",
            config={"top_k": 5},
        )

        mock_run = MagicMock()
        mock_run.id = "run-789"
        mock_run.dataset_id = "ds-123"
        mock_run.config = {"top_k": 5}
        mock_run.metrics = {
            "queries_total": 10,
            "queries_processed": 10,
            "queries_failed": 0,
            "queries_with_labels": 10,
            "mrr": 0.75,
            "ndcg": 0.80,
            "precision": 0.60,
            "recall": 0.70,
        }
        mock_run.created_at.isoformat.return_value = "2026-02-06T12:00:00"

        mock_mongo = MagicMock()
        mock_mongo.db = MagicMock()

        with patch(
            "app.api.endpoints.eval.get_mongo", new_callable=AsyncMock
        ) as mock_get_mongo:
            mock_get_mongo.return_value = mock_mongo
            with patch(
                "app.api.endpoints.eval.run_evaluation", new_callable=AsyncMock
            ) as mock_eval:
                mock_eval.return_value = mock_run

                result = await execute_evaluation(request)

                assert result.id == "run-789"
                assert result.metrics.mrr == 0.75
                assert result.metrics.recall == 0.70


class TestGetRunResultsEndpoint:
    """Tests for GET /api/v1/eval/runs/{run_id}"""

    @pytest.mark.asyncio
    async def test_get_run_not_found_returns_404(self):
        from app.api.endpoints.eval import get_run_results

        mock_mongo = MagicMock()
        mock_mongo.db = MagicMock()

        with patch(
            "app.api.endpoints.eval.get_mongo", new_callable=AsyncMock
        ) as mock_get_mongo:
            mock_get_mongo.return_value = mock_mongo
            with patch("app.api.endpoints.eval.EvalRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.get_run = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo

                with pytest.raises(HTTPException) as exc_info:
                    await get_run_results("nonexistent-run")

                assert exc_info.value.status_code == 404


class TestGetRunsForDatasetEndpoint:
    """Tests for GET /api/v1/eval/runs"""

    @pytest.mark.asyncio
    async def test_list_runs_success(self):
        from app.api.endpoints.eval import get_runs_for_dataset
        from datetime import datetime

        mock_mongo = MagicMock()
        mock_mongo.db = MagicMock()

        mock_run_dict = {
            "_id": "run-1",
            "dataset_id": "ds-1",
            "config": {"top_k": 5},
            "metrics": {
                "queries_total": 10,
                "queries_processed": 10,
                "queries_failed": 0,
                "queries_with_labels": 10,
                "mrr": 0.75,
                "ndcg": 0.80,
                "precision": 0.60,
                "recall": 0.70,
            },
            "created_at": datetime(2026, 2, 6, 12, 0, 0),
        }

        async def mock_cursor_iter():
            yield mock_run_dict

        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__aiter__ = lambda self: mock_cursor_iter()

        with patch(
            "app.api.endpoints.eval.get_mongo", new_callable=AsyncMock
        ) as mock_get_mongo:
            mock_get_mongo.return_value = mock_mongo
            with patch("app.api.endpoints.eval.EvalRepository") as mock_repo_class:
                mock_repo = MagicMock()
                mock_repo.runs_collection.find.return_value = mock_cursor
                mock_repo_class.return_value = mock_repo

                result = await get_runs_for_dataset(dataset_id="ds-1")

                assert len(result.runs) == 1
                assert result.runs[0].id == "run-1"

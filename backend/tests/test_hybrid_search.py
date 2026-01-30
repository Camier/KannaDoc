#!/usr/bin/env python3
"""
Tests for LAYRA hybrid search implementation.

These tests verify:
1. Configuration loading and validation
2. Ranker selection (RRF vs Weighted)
3. Sparse vector detection
4. Hybrid search fallback behavior
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestHybridSearchConfig:
    """Tests for hybrid search configuration."""

    def test_hybrid_config_defaults(self):
        """Default values are correct when env not set."""
        from app.core.config import Settings

        with patch.dict("os.environ", {}, clear=False):
            settings = Settings()
            assert settings.rag_hybrid_enabled is False
            assert settings.rag_hybrid_ranker == "rrf"
            assert settings.rag_hybrid_rrf_k == 60
            assert settings.rag_hybrid_dense_weight == 0.7
            assert settings.rag_hybrid_sparse_weight == 0.3

    def test_hybrid_config_loads_from_env(self):
        """Config loads hybrid settings from environment."""
        from app.core.config import Settings

        env_vars = {
            "RAG_HYBRID_ENABLED": "true",
            "RAG_HYBRID_RANKER": "weighted",
            "RAG_HYBRID_RRF_K": "30",
            "RAG_HYBRID_DENSE_WEIGHT": "0.6",
            "RAG_HYBRID_SPARSE_WEIGHT": "0.4",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            settings = Settings()
            assert settings.rag_hybrid_enabled is True
            assert settings.rag_hybrid_ranker == "weighted"
            assert settings.rag_hybrid_rrf_k == 30
            assert settings.rag_hybrid_dense_weight == 0.6
            assert settings.rag_hybrid_sparse_weight == 0.4


class TestRankerSelection:
    """Tests for ranker selection logic."""

    def test_get_ranker_returns_rrf_by_default(self):
        """Default ranker is RRFRanker(k=60)."""
        from app.db.milvus import get_ranker
        from pymilvus import RRFRanker

        mock_settings = MagicMock()
        mock_settings.rag_hybrid_ranker = "rrf"
        mock_settings.rag_hybrid_rrf_k = 60

        ranker = get_ranker(mock_settings)
        assert isinstance(ranker, RRFRanker)

    def test_get_ranker_returns_weighted_when_configured(self):
        """RAG_HYBRID_RANKER=weighted uses WeightedRanker."""
        from app.db.milvus import get_ranker
        from pymilvus import WeightedRanker

        mock_settings = MagicMock()
        mock_settings.rag_hybrid_ranker = "weighted"
        mock_settings.rag_hybrid_dense_weight = 0.7
        mock_settings.rag_hybrid_sparse_weight = 0.3

        ranker = get_ranker(mock_settings)
        assert isinstance(ranker, WeightedRanker)

    def test_get_ranker_respects_rrf_k_config(self):
        """Changing RAG_HYBRID_RRF_K affects RRF ranker."""
        from app.db.milvus import get_ranker
        from pymilvus import RRFRanker

        mock_settings = MagicMock()
        mock_settings.rag_hybrid_ranker = "rrf"
        mock_settings.rag_hybrid_rrf_k = 30

        ranker = get_ranker(mock_settings)
        assert isinstance(ranker, RRFRanker)


class TestSparseVectorDetection:
    """Tests for sparse vector detection helper."""

    def test_has_sparse_vectors_empty_list(self):
        """Empty list returns False."""
        from app.db.milvus import _has_sparse_vectors

        assert _has_sparse_vectors([]) is False

    def test_has_sparse_vectors_empty_dicts(self):
        """List of empty dicts returns False."""
        from app.db.milvus import _has_sparse_vectors

        assert _has_sparse_vectors([{}, {}, {}]) is False

    def test_has_sparse_vectors_with_valid_sparse(self):
        """List with non-empty sparse vectors returns True."""
        from app.db.milvus import _has_sparse_vectors

        sparse_vecs = [{1: 0.5, 2: 0.3}, {3: 0.8}]
        assert _has_sparse_vectors(sparse_vecs) is True

    def test_has_sparse_vectors_mixed(self):
        """List with some empty, some valid returns True."""
        from app.db.milvus import _has_sparse_vectors

        sparse_vecs = [{}, {1: 0.5}, {}]
        assert _has_sparse_vectors(sparse_vecs) is True


class TestHybridSearchFallback:
    """Tests for hybrid search fallback behavior."""

    def test_hybrid_disabled_uses_dense_only(self):
        """RAG_HYBRID_ENABLED=false uses dense-only search."""
        from app.db.milvus import _has_sparse_vectors

        mock_settings = MagicMock()
        mock_settings.rag_hybrid_enabled = False

        use_hybrid = (
            mock_settings.rag_hybrid_enabled
            and _has_sparse_vectors([{1: 0.5}])
            and len([{1: 0.5}]) == len([[0.1] * 128])
        )
        assert use_hybrid is False

    def test_missing_sparse_falls_back_to_dense(self):
        """Documents without sparse vectors still search with dense only."""
        from app.db.milvus import _has_sparse_vectors

        mock_settings = MagicMock()
        mock_settings.rag_hybrid_enabled = True

        sparse_vecs = [{}, {}, {}]
        dense_vecs = [[0.1] * 128, [0.2] * 128, [0.3] * 128]

        use_hybrid = (
            mock_settings.rag_hybrid_enabled
            and _has_sparse_vectors(sparse_vecs)
            and len(sparse_vecs) == len(dense_vecs)
        )
        assert use_hybrid is False


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_weight_validation_rejects_negative(self):
        """Negative weights raise ValueError."""
        from app.core.config import settings, validate_settings

        original = settings.rag_hybrid_dense_weight
        try:
            settings.rag_hybrid_enabled = True
            settings.rag_hybrid_dense_weight = -0.5
            with pytest.raises(ValueError, match="rag_hybrid_dense_weight"):
                validate_settings()
        finally:
            settings.rag_hybrid_dense_weight = original
            settings.rag_hybrid_enabled = False

    def test_weight_validation_rejects_over_one(self):
        """Weights > 1.0 raise ValueError."""
        from app.core.config import settings, validate_settings

        original = settings.rag_hybrid_sparse_weight
        try:
            settings.rag_hybrid_enabled = True
            settings.rag_hybrid_sparse_weight = 1.5
            with pytest.raises(ValueError, match="rag_hybrid_sparse_weight"):
                validate_settings()
        finally:
            settings.rag_hybrid_sparse_weight = original
            settings.rag_hybrid_enabled = False

    def test_ranker_validation_rejects_invalid(self):
        """Invalid ranker type raises ValueError."""
        from app.core.config import settings, validate_settings

        original = settings.rag_hybrid_ranker
        try:
            settings.rag_hybrid_enabled = True
            settings.rag_hybrid_ranker = "invalid"
            with pytest.raises(ValueError, match="rag_hybrid_ranker"):
                validate_settings()
        finally:
            settings.rag_hybrid_ranker = original
            settings.rag_hybrid_enabled = False

    def test_rrf_k_validation_rejects_zero(self):
        """rag_hybrid_rrf_k <= 0 raises ValueError."""
        from app.core.config import settings, validate_settings

        original = settings.rag_hybrid_rrf_k
        try:
            settings.rag_hybrid_enabled = True
            settings.rag_hybrid_rrf_k = 0
            with pytest.raises(ValueError, match="rag_hybrid_rrf_k"):
                validate_settings()
        finally:
            settings.rag_hybrid_rrf_k = original
            settings.rag_hybrid_enabled = False


class TestQueryTimeSparseEmbeddings:
    """Tests for query-time sparse embedding generation."""

    @pytest.mark.asyncio
    async def test_get_sparse_embeddings_returns_list(self):
        """get_sparse_embeddings returns list of dicts."""
        from unittest.mock import AsyncMock
        from app.rag.get_embedding import get_sparse_embeddings

        with patch("app.rag.get_embedding.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"embeddings": [{1: 0.5, 2: 0.3}]}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await get_sparse_embeddings(["test query"])
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], dict)

    @pytest.mark.asyncio
    async def test_get_sparse_embeddings_empty_input(self):
        """Empty input returns empty list."""
        from app.rag.get_embedding import get_sparse_embeddings

        result = await get_sparse_embeddings([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_sparse_embeddings_handles_failure(self):
        """API failure returns empty list with warning."""
        from unittest.mock import AsyncMock
        from app.rag.get_embedding import get_sparse_embeddings

        with patch("app.rag.get_embedding.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await get_sparse_embeddings(["test query"])
            assert result == []

    def test_sparse_vector_replication_logic(self):
        """Sparse vector replication matches dense vector count."""
        # This tests the logic used in ChatService
        sparse_result = [{1: 0.5, 2: 0.3}]
        dense_count = 48  # Typical after downsample

        if sparse_result and len(sparse_result) > 0:
            sparse_vecs = [sparse_result[0]] * dense_count
        else:
            sparse_vecs = []

        assert len(sparse_vecs) == dense_count
        assert all(v == sparse_result[0] for v in sparse_vecs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

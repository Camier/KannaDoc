"""
Baseline tests for model configuration system.

This test module captures the current behavior of:
1. ChatService normalizers for model parameters (tested via isolated implementations)
2. Pydantic validation in ModelConfigBase
3. Cache invalidation on model_config writes
"""

import pytest
from unittest.mock import MagicMock
import sys
from typing import Any

pytestmark = pytest.mark.unit


# ==============================================================================
# FIXTURES
# ==============================================================================


def _require_chat_service_deps() -> None:
    pytest.importorskip("circuitbreaker")
    pytest.importorskip("openai")


@pytest.fixture
def clean_env(monkeypatch):
    env_vars = [
        "ZAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "CLIPROXYAPI_BASE_URL",
        "CLIPROXYAPI_API_KEY",
        "OLLAMA_CLOUD_API_KEY",
        "MINIMAX_API_KEY",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    yield


# ==============================================================================
# NORMALIZER IMPLEMENTATIONS (Isolated for testing without heavy imports)
# ==============================================================================


def _normalize_temperature(temperature: float) -> float:
    if temperature < 0 and not temperature == -1:
        return 0
    elif temperature > 2:
        return 2
    return temperature


def _normalize_max_length(max_length: int) -> int:
    if max_length < 1024 and not max_length == -1:
        return 1024
    elif max_length > 1048576:
        return 1048576
    return max_length


def _normalize_top_p(top_p: float) -> float:
    if top_p < 0 and not top_p == -1:
        return 0
    elif top_p > 1:
        return 1
    return top_p


def _normalize_top_k(
    top_k: int,
    *,
    retrieval_mode: str = "dense",
    rag_default_top_k: int = 50,
    rag_top_k_cap: int = 120,
    rag_search_limit_min: int = 50,
    rag_hybrid_enabled: bool = False,
) -> int:
    if top_k == -1:
        normalized = rag_default_top_k
    elif top_k < 1:
        normalized = 1
    elif top_k > rag_top_k_cap:
        normalized = rag_top_k_cap
    else:
        normalized = top_k

    if retrieval_mode == "dense" and rag_hybrid_enabled:
        retrieval_mode = "hybrid"
    if retrieval_mode in ["sparse_then_rerank", "dual_then_rerank"]:
        if normalized < rag_search_limit_min:
            normalized = rag_search_limit_min

    if normalized > rag_top_k_cap:
        normalized = rag_top_k_cap
    return normalized


def _normalize_score_threshold(score_threshold: float) -> float:
    if score_threshold == -1:
        return 0
    elif score_threshold < 0:
        return 0
    elif score_threshold > 20:
        return 20
    return score_threshold


# ==============================================================================
# CHATSERVICE NORMALIZER TESTS (Using isolated implementations)
# ==============================================================================


class TestChatServiceNormalizers:
    def test_normalize_temperature_sentinel_preserved(self):
        result = _normalize_temperature(-1)
        assert result == -1, "Sentinel value -1 should be preserved"

    def test_normalize_temperature_clamps_low(self):
        assert _normalize_temperature(-0.5) == 0
        assert _normalize_temperature(-2) == 0

    def test_normalize_temperature_clamps_high(self):
        assert _normalize_temperature(2.1) == 2
        assert _normalize_temperature(10.0) == 2

    def test_normalize_temperature_valid_range(self):
        assert _normalize_temperature(0.5) == 0.5
        assert _normalize_temperature(0) == 0
        assert _normalize_temperature(1) == 1
        assert _normalize_temperature(1.5) == 1.5
        assert _normalize_temperature(2.0) == 2.0

    def test_normalize_max_length_sentinel_preserved(self):
        result = _normalize_max_length(-1)
        assert result == -1, "Sentinel value -1 should be preserved"

    def test_normalize_max_length_clamps_low(self):
        assert _normalize_max_length(512) == 1024
        assert _normalize_max_length(0) == 1024

    def test_normalize_max_length_clamps_high(self):
        assert _normalize_max_length(2000000) == 1048576

    def test_normalize_top_p_sentinel_preserved(self):
        result = _normalize_top_p(-1)
        assert result == -1, "Sentinel value -1 should be preserved"

    def test_normalize_top_p_clamps_low(self):
        assert _normalize_top_p(-0.5) == 0

    def test_normalize_top_p_clamps_high(self):
        assert _normalize_top_p(1.5) == 1

    def test_normalize_top_k_sentinel_converts_to_default(self):
        result = _normalize_top_k(-1)
        assert result == 50, "Sentinel -1 should convert to thesis default 50"

    def test_normalize_top_k_clamps_low(self):
        assert _normalize_top_k(0) == 1
        assert _normalize_top_k(-2) == 1

    def test_normalize_top_k_clamps_high(self):
        assert _normalize_top_k(121) == 120
        assert _normalize_top_k(500) == 120

    def test_normalize_top_k_minimum_for_dual_then_rerank(self):
        assert _normalize_top_k(2, retrieval_mode="dual_then_rerank") == 50

    def test_normalize_score_threshold_sentinel_converts_to_default(self):
        result = _normalize_score_threshold(-1)
        assert result == 0, "Sentinel -1 should convert to default 0"

    def test_normalize_score_threshold_clamps_low(self):
        assert _normalize_score_threshold(-2) == 0

    def test_normalize_score_threshold_clamps_high(self):
        assert _normalize_score_threshold(25) == 20


class TestChatServiceOptionalArgs:
    def test_optional_args_basic(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        optional = ChatService._build_optional_openai_args(
            model_name="deepseek-chat",
            temperature=0.2,
            max_length=2048,
            top_p=0.9,
        )
        assert optional.get("temperature") == 0.2
        assert optional.get("top_p") == 0.9
        assert optional.get("max_tokens") == 2048

    def test_optional_args_sentinel_omitted(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        optional = ChatService._build_optional_openai_args(
            model_name="some-model",
            temperature=-1,
            max_length=-1,
            top_p=-1,
        )
        assert "temperature" not in optional
        assert "max_tokens" not in optional
        assert "top_p" not in optional


# ==============================================================================
# PYDANTIC VALIDATION TESTS (ModelConfigBase)
# ==============================================================================


class TestModelConfigBaseValidation:
    def test_model_name_min_length(self):
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="at least 2 characters"):
            ModelConfigBase(model_name="x", api_key="valid-api-key-12345678")

    def test_model_name_accepts_any_name(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="completely-unknown-model",
            api_key="valid-api-key-12345678901234567890",
        )
        assert config.model_name == "completely-unknown-model"

    def test_model_name_valid(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
        )
        assert config.model_name == "glm-4.7"

    def test_api_key_min_length(self):
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="at least 10 characters"):
            ModelConfigBase(model_name="glm-4.7", api_key="short")

    def test_api_key_short_key_without_prefix_rejected(self):
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="too short"):
            ModelConfigBase(
                model_name="glm-4.7",
                api_key="1234567890123",
            )

    def test_api_key_with_sk_prefix_accepted(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(model_name="glm-4.7", api_key="sk-abcdefghij")
        assert config.api_key == "sk-abcdefghij"

    def test_api_key_with_dot_accepted(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(model_name="glm-4.7", api_key="jwt.token.here")
        assert config.api_key == "jwt.token.here"

    def test_temperature_clamps_negative(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            temperature=-0.5,
        )
        assert config.temperature == 0.0

    def test_temperature_clamps_high(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            temperature=3.0,
        )
        assert config.temperature == 2.0

    def test_max_length_clamps_low(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            max_length=100,
        )
        assert config.max_length == 1024

    def test_max_length_clamps_high(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            max_length=2000000,
        )
        assert config.max_length == 1048576

    def test_top_p_clamps_negative(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            top_P=-0.5,
        )
        assert config.top_P == 0.0

    def test_top_p_clamps_high(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            top_P=1.5,
        )
        assert config.top_P == 1.0

    def test_top_k_clamps_low(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            top_K=0,
        )
        assert config.top_K == 1

    def test_top_k_clamps_high(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            top_K=1000,
        )
        assert config.top_K == 120

    def test_score_threshold_clamps_negative(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            score_threshold=-5,
        )
        assert config.score_threshold == 0

    def test_score_threshold_clamps_high(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            score_threshold=150,
        )
        assert config.score_threshold == 20

    def test_no_provider_field(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
        )
        assert not hasattr(config, "provider") or "provider" not in config.model_fields


# ==============================================================================
# CACHE INVALIDATION TESTS
# ==============================================================================


@pytest.fixture
def mock_redis():
    mock_redis_module = MagicMock()
    mock_redis_module.asyncio = MagicMock()
    sys.modules["redis"] = mock_redis_module
    sys.modules["redis.asyncio"] = mock_redis_module.asyncio
    yield mock_redis_module
    if "app.db.redis" in sys.modules:
        del sys.modules["app.db.redis"]
    if "app.db.cache" in sys.modules:
        del sys.modules["app.db.cache"]


class TestCacheInvalidation:
    def test_cache_service_has_invalidate_method(self, mock_redis):
        from app.db.cache import cache_service

        assert hasattr(cache_service, "invalidate_model_config")
        assert callable(cache_service.invalidate_model_config)

    def test_cache_key_format(self, mock_redis):
        from app.db.cache import CacheService

        key = CacheService._make_key("model_config", "testuser")
        assert key == "model_config:testuser"

    def test_cache_pattern_format(self, mock_redis):
        from app.db.cache import CacheService

        pattern = CacheService._make_pattern("model_config", "testuser")
        assert pattern == "model_config:testuser"

        wildcard_pattern = CacheService._make_pattern("model_config")
        assert wildcard_pattern == "model_config:*"

    def test_cache_invalidation_import_structure(self, mock_redis):
        from app.db.cache import cache_service
        import inspect

        sig = inspect.signature(cache_service.invalidate_model_config)
        params = list(sig.parameters.keys())
        assert "username" in params or "self" in params, (
            "invalidate_model_config should accept username parameter"
        )

    def test_repository_source_contains_cache_invalidation_call(self):
        import os

        repo_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "app",
            "db",
            "repositories",
            "model_config.py",
        )
        with open(repo_path) as f:
            source = f.read()

        assert "cache_service" in source, (
            "ModelConfigRepository should import cache_service"
        )

        assert "invalidate_model_config" in source, (
            "ModelConfigRepository should call invalidate_model_config"
        )

        invalidation_count = source.count("await cache_service.invalidate_model_config")
        assert invalidation_count >= 4, (
            f"Expected at least 4 cache invalidation calls, found {invalidation_count}"
        )


# ==============================================================================
# BOUNDARY VALUE TESTS
# ==============================================================================


class TestBoundaryValues:
    def test_temperature_exact_boundaries(self):
        from app.models.model_config import ModelConfigBase

        config_low = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            temperature=0.0,
        )
        assert config_low.temperature == 0.0

        config_high = ModelConfigBase(
            model_name="glm-4.7",
            api_key="valid-api-key-12345678901234567890",
            temperature=2.0,
        )
        assert config_high.temperature == 2.0

    def test_normalizer_boundary_alignment_temperature(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            temperature=1.5,
        )
        assert config.temperature == 1.5

        normalized = _normalize_temperature(1.5)
        assert normalized == 1.5

    def test_normalizer_boundary_alignment_max_length(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            max_length=100,
        )
        normalized = _normalize_max_length(100)
        assert config.max_length == normalized == 1024

    def test_normalizer_boundary_alignment_top_k(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            top_K=500,
        )
        normalized = _normalize_top_k(500)
        assert config.top_K == normalized == 120

    def test_normalizer_boundary_alignment_score_threshold(self):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            score_threshold=150,
        )
        normalized = _normalize_score_threshold(150)
        assert config.score_threshold == normalized == 20

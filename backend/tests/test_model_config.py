"""
Baseline tests for model configuration system.

This test module captures the current behavior of:
1. Provider detection logic (ProviderClient.get_provider_for_model)
2. ChatService normalizers for model parameters (tested via isolated implementations)
3. Pydantic validation in ModelConfigBase
4. Cache invalidation on model_config writes

These tests serve as a safety net before refactoring the model config system.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock
import os
import sys
from typing import Any, cast, Dict, List

pytestmark = pytest.mark.unit


# ==============================================================================
# FIXTURES
# ==============================================================================


def _require_chat_service_deps() -> None:
    """Skip ChatService-dependent tests when optional deps are missing."""
    pytest.importorskip("circuitbreaker")
    pytest.importorskip("openai")


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all provider-related environment variables for clean testing."""
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


@pytest.fixture
def zai_env(monkeypatch, clean_env):
    """Set up environment with only ZAI_API_KEY."""
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-api-key-12345")
    yield


@pytest.fixture
def cliproxyapi_env(monkeypatch, clean_env):
    """Set up environment for CLIProxyAPI."""
    monkeypatch.setenv("CLIPROXYAPI_BASE_URL", "https://proxy.example.com/v1")
    monkeypatch.setenv("CLIPROXYAPI_API_KEY", "test-cliproxy-key-12345")
    yield


# ==============================================================================
# NORMALIZER IMPLEMENTATIONS (Isolated for testing without heavy imports)
#
# These are exact copies of the ChatService normalizer logic to test behavior
# without importing the full ChatService class with all its dependencies.
# ==============================================================================


def _normalize_temperature(temperature: float) -> float:
    """Normalize temperature parameter.

    Note: -1 is a sentinel value meaning "use provider default".
    When -1 is passed, it's preserved and typically handled by the
    LLM client to omit the parameter from the API request.
    """
    if temperature < 0 and not temperature == -1:
        return 0
    elif temperature > 2:
        return 2
    return temperature


def _normalize_max_length(max_length: int) -> int:
    """Normalize max_length parameter."""
    if max_length < 1024 and not max_length == -1:
        return 1024
    elif max_length > 1048576:
        return 1048576
    return max_length


def _normalize_top_p(top_p: float) -> float:
    """Normalize top_p parameter."""
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
    """Normalize top_k parameter (mirrors ChatService behavior).

    Note: In thesis sparse/dual modes, we enforce a minimum to avoid accidental
    "2 sources only" behavior from legacy UI defaults.
    """
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
    """Normalize score_threshold parameter."""
    if score_threshold == -1:
        # Thesis default: treat -1 as "no filter".
        return 0
    elif score_threshold < 0:
        return 0
    elif score_threshold > 20:
        return 20
    return score_threshold


# ==============================================================================
# PROVIDER DETECTION TESTS
# ==============================================================================


class TestProviderDetection:
    """Tests for ProviderClient.get_provider_for_model()."""

    def test_deepseek_chat_detection(self, clean_env):
        """Verify deepseek-chat model is detected as deepseek provider."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("deepseek-chat")
        assert result == "deepseek"

    def test_deepseek_reasoner_detection(self, clean_env):
        """Verify deepseek-reasoner model is detected as deepseek provider."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("deepseek-reasoner")
        assert result == "deepseek"

    def test_glm_detection_with_zai_key(self, zai_env):
        """Verify GLM models use zai provider when ZAI_API_KEY is set."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("glm-4.7-flash")
        assert result == "zai"

    def test_glm_detection_defaults_to_zai_without_keys(self, clean_env):
        """Verify GLM models default to zai when no API keys are set."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("glm-4.7-flash")
        assert result == "zai", "GLM should default to zai without any API keys"

    def test_cliproxyapi_detection_with_base_url(self, cliproxyapi_env):
        """Verify CLIProxyAPI models are detected when CLIPROXYAPI_BASE_URL is set."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("claude-sonnet-4-5")
        assert result == "cliproxyapi"

    def test_cliproxyapi_fallback_matching_without_base_url(self, clean_env):
        """Document current behavior: CLIProxyAPI models still match via generic loop.

        CURRENT BEHAVIOR (documenting for refactoring awareness):
        Without CLIPROXYAPI_BASE_URL, models like claude-sonnet-4-5 still match
        'cliproxyapi' because the generic provider loop matches against the
        cliproxyapi models list. This may be unintended - the model matches a
        provider that cannot actually be used without the base URL.

        This test documents this quirk so we can decide during refactoring whether
        to change this behavior (e.g., skip cliproxyapi in generic matching if
        CLIPROXYAPI_BASE_URL is not set).
        """
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("claude-sonnet-4-5")
        # Current behavior: matches cliproxyapi even without BASE_URL
        assert result == "cliproxyapi", (
            "Current behavior: CLIProxyAPI models match via generic loop even without BASE_URL"
        )

    def test_gpt_oss_prefers_ollama_cloud_over_cliproxy(self, clean_env, monkeypatch):
        """Verify gpt-oss legacy model routes to Ollama Cloud when key is set."""
        from app.rag.provider_client import ProviderClient

        monkeypatch.setenv("CLIPROXYAPI_BASE_URL", "https://proxy.example.com/v1")
        monkeypatch.setenv("CLIPROXYAPI_API_KEY", "test-cliproxy-key-12345")
        monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "test-ollama-key-12345")
        result = ProviderClient.get_provider_for_model("gpt-oss-120b-medium")
        assert result == "ollama-cloud"

    def test_minimax_abab_detection_requires_key(self, clean_env):
        """MiniMax heuristic detection should be gated on MINIMAX_API_KEY presence."""
        from app.rag.provider_client import ProviderClient

        # clean_env ensures MINIMAX_API_KEY isn't present.
        assert ProviderClient.get_provider_for_model("abab6.5s-chat") is None

        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-minimax-key-12345"}):
            assert ProviderClient.get_provider_for_model("abab6.5s-chat") == "minimax"

    def test_ollama_cloud_detection(self, clean_env):
        """Verify ollama-cloud models are detected correctly."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("llama3.3")
        assert result == "ollama-cloud"

    def test_minimax_detection(self, clean_env):
        """Verify MiniMax models are detected correctly."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("MiniMax-M2.1")
        assert result == "minimax"

    def test_unknown_model_returns_none(self, clean_env):
        """Verify unknown models return None."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("unknown-model-xyz")
        assert result is None

    def test_case_insensitive_matching(self, clean_env):
        """Verify model name matching is case-insensitive."""
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model("DEEPSEEK-CHAT")
        assert result == "deepseek"


class TestModelNameMapping:
    """Tests for legacy model name mapping to API ids."""

    def test_gpt_oss_model_name_mapping(self):
        from app.rag.provider_client import resolve_api_model_name

        assert resolve_api_model_name("gpt-oss-120b-medium") == "gpt-oss:120b"
        assert resolve_api_model_name("gpt-oss:120b") == "gpt-oss:120b"


# ==============================================================================
# CHATSERVICE NORMALIZER TESTS (Using isolated implementations)
# ==============================================================================


class TestChatServiceNormalizers:
    """Tests for ChatService parameter normalizers with sentinel value handling.

    These tests use isolated implementations that match the ChatService logic
    to avoid importing the full ChatService class with all its dependencies.
    """

    def test_normalize_temperature_sentinel_preserved(self):
        """Verify -1 sentinel value is preserved for temperature."""
        result = _normalize_temperature(-1)
        assert result == -1, "Sentinel value -1 should be preserved"

    def test_normalize_temperature_clamps_low(self):
        """Verify negative temperature (except -1) is clamped to 0."""
        assert _normalize_temperature(-0.5) == 0
        assert _normalize_temperature(-2) == 0

    def test_normalize_temperature_clamps_high(self):
        """Verify temperature above 2 is clamped to 2 (sentinel -1 preserved)."""
        assert _normalize_temperature(2.1) == 2
        assert _normalize_temperature(10.0) == 2

    def test_normalize_temperature_valid_range(self):
        """Verify valid temperature values are preserved."""
        assert _normalize_temperature(0.5) == 0.5
        assert _normalize_temperature(0) == 0
        assert _normalize_temperature(1) == 1
        assert _normalize_temperature(1.5) == 1.5
        assert _normalize_temperature(2.0) == 2.0

    def test_normalize_max_length_sentinel_preserved(self):
        """Verify -1 sentinel value is preserved for max_length."""
        result = _normalize_max_length(-1)
        assert result == -1, "Sentinel value -1 should be preserved"

    def test_normalize_max_length_clamps_low(self):
        """Verify max_length below 1024 (except -1) is clamped to 1024."""
        assert _normalize_max_length(512) == 1024
        assert _normalize_max_length(0) == 1024

    def test_normalize_max_length_clamps_high(self):
        """Verify max_length above 1048576 is clamped to 1048576."""
        assert _normalize_max_length(2000000) == 1048576

    def test_normalize_top_p_sentinel_preserved(self):
        """Verify -1 sentinel value is preserved for top_p."""
        result = _normalize_top_p(-1)
        assert result == -1, "Sentinel value -1 should be preserved"

    def test_normalize_top_p_clamps_low(self):
        """Verify negative top_p (except -1) is clamped to 0."""
        assert _normalize_top_p(-0.5) == 0

    def test_normalize_top_p_clamps_high(self):
        """Verify top_p above 1 is clamped to 1."""
        assert _normalize_top_p(1.5) == 1

    def test_normalize_top_k_sentinel_converts_to_default(self):
        """Verify -1 sentinel value for top_k converts to thesis default (50)."""
        result = _normalize_top_k(-1)
        assert result == 50, "Sentinel -1 should convert to thesis default 50"

    def test_normalize_top_k_clamps_low(self):
        """Verify top_k below 1 (except -1) is clamped to 1."""
        assert _normalize_top_k(0) == 1
        assert _normalize_top_k(-2) == 1

    def test_normalize_top_k_clamps_high(self):
        """Verify top_k above 120 is clamped to 120."""
        assert _normalize_top_k(121) == 120
        assert _normalize_top_k(500) == 120

    def test_normalize_top_k_minimum_for_dual_then_rerank(self):
        """Verify sparse/dual modes enforce a minimum recall breadth."""
        assert _normalize_top_k(2, retrieval_mode="dual_then_rerank") == 50


class TestChatServiceProviderAwareReasoner:
    """Unit tests for provider-aware DeepSeek reasoner handling."""

    def test_resolve_effective_provider_skips_detection_for_custom_model_url(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        # If a user provides an explicit OpenAI-compatible model_url, we should not
        # apply provider-specific special-cases based on model name heuristics.
        effective = ChatService._resolve_effective_provider(
            provider=None,
            model_url="http://example.com/v1",
            model_name="deepseek-reasoner",
        )
        assert effective is None

    def test_resolve_effective_provider_uses_explicit_provider(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        effective = ChatService._resolve_effective_provider(
            provider="deepseek",
            model_url="http://example.com/v1",
            model_name="deepseek-reasoner",
        )
        assert effective == "deepseek"

    def test_deepseek_reasoner_only_for_official_provider(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        assert (
            ChatService._is_deepseek_reasoner_model("deepseek-reasoner", "deepseek")
            is True
        )
        # Critical: deepseek-r1 served via ollama-cloud must NOT be treated as deepseek-reasoner.
        assert (
            ChatService._is_deepseek_reasoner_model("deepseek-r1", "ollama-cloud")
            is False
        )

    def test_optional_args_for_ollama_deepseek_r1_keeps_standard_params(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        optional = ChatService._build_optional_openai_args(
            model_name="deepseek-r1",
            provider="ollama-cloud",
            temperature=0.2,
            max_length=2048,
            top_p=0.9,
        )
        assert optional.get("temperature") == 0.2
        assert optional.get("top_p") == 0.9
        assert optional.get("max_tokens") == 2048
        assert "max_completion_tokens" not in optional

    def test_optional_args_for_deepseek_reasoner_uses_max_completion_tokens(self, clean_env):
        _require_chat_service_deps()
        from app.core.llm.chat_service import ChatService

        optional = ChatService._build_optional_openai_args(
            model_name="deepseek-reasoner",
            provider="deepseek",
            temperature=0.2,
            max_length=2048,
            top_p=0.9,
        )
        assert "temperature" not in optional
        assert "top_p" not in optional
        assert "max_tokens" not in optional
        assert optional.get("max_completion_tokens") == 2048

    def test_normalize_score_threshold_sentinel_converts_to_default(self):
        """Verify -1 sentinel value for score_threshold converts to default (no filter)."""
        result = _normalize_score_threshold(-1)
        assert result == 0, "Sentinel -1 should convert to default 0"

    def test_normalize_score_threshold_clamps_low(self):
        """Verify score_threshold below 0 (except -1) is clamped to 0."""
        assert _normalize_score_threshold(-2) == 0

    def test_normalize_score_threshold_clamps_high(self):
        """Verify score_threshold above 20 is clamped to 20."""
        assert _normalize_score_threshold(25) == 20


# ==============================================================================
# PYDANTIC VALIDATION TESTS (ModelConfigBase)
# ==============================================================================


class TestModelConfigBaseValidation:
    """Tests for Pydantic field validators in ModelConfigBase."""

    def test_model_name_min_length(self, zai_env):
        """Verify model_name requires at least 2 characters."""
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="at least 2 characters"):
            ModelConfigBase(model_name="x", api_key="valid-api-key-12345678")

    def test_model_name_unknown_provider_rejected(self, clean_env):
        """Verify unknown model names are rejected."""
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="Unknown model"):
            ModelConfigBase(
                model_name="completely-unknown-model", api_key="valid-api-key-12345678"
            )

    def test_model_name_unknown_allowed_with_explicit_provider(self, clean_env):
        """If provider is explicit, allow unknown model ids (forward-compatible).

        This matters for OpenAI-compatible providers where model ids may change faster
        than our static providers.yaml list.
        """
        from app.models.model_config import ModelConfigBase

        cfg = ModelConfigBase(
            model_name="abab6.5s-chat",
            provider="minimax",
            api_key="sk-abcdefghij",
        )
        assert cfg.model_name == "abab6.5s-chat"
        assert cfg.provider == "minimax"

    def test_model_name_valid_known_model(self, zai_env):
        """Verify valid model names are accepted."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash", api_key="valid-api-key-12345678"
        )
        assert config.model_name == "glm-4.7-flash"

    def test_api_key_min_length(self, zai_env):
        """Verify api_key requires at least 10 characters."""
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="at least 10 characters"):
            ModelConfigBase(model_name="glm-4.7-flash", api_key="short")

    def test_api_key_short_key_without_prefix_rejected(self, zai_env):
        """Verify short API keys without known prefix are rejected."""
        from app.models.model_config import ModelConfigBase

        with pytest.raises(ValueError, match="too short"):
            ModelConfigBase(
                model_name="glm-4.7-flash",
                api_key="1234567890123",  # 13 chars but no sk-/hf_ prefix and no dot
            )

    def test_api_key_with_sk_prefix_accepted(self, zai_env):
        """Verify API keys starting with sk- are accepted."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(model_name="glm-4.7-flash", api_key="sk-abcdefghij")
        assert config.api_key == "sk-abcdefghij"

    def test_api_key_with_dot_accepted(self, zai_env):
        """Verify API keys containing a dot are accepted."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(model_name="glm-4.7-flash", api_key="jwt.token.here")
        assert config.api_key == "jwt.token.here"

    def test_temperature_clamps_negative(self, zai_env):
        """Verify temperature is clamped to 0 when negative."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            temperature=-0.5,
        )
        assert config.temperature == 0.0

    def test_temperature_clamps_high(self, zai_env):
        """Verify temperature is clamped to 2 when too high."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            temperature=3.0,
        )
        assert config.temperature == 2.0

    def test_max_length_clamps_low(self, zai_env):
        """Verify max_length is clamped to 1024 when too low (aligned with ChatService)."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            max_length=100,
        )
        assert config.max_length == 1024

    def test_max_length_clamps_high(self, zai_env):
        """Verify max_length is clamped to 1048576 when too high."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            max_length=2000000,
        )
        assert config.max_length == 1048576

    def test_top_p_clamps_negative(self, zai_env):
        """Verify top_P is clamped to 0 when negative."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            top_P=-0.5,
        )
        assert config.top_P == 0.0

    def test_top_p_clamps_high(self, zai_env):
        """Verify top_P is clamped to 1 when above 1."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            top_P=1.5,
        )
        assert config.top_P == 1.0

    def test_top_k_clamps_low(self, zai_env):
        """Verify top_K is clamped to 1 when below 1."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            top_K=0,
        )
        assert config.top_K == 1

    def test_top_k_clamps_high(self, zai_env):
        """Verify top_K is clamped to 120 when above 120 (aligned with thesis settings)."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            top_K=1000,
        )
        assert config.top_K == 120

    def test_score_threshold_clamps_negative(self, zai_env):
        """Verify score_threshold is clamped to 0 when negative."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            score_threshold=-5,
        )
        assert config.score_threshold == 0

    def test_score_threshold_clamps_high(self, zai_env):
        """Verify score_threshold is clamped to 20 when above 20 (aligned with ChatService)."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            score_threshold=150,
        )
        assert config.score_threshold == 20


# ==============================================================================
# CACHE INVALIDATION TESTS
#
# These tests verify the cache invalidation logic without requiring Redis.
# We mock the redis module to avoid import errors.
# ==============================================================================


@pytest.fixture
def mock_redis():
    """Mock redis module before importing cache module."""
    mock_redis_module = MagicMock()
    mock_redis_module.asyncio = MagicMock()
    sys.modules["redis"] = mock_redis_module
    sys.modules["redis.asyncio"] = mock_redis_module.asyncio
    yield mock_redis_module
    # Cleanup
    if "app.db.redis" in sys.modules:
        del sys.modules["app.db.redis"]
    if "app.db.cache" in sys.modules:
        del sys.modules["app.db.cache"]


class TestCacheInvalidation:
    """Tests verifying cache invalidation is called on model_config writes.

    These tests mock redis dependencies to test cache logic in isolation.
    """

    def test_cache_service_has_invalidate_method(self, mock_redis):
        """Verify cache_service has invalidate_model_config method."""
        # Import after mocking redis
        from app.db.cache import cache_service

        assert hasattr(cache_service, "invalidate_model_config")
        assert callable(cache_service.invalidate_model_config)

    def test_cache_key_format(self, mock_redis):
        """Verify cache keys are generated in expected format."""
        from app.db.cache import CacheService

        key = CacheService._make_key("model_config", "testuser")
        assert key == "model_config:testuser"

    def test_cache_pattern_format(self, mock_redis):
        """Verify cache patterns are generated correctly for invalidation."""
        from app.db.cache import CacheService

        pattern = CacheService._make_pattern("model_config", "testuser")
        assert pattern == "model_config:testuser"

        # Wildcard pattern
        wildcard_pattern = CacheService._make_pattern("model_config")
        assert wildcard_pattern == "model_config:*"

    def test_cache_invalidation_import_structure(self, mock_redis):
        """Verify cache invalidation is wired into model_config repository.

        This test verifies the import structure and method signature without
        actually instantiating the repository (which triggers Milvus connection).
        Full integration testing requires Docker services.
        """
        from app.db.cache import cache_service

        # Verify cache_service has the expected method signature
        import inspect

        sig = inspect.signature(cache_service.invalidate_model_config)
        params = list(sig.parameters.keys())
        assert "username" in params or "self" in params, (
            "invalidate_model_config should accept username parameter"
        )

    def test_repository_source_contains_cache_invalidation_call(self):
        """Verify ModelConfigRepository source code calls cache invalidation.

        This is a source-level check that confirms the cache invalidation pattern
        is properly wired without requiring runtime dependencies.
        """
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

        # Verify cache invalidation is imported
        assert "cache_service" in source, (
            "ModelConfigRepository should import cache_service"
        )

        # Verify invalidate_model_config is called
        assert "invalidate_model_config" in source, (
            "ModelConfigRepository should call invalidate_model_config"
        )

        # Count number of cache invalidation calls (should be at least 5)
        invalidation_count = source.count("await cache_service.invalidate_model_config")
        assert invalidation_count >= 5, (
            f"Expected at least 5 cache invalidation calls, found {invalidation_count}"
        )


# ==============================================================================
# BOUNDARY VALUE TESTS
# ==============================================================================


class TestBoundaryValues:
    """Tests for edge cases and boundary values in validation."""

    def test_temperature_exact_boundaries(self, zai_env):
        """Verify exact boundary values for temperature."""
        from app.models.model_config import ModelConfigBase

        # Exact lower bound
        config_low = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            temperature=0.0,
        )
        assert config_low.temperature == 0.0

        # Exact upper bound
        config_high = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            temperature=2.0,
        )
        assert config_high.temperature == 2.0

    def test_normalizer_boundary_alignment_temperature(self):
        """Verify ModelConfigBase and ChatService temperature bounds are aligned (0-2)."""
        from app.models.model_config import ModelConfigBase

        # ModelConfigBase allows 1.5
        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            temperature=1.5,
        )
        assert config.temperature == 1.5

        # ChatService should preserve 1.5 (clamp only above 2.0; -1 sentinel preserved)
        normalized = _normalize_temperature(1.5)
        assert normalized == 1.5

    def test_normalizer_boundary_alignment_max_length(self):
        """Verify ModelConfigBase and ChatService max_length bounds are aligned."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            max_length=100,
        )
        normalized = _normalize_max_length(100)
        assert config.max_length == normalized == 1024

    def test_normalizer_boundary_alignment_top_k(self):
        """Verify ModelConfigBase and ChatService top_k bounds are aligned."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            top_K=500,
        )
        normalized = _normalize_top_k(500)
        assert config.top_K == normalized == 120

    def test_normalizer_boundary_alignment_score_threshold(self):
        """Verify ModelConfigBase and ChatService score_threshold bounds are aligned."""
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="deepseek-chat",
            api_key="valid-api-key-12345678901234567890",
            score_threshold=150,
        )
        normalized = _normalize_score_threshold(150)
        assert config.score_threshold == normalized == 20


# ==============================================================================
# EXPLICIT PROVIDER FIELD TESTS
# ==============================================================================


class TestExplicitProviderField:
    """Tests for the explicit provider field in ModelConfigBase."""

    def test_provider_field_none_by_default(self, zai_env):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
        )
        assert config.provider is None

    def test_provider_field_accepts_valid_provider(self, zai_env):
        from app.models.model_config import ModelConfigBase

        config = ModelConfigBase(
            model_name="glm-4.7-flash",
            api_key="valid-api-key-12345678901234567890",
            provider="zai",
        )
        assert config.provider == "zai"

    def test_provider_field_rejects_unknown_provider(self, zai_env):
        from app.models.model_config import ModelConfigBase
        import pytest

        with pytest.raises(ValueError, match="Unknown provider"):
            ModelConfigBase(
                model_name="glm-4.7-flash",
                api_key="valid-api-key-12345678901234567890",
                provider="nonexistent-provider",
            )

    def test_explicit_provider_overrides_auto_detection(self, clean_env):
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model(
            "glm-4.7-flash", explicit_provider="zai"
        )
        assert result == "zai"

    def test_none_provider_uses_auto_detection(self, zai_env):
        from app.rag.provider_client import ProviderClient

        result = ProviderClient.get_provider_for_model(
            "glm-4.7-flash", explicit_provider=None
        )
        assert result == "zai"


class TestModelConfigRepositorySanitization:
    """Tests for system model sanitization in ModelConfigRepository."""

    @pytest.mark.asyncio
    async def test_system_model_sanitization(self, clean_env, monkeypatch):
        """Verify system_* models are sanitized when retrieved from DB."""
        from app.db.repositories.model_config import ModelConfigRepository

        # Mock DB and dependencies
        mock_db = MagicMock()
        repo = ModelConfigRepository(mock_db)

        test_username = "testuser"
        test_system_model = {
            "model_id": "system_deepseek-chat",
            "model_name": "deepseek-chat",
            "model_url": "http://cliproxyapi:8317/v1",
            "api_key": "stale-key",
            "provider": None,
            "base_used": [],
            "system_prompt": "",
            "temperature": -1,
            "max_length": -1,
            "top_P": -1,
            "top_K": -1,
            "score_threshold": -1,
        }

        mock_user_config = {
            "username": test_username,
            "selected_model": "system_deepseek-chat",
            "models": [test_system_model],
        }

        # Mock find_one to return our test config
        mock_db.model_config.find_one = AsyncMock(return_value=mock_user_config)

        # 1. Test get_all_models_config
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        result = cast(Dict[str, Any], await repo.get_all_models_config(test_username))

        assert result["status"] == "success"
        # Find the sanitized model in the list
        models = cast(List[Dict[str, Any]], result["models"])
        sanitized = next(m for m in models if m["model_id"] == "system_deepseek-chat")
        assert sanitized["model_url"] == ""
        assert sanitized["api_key"] is None
        assert sanitized["provider"] == "deepseek"
        # System models should have academic/RAG-friendly explicit defaults (not all -1 sentinels).
        assert sanitized["temperature"] == 0.2
        assert sanitized["max_length"] == 4096

        # 2. Test get_selected_model_config
        result_selected = cast(
            Dict[str, Any], await repo.get_selected_model_config(test_username)
        )
        assert result_selected["status"] == "success"
        sanitized_selected = cast(
            Dict[str, Any], result_selected["select_model_config"]
        )
        assert sanitized_selected["model_id"] == "system_deepseek-chat"
        assert sanitized_selected["model_url"] == ""
        assert sanitized_selected["api_key"] is None
        assert sanitized_selected["provider"] == "deepseek"
        assert sanitized_selected["temperature"] == 0.2
        assert sanitized_selected["max_length"] == 4096

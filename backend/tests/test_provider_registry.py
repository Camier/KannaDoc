"""
Tests for ProviderRegistry - unified provider configuration with timeout support.
"""

import asyncio
import importlib.util
from pathlib import Path
import pytest
import sys
from types import ModuleType
from unittest.mock import AsyncMock, Mock, patch

if "redis" not in sys.modules:
    sys.modules.setdefault("redis", Mock())
    sys.modules.setdefault("redis.asyncio", Mock())

if "botocore" not in sys.modules:
    mock_botocore_exceptions = Mock()
    mock_botocore_exceptions.ClientError = Exception
    sys.modules.setdefault("botocore", Mock())
    sys.modules.setdefault("botocore.exceptions", mock_botocore_exceptions)
    sys.modules.setdefault("aioboto3", Mock())

if "fastapi" not in sys.modules:
    fastapi_module = ModuleType("fastapi")

    class DummyRouter:
        def get(self, *args, **kwargs):
            return lambda func: func

        def post(self, *args, **kwargs):
            return lambda func: func

        def delete(self, *args, **kwargs):
            return lambda func: func

        def patch(self, *args, **kwargs):
            return lambda func: func

        def put(self, *args, **kwargs):
            return lambda func: func

    setattr(fastapi_module, "APIRouter", DummyRouter)
    setattr(fastapi_module, "Depends", Mock())
    setattr(fastapi_module, "HTTPException", Exception)
    setattr(fastapi_module, "Query", lambda *args, **kwargs: None)
    setattr(fastapi_module, "UploadFile", Mock())
    sys.modules.setdefault("fastapi", fastapi_module)

from app.rag.provider_registry import (
    ProviderRegistry,
    ProviderConfig,
    get_provider_timeout,
    get_timeout_for_model,
)
from app.core.logging import logger


class TestProviderRegistry:
    """Test ProviderRegistry class methods."""

    def setup_method(self):
        """Ensure registry is loaded before each test."""
        ProviderRegistry.load()

    def test_load_providers(self):
        """Test that providers are loaded correctly."""
        providers = ProviderRegistry.get_all_providers()
        assert isinstance(providers, list)
        assert len(providers) >= 5  # deepseek, zai, cliproxyapi, ollama-cloud, minimax
        assert "deepseek" in providers
        assert "zai" in providers
        assert "cliproxyapi" in providers

    def test_get_provider_config(self):
        """Test getting complete provider configuration."""
        config = ProviderRegistry.get_provider_config("deepseek")
        assert isinstance(config, ProviderConfig)
        assert config.provider_id == "deepseek"
        assert config.base_url == "https://api.deepseek.com/v1"
        assert config.env_key == "DEEPSEEK_API_KEY"
        assert config.timeout == 180
        assert config.vision is False
        assert "deepseek-chat" in config.models

    def test_get_provider_config_unknown(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderRegistry.get_provider_config("unknown_provider")

    def test_get_timeout(self):
        """Test getting timeout for specific providers."""
        assert ProviderRegistry.get_timeout("deepseek") == 180
        assert ProviderRegistry.get_timeout("zai") == 180
        assert ProviderRegistry.get_timeout("cliproxyapi") == 120
        assert ProviderRegistry.get_timeout("ollama-cloud") == 120
        assert ProviderRegistry.get_timeout("minimax") == 120

    def test_get_timeout_for_model_glm(self):
        """Test timeout detection for GLM models."""
        # GLM models should get 180s timeout (zai)
        assert ProviderRegistry.get_timeout_for_model("glm-4.7") == 180
        assert ProviderRegistry.get_timeout_for_model("glm-4.6") == 180
        assert ProviderRegistry.get_timeout_for_model("glm-4.5-air") == 180

    def test_get_timeout_for_model_deepseek(self):
        """Test timeout detection for DeepSeek models."""
        assert ProviderRegistry.get_timeout_for_model("deepseek-chat") == 180
        assert ProviderRegistry.get_timeout_for_model("deepseek-reasoner") == 180

    def test_get_timeout_for_model_claude(self):
        """Test timeout detection for Claude models (cliproxyapi)."""
        assert ProviderRegistry.get_timeout_for_model("claude-opus-4-6-thinking") == 120
        assert ProviderRegistry.get_timeout_for_model("claude-sonnet-4-5") == 120

    def test_get_timeout_for_model_gpt(self, monkeypatch):
        """Test timeout detection for GPT models (cliproxyapi, env-gated)."""
        monkeypatch.setenv("CLIPROXYAPI_BASE_URL", "http://test")
        assert ProviderRegistry.get_timeout_for_model("gpt-4o") == 120
        assert ProviderRegistry.get_timeout_for_model("gpt-4o-mini") == 120
        assert ProviderRegistry.get_timeout_for_model("codex-5.3") == 120

    def test_get_timeout_for_model_unknown(self):
        """Test that unknown model raises ValueError."""
        with pytest.raises(ValueError, match="Cannot detect provider"):
            ProviderRegistry.get_timeout_for_model("unknown_model_xyz")

    def test_get_models_for_provider(self):
        """Test getting models list for a provider."""
        deepseek_models = ProviderRegistry.get_models_for_provider("deepseek")
        assert isinstance(deepseek_models, list)
        assert "deepseek-chat" in deepseek_models
        assert "deepseek-reasoner" in deepseek_models

    def test_is_vision_model(self):
        """Test vision model detection."""
        # Vision models (from vision_patterns in providers.yaml)
        assert ProviderRegistry.is_vision_model("gpt-4o") is True
        assert ProviderRegistry.is_vision_model("claude-3.5-sonnet") is True
        assert ProviderRegistry.is_vision_model("claude-opus-4-6-thinking") is True
        assert ProviderRegistry.is_vision_model("qwen3-vl:235b") is True
        assert ProviderRegistry.is_vision_model("gemini-2.5-pro") is True
        assert ProviderRegistry.is_vision_model("llama3.2-vision") is True

        # Non-vision models (not in vision_patterns)
        assert ProviderRegistry.is_vision_model("deepseek-chat") is False
        assert ProviderRegistry.is_vision_model("MiniMax-M2.1") is False

    def test_detect_provider_minimax(self, monkeypatch):
        """Test MiniMax detection via heuristic when MINIMAX_API_KEY set."""
        monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
        assert ProviderRegistry.get_provider_for_model("abab6.5s-chat") == "minimax"
        assert ProviderRegistry.get_provider_for_model("MiniMax-M2.1") == "minimax"

    def test_detect_provider_minimax_no_key(self, monkeypatch):
        """Test MiniMax heuristic NOT triggered without MINIMAX_API_KEY."""
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        # Without key, abab model should NOT match minimax heuristic
        result = ProviderRegistry.get_provider_for_model("abab6.5s-chat")
        assert result != "minimax"

    def test_detect_provider_ollama_cloud(self, monkeypatch):
        """Test Ollama Cloud detection for open-source model patterns."""
        monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "test-ollama-key")
        monkeypatch.delenv("CLIPROXYAPI_BASE_URL", raising=False)
        assert ProviderRegistry.get_provider_for_model("llama3:8b") == "ollama-cloud"
        assert (
            ProviderRegistry.get_provider_for_model("qwen3-next:80b") == "ollama-cloud"
        )
        assert ProviderRegistry.get_provider_for_model("mistral-7b") == "ollama-cloud"
        assert ProviderRegistry.get_provider_for_model("gemma-2b") == "ollama-cloud"

    def test_detect_provider_deepseek_v3(self, monkeypatch):
        """Test deepseek-v3.x routes to ollama-cloud, NOT deepseek provider."""
        monkeypatch.setenv("OLLAMA_CLOUD_API_KEY", "test-ollama-key")
        monkeypatch.delenv("CLIPROXYAPI_BASE_URL", raising=False)
        assert (
            ProviderRegistry.get_provider_for_model("deepseek-v3.1") == "ollama-cloud"
        )
        assert ProviderRegistry.get_provider_for_model("deepseek-v3") == "ollama-cloud"

    def test_detect_provider_unknown_returns_none(self, monkeypatch):
        """Test that truly unknown models return None (not ValueError)."""
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_CLOUD_API_KEY", raising=False)
        monkeypatch.delenv("CLIPROXYAPI_BASE_URL", raising=False)
        result = ProviderRegistry.get_provider_for_model("unknown-model-xyz")
        assert result is None


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility."""

    def test_get_provider_timeout(self):
        """Test get_provider_timeout convenience function."""
        assert get_provider_timeout("deepseek") == 180
        assert get_provider_timeout("zai") == 180
        assert get_provider_timeout("cliproxyapi") == 120

    def test_get_timeout_for_model(self):
        """Test get_timeout_for_model convenience function."""
        assert get_timeout_for_model("glm-4.7") == 180
        assert get_timeout_for_model("deepseek-chat") == 180
        assert get_timeout_for_model("claude-opus-4-6-thinking") == 120


class TestProviderConfigDataclass:
    """Test ProviderConfig dataclass validation."""

    def test_valid_config(self):
        """Test creating a valid ProviderConfig."""
        config = ProviderConfig(
            provider_id="test",
            base_url="https://api.test.com/v1",
            env_key="TEST_API_KEY",
            timeout=120,
            vision=True,
            models=["test-model"],
        )
        assert config.provider_id == "test"
        assert config.timeout == 120

    def test_invalid_timeout(self):
        """Test that invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timeout"):
            ProviderConfig(
                provider_id="test",
                base_url="https://api.test.com/v1",
                env_key="TEST_API_KEY",
                timeout=0,  # Invalid
                vision=False,
                models=[],
            )


class TestConfigEndpoints:
    """Tests for config API endpoints."""

    def _load_config_module(self) -> ModuleType:
        module_name = "config_endpoint_test"
        if module_name in sys.modules:
            return sys.modules[module_name]

        mock_repo_manager = Mock()
        mock_repo_manager.RepositoryManager = Mock()
        mock_repo_manager.get_repository_manager = Mock()
        original_repo_manager = sys.modules.get(
            "app.db.repositories.repository_manager"
        )
        sys.modules["app.db.repositories.repository_manager"] = mock_repo_manager

        config_path = (
            Path(__file__).resolve().parent.parent
            / "app"
            / "api"
            / "endpoints"
            / "config.py"
        )
        spec = importlib.util.spec_from_file_location(module_name, config_path)
        if not spec or not spec.loader:
            raise RuntimeError("Failed to load config endpoint module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            if original_repo_manager is None:
                sys.modules.pop("app.db.repositories.repository_manager", None)
            else:
                sys.modules["app.db.repositories.repository_manager"] = (
                    original_repo_manager
                )
        return module

    @pytest.mark.asyncio
    async def test_available_models_cliproxyapi_dynamic(self, monkeypatch):
        config_endpoint = self._load_config_module()

        monkeypatch.setenv("CLIPROXYAPI_BASE_URL", "https://proxy.example.com/v1")
        monkeypatch.setenv("CLIPROXYAPI_API_KEY", "test-cliproxy-key")

        with patch.object(
            ProviderRegistry,
            "fetch_cliproxyapi_models",
            new_callable=AsyncMock,
            return_value=(["gpt-4o"], "ok"),
        ):
            payload = await config_endpoint.get_available_models()

        providers = {item["provider_id"]: item for item in payload["providers"]}
        cliproxyapi = providers["cliproxyapi"]
        assert cliproxyapi["models"] == ["gpt-4o"]
        assert cliproxyapi["is_configured"] is True
        assert cliproxyapi["base_url"] == "https://proxy.example.com/v1"
        assert cliproxyapi["cliproxy_reason"] == "ok"

    @pytest.mark.asyncio
    async def test_resolve_provider_unknown(self):
        config_endpoint = self._load_config_module()

        payload = await config_endpoint.resolve_provider("unknown-model-xyz")
        assert payload["provider_id"] is None
        assert payload["reason"] == "unknown_model"

    @pytest.mark.asyncio
    async def test_resolve_provider_cliproxy_reports_no_models(self, monkeypatch):
        config_endpoint = self._load_config_module()

        monkeypatch.setenv("CLIPROXYAPI_BASE_URL", "https://proxy.example.com/v1")
        monkeypatch.setenv("CLIPROXYAPI_API_KEY", "test-cliproxy-key")

        with patch.object(
            ProviderRegistry,
            "fetch_cliproxyapi_models",
            new_callable=AsyncMock,
            return_value=([], "empty"),
        ):
            payload = await config_endpoint.resolve_provider("gpt-4o")

        assert payload["provider_id"] == "cliproxyapi"
        assert payload["reason"] == "cliproxy_no_models"
        assert payload["cliproxy_reason"] == "empty"


class TestClipProxyApiCache:
    """Tests for CLIProxyAPI fetch_cliproxyapi_models TTL cache and locking."""

    def setup_method(self):
        ProviderRegistry.load()
        ProviderRegistry._cliproxy_cache_at = 0.0
        ProviderRegistry._cliproxy_lock = None
        ProviderRegistry._cliproxy_cache = []
        ProviderRegistry._cliproxy_cache_reason = "not_checked"

    @pytest.mark.asyncio
    async def test_cliproxyapi_cache_lock(self, monkeypatch):
        monkeypatch.setenv("CLIPROXYAPI_BASE_URL", "https://proxy.example.com/v1")
        monkeypatch.setenv("CLIPROXYAPI_API_KEY", "test-key")

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "data": [{"id": "gpt-4o"}, {"id": "claude-sonnet-4-5"}]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.rag.provider_registry.httpx.AsyncClient", return_value=mock_client
        ):
            results = await asyncio.gather(
                *[ProviderRegistry.fetch_cliproxyapi_models() for _ in range(5)]
            )

        assert mock_client.get.call_count == 1
        for models, reason in results:
            assert models == ["gpt-4o", "claude-sonnet-4-5"]
            assert reason == "ok"


class TestGenerationDefaults:
    """Tests for ProviderRegistry.get_generation_defaults."""

    def setup_method(self):
        ProviderRegistry.load()

    def test_generation_defaults_standard(self):
        defaults = ProviderRegistry.get_generation_defaults("deepseek", "deepseek-chat")
        assert set(defaults.keys()) == {"temperature", "max_length", "top_P"}
        assert defaults["temperature"] == 0.2
        assert defaults["max_length"] == 4096
        assert defaults["top_P"] == -1.0

    def test_generation_defaults_reasoner(self):
        defaults = ProviderRegistry.get_generation_defaults(
            "deepseek", "deepseek-reasoner"
        )
        assert defaults["temperature"] == -1.0
        assert defaults["top_P"] == -1.0
        assert defaults["max_length"] == 4096

    def test_generation_defaults_flash(self):
        defaults = ProviderRegistry.get_generation_defaults("zai", "glm-4-flash")
        assert defaults["max_length"] == 3072


class TestBackwardCompatShim:
    """Tests for ProviderClient backward-compatibility shim."""

    def setup_method(self):
        ProviderRegistry.load()

    def test_backward_compat_provider_client_shim(self):
        from app.rag.provider_client import ProviderClient

        assert ProviderClient.get_provider_for_model("deepseek-chat") == "deepseek"

    def test_backward_compat_get_all_providers(self):
        from app.rag.provider_client import ProviderClient

        assert (
            ProviderClient.get_all_providers() == ProviderRegistry.get_all_providers()
        )

    def test_backward_compat_is_vision_model(self):
        from app.rag.provider_client import ProviderClient

        assert ProviderClient.is_vision_model("gpt-4o") is True
        assert ProviderClient.is_vision_model("deepseek-chat") is False

"""
Tests for ProviderRegistry - unified provider configuration with timeout support.
"""

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
        assert ProviderRegistry.get_timeout_for_model("glm-4.7-flash") == 180
        assert ProviderRegistry.get_timeout_for_model("glm-4.6") == 180
        assert ProviderRegistry.get_timeout_for_model("glm-4-plus") == 180

    def test_get_timeout_for_model_deepseek(self):
        """Test timeout detection for DeepSeek models."""
        assert ProviderRegistry.get_timeout_for_model("deepseek-chat") == 180
        assert ProviderRegistry.get_timeout_for_model("deepseek-reasoner") == 180

    def test_get_timeout_for_model_claude(self):
        """Test timeout detection for Claude models (cliproxyapi)."""
        assert ProviderRegistry.get_timeout_for_model("claude-opus-4-5-thinking") == 120
        assert ProviderRegistry.get_timeout_for_model("claude-sonnet-4-5") == 120

    def test_get_timeout_for_model_gpt(self):
        """Test timeout detection for GPT models (cliproxyapi)."""
        assert ProviderRegistry.get_timeout_for_model("gpt-4o") == 120
        assert ProviderRegistry.get_timeout_for_model("gpt-4o-mini") == 120

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
        assert ProviderRegistry.is_vision_model("glm-4.5v") is True
        assert ProviderRegistry.is_vision_model("gemini-2.5-pro") is True
        assert ProviderRegistry.is_vision_model("llama3.2-vision") is True

        # Non-vision models (not in vision_patterns)
        assert ProviderRegistry.is_vision_model("deepseek-chat") is False
        assert ProviderRegistry.is_vision_model("MiniMax-M2.1") is False


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility."""

    def test_get_provider_timeout(self):
        """Test get_provider_timeout convenience function."""
        assert get_provider_timeout("deepseek") == 180
        assert get_provider_timeout("zai") == 180
        assert get_provider_timeout("cliproxyapi") == 120

    def test_get_timeout_for_model(self):
        """Test get_timeout_for_model convenience function."""
        assert get_timeout_for_model("glm-4.7-flash") == 180
        assert get_timeout_for_model("deepseek-chat") == 180
        assert get_timeout_for_model("claude-opus-4-5-thinking") == 120


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

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"data": [{"id": "gpt-4o"}]})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__.return_value = mock_client

        with patch.object(
            config_endpoint.httpx, "AsyncClient", return_value=mock_client
        ):
            payload = await config_endpoint.get_available_models()

        providers = {item["provider_id"]: item for item in payload["providers"]}
        cliproxyapi = providers["cliproxyapi"]
        assert cliproxyapi["models"] == ["gpt-4o"]
        assert cliproxyapi["is_configured"] is True
        assert cliproxyapi["base_url"] == "https://proxy.example.com/v1"
        assert cliproxyapi["cliproxy_reason"] == "ok"

        # Verify Authorization header is included when CLIPROXYAPI_API_KEY is present
        mock_client.get.assert_called_with(
            "https://proxy.example.com/v1/models",
            headers={"Authorization": "Bearer test-cliproxy-key"},
        )

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

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"data": []})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__.return_value = mock_client

        with patch.object(
            config_endpoint.httpx, "AsyncClient", return_value=mock_client
        ):
            payload = await config_endpoint.resolve_provider("gpt-4o")

        assert payload["provider_id"] == "cliproxyapi"
        assert payload["reason"] == "cliproxy_no_models"
        assert payload["cliproxy_reason"] == "cliproxyapi returned no models"

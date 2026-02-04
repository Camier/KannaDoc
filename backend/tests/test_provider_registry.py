"""
Tests for ProviderRegistry - unified provider configuration with timeout support.
"""

import pytest

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
        assert len(providers) >= 6  # deepseek, zai, zhipu, cliproxyapi, ollama-cloud, minimax
        assert "deepseek" in providers
        assert "zai" in providers
        assert "zhipu" in providers
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
        assert ProviderRegistry.get_timeout("zhipu") == 180
        assert ProviderRegistry.get_timeout("cliproxyapi") == 120
        assert ProviderRegistry.get_timeout("ollama-cloud") == 120
        assert ProviderRegistry.get_timeout("minimax") == 120

    def test_get_timeout_for_model_glm(self):
        """Test timeout detection for GLM models."""
        # GLM models should get 180s timeout (zai/zhipu)
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

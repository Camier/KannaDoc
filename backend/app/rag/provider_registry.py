"""
Unified Provider Registry - Façade over providers.yaml

This module provides a unified interface to provider configuration,
consolidating timeout configuration that was previously duplicated
in workflow/components/constants.py.

Usage:
    from app.rag.provider_registry import ProviderRegistry

    # Get timeout for a provider
    timeout = ProviderRegistry.get_timeout("deepseek")  # 180

    # Get timeout for a model (auto-detects provider)
    timeout = ProviderRegistry.get_timeout_for_model("glm-4.7-flash")  # 180

    # Get complete provider config
    config = ProviderRegistry.get_provider_config("zai")
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from app.core.logging import logger


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""

    provider_id: str
    base_url: str
    env_key: str
    timeout: int
    vision: bool
    models: List[str]

    def __post_init__(self):
        """Validate timeout is positive."""
        if self.timeout <= 0:
            raise ValueError(f"Invalid timeout for {self.provider_id}: {self.timeout}")


class ProviderRegistry:
    """
    Unified provider registry with timeout support.

    This class serves as a façade over providers.yaml, providing
    a single source of truth for provider configuration including
    timeouts that were previously duplicated in constants.py.
    """

    _config: Dict[str, Any] = {}
    _providers: Dict[str, ProviderConfig] = {}
    _default_timeout: int = 120

    @classmethod
    def load(cls) -> None:
        """Load provider configuration from providers.yaml."""
        if cls._providers:
            return  # Already loaded

        config_path = Path(__file__).parent.parent / "core" / "llm" / "providers.yaml"
        with open(config_path) as f:
            cls._config = yaml.safe_load(f)

        # Extract default timeout
        cls._default_timeout = cls._config.get("default_timeout", 120)

        # Build provider configs
        for provider_id, provider_data in cls._config.get("providers", {}).items():
            cls._providers[provider_id] = ProviderConfig(
                provider_id=provider_id,
                base_url=provider_data.get("base_url", ""),
                env_key=provider_data.get("env_key", ""),
                timeout=provider_data.get("timeout", cls._default_timeout),
                vision=provider_data.get("vision", False),
                models=provider_data.get("models", []),
            )

        logger.info(
            f"ProviderRegistry loaded: {len(cls._providers)} providers, "
            f"default_timeout={cls._default_timeout}s"
        )

    @classmethod
    def get_provider_config(cls, provider_id: str) -> ProviderConfig:
        """
        Get complete configuration for a provider.

        Args:
            provider_id: Provider identifier (e.g., "deepseek", "zai")

        Returns:
            ProviderConfig with all provider settings

        Raises:
            ValueError: If provider not found
        """
        cls.load()
        if provider_id not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_id}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[provider_id]

    @classmethod
    def get_timeout(cls, provider_id: str) -> int:
        """
        Get timeout in seconds for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Timeout in seconds (from provider config or default)

        Raises:
            ValueError: If provider not found
        """
        config = cls.get_provider_config(provider_id)
        return config.timeout

    @classmethod
    def get_timeout_for_model(cls, model_name: str) -> int:
        """
        Get timeout for a model by auto-detecting its provider.

        Uses the same detection logic as ProviderClient:
        1. Check if model matches CLIProxyAPI (if CLIPROXYAPI_BASE_URL set)
        2. Check GLM family (zai)
        3. Generic provider matching

        Args:
            model_name: Model name (e.g., "glm-4.7-flash", "deepseek-chat")

        Returns:
            Timeout in seconds

        Raises:
            ValueError: If provider cannot be detected
        """
        provider_id = cls._detect_provider(model_name)
        return cls.get_timeout(provider_id)

    @classmethod
    def _detect_provider(cls, model_name: str) -> str:
        """
        Detect provider for a model name.

        Mirrors ProviderClient.get_provider_for_model() logic.
        """
        cls.load()  # Ensure providers are loaded
        model_lower = model_name.lower()

        # 1. CLIProxyAPI precedence
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            cliproxyapi_config = cls._providers.get("cliproxyapi")
            if cliproxyapi_config:
                for model_pattern in cliproxyapi_config.models:
                    if (
                        model_pattern.lower() in model_lower
                        or model_lower in model_pattern.lower()
                    ):
                        return "cliproxyapi"

        # 2. GLM family special resolution (Z.ai SSOT)
        if any(x in model_lower for x in ["glm-4", "glm-4.5", "glm-4.6", "glm-4.7"]):
            if os.getenv("ZAI_API_KEY"):
                return "zai"
            return "zai"  # Default

        # 3. Generic provider matching
        for provider_id, config in cls._providers.items():
            for model_pattern in config.models:
                if model_pattern.lower() in model_lower:
                    return provider_id

        raise ValueError(
            f"Cannot detect provider for model: {model_name}. "
            f"Available providers: {list(cls._providers.keys())}"
        )

    @classmethod
    def get_all_providers(cls) -> List[str]:
        """Get list of all provider IDs."""
        cls.load()
        return list(cls._providers.keys())

    @classmethod
    def get_models_for_provider(cls, provider_id: str) -> List[str]:
        """Get list of models for a specific provider."""
        config = cls.get_provider_config(provider_id)
        return config.models

    @classmethod
    def is_vision_model(cls, model_name: str) -> bool:
        """
        Check if a model supports vision.

        Uses vision_patterns from providers.yaml.
        """
        cls.load()
        vision_patterns = cls._config.get("vision_patterns", [])
        model_lower = model_name.lower()
        return any(pattern.lower() in model_lower for pattern in vision_patterns)


# Convenience functions for backward compatibility
def get_provider_timeout(provider_id: str) -> int:
    """Get timeout for a provider (convenience function)."""
    return ProviderRegistry.get_timeout(provider_id)


def get_timeout_for_model(model_name: str) -> int:
    """Get timeout for a model (convenience function)."""
    return ProviderRegistry.get_timeout_for_model(model_name)


__all__ = [
    "ProviderRegistry",
    "ProviderConfig",
    "get_provider_timeout",
    "get_timeout_for_model",
]

"""
Unified Provider Registry - Façade over providers.yaml

Single source of truth for provider configuration, detection, timeout,
and client creation. Consolidates logic from ProviderClient + constants.py.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
from openai import AsyncOpenAI

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
    """Unified provider registry — façade over providers.yaml with detection, timeout, and client creation."""

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
        """Get complete configuration for a provider. Raises ValueError if not found."""
        cls.load()
        if provider_id not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_id}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[provider_id]

    @classmethod
    def get_timeout(cls, provider_id: str) -> int:
        """Get timeout in seconds for a provider."""
        config = cls.get_provider_config(provider_id)
        return config.timeout

    @classmethod
    def get_timeout_for_model(cls, model_name: str) -> int:
        """Get timeout for a model by auto-detecting its provider. Raises ValueError if undetectable."""
        provider_id = cls.get_provider_for_model(model_name)
        if not provider_id:
            raise ValueError(
                f"Cannot detect provider for model: {model_name}. "
                f"Available providers: {list(cls._providers.keys())}"
            )
        return cls.get_timeout(provider_id)

    # ── Detection & Resolution ──────────────────────────────────────────

    @classmethod
    def get_provider_for_model(
        cls, model_name: str, explicit_provider: Optional[str] = None
    ) -> Optional[str]:
        """Detect provider from model name, or use explicit_provider if given."""
        cls.load()

        if explicit_provider:
            if explicit_provider in cls._providers:
                logger.debug(
                    f"Using explicit provider: {explicit_provider} for model '{model_name}'"
                )
                return explicit_provider
            logger.warning(
                f"Explicit provider '{explicit_provider}' not found in config"
            )

        model_lower = model_name.lower()

        # Ollama Cloud override for gpt-oss models when key is present
        if "gpt-oss" in model_lower and os.getenv("OLLAMA_CLOUD_API_KEY"):
            logger.debug(
                f"Provider detected: ollama-cloud for model '{model_name}' (OLLAMA_CLOUD_API_KEY set)"
            )
            return "ollama-cloud"

        # Ollama Cloud open-source models
        ollama_patterns = [
            "llama",
            "qwen",
            "mistral",
            "gemma",
            "cogito",
            "kimi",
            "nemotron",
            "devstral",
            "ministral",
            "rnj-",
        ]
        if os.getenv("OLLAMA_CLOUD_API_KEY"):
            if any(p in model_lower for p in ollama_patterns):
                logger.debug(
                    f"Provider detected: ollama-cloud for model '{model_name}'"
                )
                return "ollama-cloud"
            # deepseek-v3.x on Ollama (not official DeepSeek API)
            if model_lower.startswith("deepseek-v3"):
                logger.debug(
                    f"Provider detected: ollama-cloud for model '{model_name}'"
                )
                return "ollama-cloud"

        # Antigravity: Check FIRST when configured
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            cliproxyapi_config = cls._providers.get("cliproxyapi")
            if cliproxyapi_config:
                for model_pattern in cliproxyapi_config.models:
                    if (
                        model_pattern.lower() in model_lower
                        or model_lower in model_pattern.lower()
                    ):
                        logger.debug(
                            f"Provider detected: cliproxyapi for model '{model_name}'"
                        )
                        return "cliproxyapi"

            # Heuristic fallback: cliproxyapi can proxy many OpenAI-compatible model ids
            # beyond the static providers.yaml list. Keep this gated on CLIPROXYAPI_BASE_URL
            # so we don't "detect" an unconfigured provider.
            if "gpt-oss" not in model_lower:
                if (
                    model_lower.startswith("gpt-")
                    or model_lower.startswith("codex-")
                    or model_lower.startswith("o1")
                    or model_lower.startswith("o3")
                    or "claude" in model_lower
                    or "gemini" in model_lower
                ):
                    logger.debug(
                        f"Provider detected: cliproxyapi for model '{model_name}' (heuristic)"
                    )
                    return "cliproxyapi"

        # GLM models -> zai (Z.ai). This repo treats Z.ai as SSOT for GLM endpoints.
        if any(x in model_lower for x in ["glm-4", "glm-4.5", "glm-4.6", "glm-4.7"]):
            if os.getenv("ZAI_API_KEY"):
                logger.debug(
                    f"Provider detected: zai for model '{model_name}' (ZAI_API_KEY set)"
                )
                return "zai"
            logger.debug(
                f"Provider detected: zai for model '{model_name}' (default, no key set)"
            )
            return "zai"

        # MiniMax: support evolving model ids beyond the static providers.yaml list.
        # Keep this gated on MINIMAX_API_KEY so we don't "detect" an unconfigured provider.
        if os.getenv("MINIMAX_API_KEY"):
            if model_lower.startswith("abab") or "minimax" in model_lower:
                logger.debug(
                    f"Provider detected: minimax for model '{model_name}' (heuristic)"
                )
                return "minimax"

        # Generic provider matching
        for provider_id, config in cls._providers.items():
            for model_pattern in config.models:
                if model_pattern.lower() in model_lower:
                    logger.debug(
                        f"Provider detected: {provider_id} for model '{model_name}'"
                    )
                    return provider_id

        logger.warning(
            f"No provider detected for model '{model_name}'. "
            f"Available providers: {list(cls._providers.keys())}"
        )
        return None

    @classmethod
    def get_env_hint_for_model(cls, model_name: str) -> str:
        """Get hint about which env var is needed for a model."""
        model_lower = model_name.lower()

        if any(x in model_lower for x in ["glm-4", "glm-4.5", "glm-4.6", "glm-4.7"]):
            return "Set ZAI_API_KEY for GLM models"
        if "deepseek" in model_lower:
            return "Set DEEPSEEK_API_KEY for DeepSeek models"
        if "gpt-oss" in model_lower:
            return "Set OLLAMA_CLOUD_API_KEY for Ollama Cloud models"
        if any(
            x in model_lower for x in ["claude", "gpt", "gemini", "o1", "o3", "codex"]
        ):
            return "Set CLIPROXYAPI_BASE_URL and CLIPROXYAPI_API_KEY for proxied models"
        if any(x in model_lower for x in ["llama", "qwen", "mistral"]):
            return "Set OLLAMA_CLOUD_API_KEY for Ollama Cloud models"
        if "minimax" in model_lower or model_lower.startswith("abab"):
            return "Set MINIMAX_API_KEY for MiniMax models"

        return (
            "Check providers.yaml for supported models. "
            f"Available: {list(cls._providers.keys())}"
        )

    @classmethod
    def resolve_api_model_name(
        cls, model_name: str, provider: Optional[str] = None
    ) -> str:
        """Map legacy/alias model names to provider API model ids."""
        model_lower = model_name.lower()
        provider_lower = (provider or "").strip().lower() or None

        # Ollama Cloud uses colon-delimited ids (e.g. gpt-oss:120b), but other
        # providers (notably CLIProxyAPI) may expose the hyphenated alias as-is.
        if model_lower == "gpt-oss-120b-medium" and provider_lower == "ollama-cloud":
            return "gpt-oss:120b"

        return model_name

    # ── Client Creation ─────────────────────────────────────────────────

    @classmethod
    def get_llm_client(
        cls,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> AsyncOpenAI:
        """Create an OpenAI-compatible async client for the specified model."""
        cls.load()

        # Detect provider if not specified
        if not provider:
            provider = cls.get_provider_for_model(model_name)
        if not provider:
            hint = cls.get_env_hint_for_model(model_name)
            raise ValueError(f"Cannot detect provider for model: {model_name}. {hint}")

        # Get provider config
        provider_config = cls._providers.get(provider)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider}")

        # Get API key (priority: parameter > env var)
        if not api_key:
            api_key = os.getenv(provider_config.env_key)
            if not api_key:
                raise ValueError(
                    f"API key for {provider} not found. "
                    f"Set {provider_config.env_key} environment variable."
                )

        # Get base URL (priority: parameter > provider default)
        if not base_url:
            if provider == "cliproxyapi":
                base_url = os.getenv("CLIPROXYAPI_BASE_URL")
                if not base_url:
                    raise ValueError(
                        "CLIProxyAPI base URL not configured. "
                        "Set CLIPROXYAPI_BASE_URL (e.g. http://host.docker.internal:8317/v1)."
                    )
            else:
                base_url = provider_config.base_url

        logger.info(
            f"Creating {provider} client for model '{model_name}' "
            f"(base_url: {base_url})"
        )

        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=600.0,
        )

    @classmethod
    def get_default_client(cls) -> AsyncOpenAI:
        """Get client for default provider (from env or fallback to DeepSeek)."""
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "deepseek")
        default_model = os.getenv("DEFAULT_LLM_MODEL", "deepseek-chat")
        return cls.get_llm_client(model_name=default_model, provider=default_provider)

    @classmethod
    def get_cliproxyapi_models_with_defaults(cls) -> List[dict]:
        """Get CLIProxyAPI models with group, base_url and vision defaults."""
        cls.load()
        config = cls._providers.get("cliproxyapi")
        models = config.models if config else []
        base_url = os.getenv("CLIPROXYAPI_BASE_URL", "")

        result = []
        for model_name in models:
            result.append(
                {
                    "name": model_name,
                    "group": "CLIProxyAPI",
                    "base_url": base_url,
                    "vision": cls.is_vision_model(model_name),
                }
            )
        return result

    # ── Query Methods ───────────────────────────────────────────────────

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
        """Check if a model supports vision using vision_patterns from providers.yaml."""
        cls.load()
        vision_patterns = cls._config.get("vision_patterns", [])
        model_lower = model_name.lower()
        return any(pattern.lower() in model_lower for pattern in vision_patterns)


# ── Convenience Functions ───────────────────────────────────────────────


def get_provider_timeout(provider_id: str) -> int:
    """Get timeout for a provider (convenience function)."""
    return ProviderRegistry.get_timeout(provider_id)


def get_timeout_for_model(model_name: str) -> int:
    """Get timeout for a model (convenience function)."""
    return ProviderRegistry.get_timeout_for_model(model_name)


def get_llm_client(
    model_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    provider: Optional[str] = None,
) -> AsyncOpenAI:
    """Get an LLM client for the specified model (convenience function)."""
    return ProviderRegistry.get_llm_client(
        model_name=model_name, api_key=api_key, base_url=base_url, provider=provider
    )


def resolve_api_model_name(model_name: str, provider: Optional[str] = None) -> str:
    """Map legacy/alias model names to provider API model ids (convenience function)."""
    return ProviderRegistry.resolve_api_model_name(model_name, provider)


def get_provider_for_model(
    model_name: str, explicit_provider: Optional[str] = None
) -> Optional[str]:
    """Detect provider from model name (convenience function)."""
    return ProviderRegistry.get_provider_for_model(model_name, explicit_provider)


__all__ = [
    "ProviderRegistry",
    "ProviderConfig",
    "get_provider_timeout",
    "get_timeout_for_model",
    "get_llm_client",
    "resolve_api_model_name",
    "get_provider_for_model",
]

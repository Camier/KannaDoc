"""
LLM Provider Client - Direct API Access
Replaces LiteLLM proxy with direct provider calls

Supported Providers (2026 stack):
- DeepSeek (R1, Chat, Reasoner)
- Z.ai (GLM-4.5/4.6/4.7) - Z.ai GLM Coding Plan
- Zhipu (GLM-4/4.7) - Direct Zhipu API
- Antigravity via CLIProxyAPI (proxied models)
- Ollama Cloud (Llama, DeepSeek, Qwen)
- MiniMax (M2.1)
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml
from openai import AsyncOpenAI
from app.core.logging import logger


def _load_providers_config() -> Dict[str, Any]:
    """Load provider configuration from YAML file.

    Returns the full config dict with 'providers' and 'vision_patterns' keys.
    """
    config_path = Path(__file__).parent.parent / "core/llm/providers.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


class ProviderClient:
    """Factory for creating provider-specific OpenAI-compatible clients"""

    _config = _load_providers_config()
    PROVIDERS = _config["providers"]
    VISION_MODELS = _config["vision_patterns"]

    @classmethod
    def is_vision_model(cls, model_name: str) -> bool:
        """Check if model supports vision/image input"""
        model_lower = model_name.lower()
        return any(v in model_lower for v in cls.VISION_MODELS)

    @classmethod
    def get_provider_for_model(
        cls, model_name: str, explicit_provider: Optional[str] = None
    ) -> Optional[str]:
        """Detect provider from model name, or use explicit_provider if given."""
        if explicit_provider:
            if explicit_provider in cls.PROVIDERS:
                logger.debug(
                    f"Using explicit provider: {explicit_provider} for model '{model_name}'"
                )
                return explicit_provider
            logger.warning(
                f"Explicit provider '{explicit_provider}' not found in config"
            )

        model_lower = model_name.lower()

        # Antigravity: Check FIRST when configured
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            cliproxyapi_models = cls.PROVIDERS.get("cliproxyapi", {}).get("models", [])
            for model_pattern in cliproxyapi_models:
                if (
                    model_pattern.lower() in model_lower
                    or model_lower in model_pattern.lower()
                ):
                    logger.debug(
                        f"Provider detected: cliproxyapi for model '{model_name}'"
                    )
                    return "cliproxyapi"

        # GLM models -> zai (ZAI_API_KEY) or zhipu (ZHIPUAI_API_KEY)
        if any(x in model_lower for x in ["glm-4", "glm-4.5", "glm-4.6", "glm-4.7"]):
            if os.getenv("ZAI_API_KEY"):
                logger.debug(
                    f"Provider detected: zai for model '{model_name}' (ZAI_API_KEY set)"
                )
                return "zai"
            elif os.getenv("ZHIPUAI_API_KEY"):
                logger.debug(
                    f"Provider detected: zhipu for model '{model_name}' (ZHIPUAI_API_KEY set)"
                )
                return "zhipu"
            logger.debug(
                f"Provider detected: zai for model '{model_name}' (default, no key set)"
            )
            return "zai"

        # Generic provider matching
        for provider, config in cls.PROVIDERS.items():
            for model_pattern in config["models"]:
                if model_pattern.lower() in model_lower:
                    logger.debug(
                        f"Provider detected: {provider} for model '{model_name}'"
                    )
                    return provider

        logger.warning(
            f"No provider detected for model '{model_name}'. "
            f"Available providers: {list(cls.PROVIDERS.keys())}"
        )
        return None

    @classmethod
    def get_env_hint_for_model(cls, model_name: str) -> str:
        """Get hint about which env var is needed for a model."""
        model_lower = model_name.lower()

        if any(x in model_lower for x in ["glm-4", "glm-4.5", "glm-4.6", "glm-4.7"]):
            return "Set ZAI_API_KEY or ZHIPUAI_API_KEY for GLM models"
        if "deepseek" in model_lower:
            return "Set DEEPSEEK_API_KEY for DeepSeek models"
        if any(x in model_lower for x in ["claude", "gpt", "gemini", "o1", "o3"]):
            return "Set CLIPROXYAPI_BASE_URL and CLIPROXYAPI_API_KEY for proxied models"
        if any(x in model_lower for x in ["llama", "qwen", "mistral"]):
            return "Set OLLAMA_CLOUD_API_KEY for Ollama Cloud models"
        if "minimax" in model_lower:
            return "Set MINIMAX_API_KEY for MiniMax models"

        return f"Check providers.yaml for supported models. Available: {list(cls.PROVIDERS.keys())}"

    @classmethod
    def get_all_providers(cls) -> List[str]:
        """Get list of all supported provider names"""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def get_models_for_provider(cls, provider: str) -> List[str]:
        """Get list of models for a specific provider"""
        config = cls.PROVIDERS.get(provider, {})
        return config.get("models", [])

    @classmethod
    def create_client(
        cls,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> AsyncOpenAI:
        """
        Create an OpenAI-compatible async client for the specified model.

        Args:
            model_name: Name of the model (e.g., "gpt-4o", "deepseek-reasoner")
            api_key: Optional API key (if None, reads from env)
            base_url: Optional base URL (if None, uses provider default)
            provider: Optional provider name (if None, auto-detects from model)

        Returns:
            AsyncOpenAI client configured for the provider

        Note: For local deployments (e.g., local Ollama), pass base_url parameter:
            client = ProviderClient.create_client(
                model_name="llama3",
                base_url="http://127.0.0.1:11434/v1"
            )
        """
        # Detect provider if not specified
        if not provider:
            provider = cls.get_provider_for_model(model_name)
        if not provider:
            hint = cls.get_env_hint_for_model(model_name)
            raise ValueError(f"Cannot detect provider for model: {model_name}. {hint}")

        # Get provider config
        provider_config = cls.PROVIDERS.get(provider)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider}")

        # Get API key (priority: parameter > env var)
        if not api_key:
            api_key = os.getenv(provider_config["env_key"])
            if not api_key:
                raise ValueError(
                    f"API key for {provider} not found. "
                    f"Set {provider_config['env_key']} environment variable."
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
                base_url = provider_config["base_url"]

        logger.info(
            f"Creating {provider} client for model '{model_name}' "
            f"(base_url: {base_url})"
        )

        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=600.0,  # Match LiteLLM timeout
        )

    @classmethod
    def get_default_client(cls) -> AsyncOpenAI:
        """Get client for default provider (from env or fallback to DeepSeek)"""
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "deepseek")
        default_model = os.getenv("DEFAULT_LLM_MODEL", "deepseek-chat")

        return cls.create_client(model_name=default_model, provider=default_provider)

    @classmethod
    def get_cliproxyapi_models_with_defaults(cls) -> List[dict]:
        """Get CLIProxyAPI models with group, base_url and vision defaults"""
        config = cls.PROVIDERS.get("cliproxyapi", {})
        models = config.get("models", [])
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


# Convenience function for backward compatibility
def get_llm_client(
    model_name: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    provider: Optional[str] = None,
) -> AsyncOpenAI:
    """
    Get an LLM client for the specified model.
    This replaces the old LiteLLM proxy approach.

    Usage:
        client = get_llm_client("gpt-4o")
        # or with custom key
        client = get_llm_client("deepseek-reasoner", api_key="sk-...")
        # or with local deployment URL
        client = get_llm_client("llama3", base_url="http://127.0.0.1:11434/v1")
        # or with explicit provider
        client = get_llm_client("glm-4.7-flash", provider="zhipu")
    """
    return ProviderClient.create_client(
        model_name=model_name, api_key=api_key, base_url=base_url, provider=provider
    )

"""
LLM Provider Client - Direct API Access
Replaces LiteLLM proxy with direct provider calls
"""

import os
from typing import Optional
from openai import AsyncOpenAI
from app.core.logging import logger


class ProviderClient:
    """Factory for creating provider-specific OpenAI-compatible clients"""

    # Provider configurations
    # Updated 2026-01-25: Latest models from January 2026
    PROVIDERS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "env_key": "OPENAI_API_KEY",
            # Updated: Added GPT-5.2, GPT-4.1, GPT-4.5 (Jan 2026)
            # Note: gpt-4o-mini deprecates Feb 27, 2026 - use gpt-4o instead
            "models": [
                "gpt-5.2",
                "gpt-4.1",
                "gpt-4.5",
                "gpt-4o",
                "gpt-4",
                "gpt-4o-mini",
                "gpt-3.5-turbo",
            ],
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "env_key": "DEEPSEEK_API_KEY",
            # Updated: Added V3.2 models (Dec 2025) - outperforms GPT-5 on reasoning
            "models": [
                "deepseek-v3.2",
                "deepseek-v3.2-speciale",
                "deepseek-r1",
                "deepseek-chat",
                "deepseek-reasoner",
            ],
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "env_key": "ANTHROPIC_API_KEY",
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "env_key": "GEMINI_API_KEY",
            "models": ["gemini-pro", "gemini-2.5-pro", "gemini-2.5-flash"],
        },
        # Chinese AI providers
        "moonshot": {
            "base_url": "https://api.moonshot.cn/v1",
            "env_key": "MOONSHOT_API_KEY",
            # Updated: Added Kimi K2 models (Nov 2025) - trillion-param, 256K context
            # K2 Thinking: Advanced reasoning with long-horizon capabilities
            # Pricing reduced by 75% compared to V1!
            "models": [
                "kimi-k2-thinking",
                "kimi-k2-thinking-turbo",
                "moonshot-v1-8k",
                "moonshot-v1-32k",
                "moonshot-v1-128k",
            ],
        },
        "zhipu": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "env_key": "ZHIPUAI_API_KEY",
            # Updated: Added GLM-4.7 models (Jan 2026) - 358B params, 200K context
            # GLM-4.7: 90.1% MMLU, 95.7% AIME - beats GPT-OSS-20B
            # GLM-4.7-Flash: Optimized for speed with MoE architecture
            "models": [
                "glm-4.7",
                "glm-4.7-flash",
                "glm-4-plus",
                "glm-4-air",
                "glm-4-flash",
                "glm-4-0520",
            ],
        },
        "minimax": {
            "base_url": "https://api.minimax.chat/v1",
            "env_key": "MINIMAX_API_KEY",
            "models": ["abab6.5s-chat", "abab6.5g-chat", "abab6.5t-chat"],
        },
        "cohere": {
            "base_url": "https://api.cohere.ai/v1",
            "env_key": "COHERE_API_KEY",
            "models": ["command-r-plus", "command-r", "command"],
        },
        "ollama": {
            "base_url": "https://api.ollama.ai/v1",
            "env_key": "OLLAMA_API_KEY",
            "models": ["llama3", "mistral", "mixtral"],
        },
    }

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[str]:
        """Detect provider from model name"""
        model_lower = model_name.lower()

        # Check each provider's model list
        for provider, config in cls.PROVIDERS.items():
            for model_pattern in config["models"]:
                if model_pattern.lower() in model_lower:
                    return provider

        # Fallback: check for provider name in model name
        # Updated 2026-01-25: Added new model patterns
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "deepseek" in model_lower:
            return "deepseek"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "gemini"
        elif "moonshot" in model_lower or "kimi" in model_lower or "k2" in model_lower:
            return "moonshot"
        elif "glm" in model_lower or "zhipu" in model_lower:
            return "zhipu"
        elif "abab" in model_lower or "minimax" in model_lower:
            return "minimax"
        elif "command" in model_lower or "cohere" in model_lower:
            return "cohere"
        elif (
            "llama" in model_lower
            or "ollama" in model_lower
            or "mistral" in model_lower
            or "mixtral" in model_lower
        ):
            return "ollama"

        # Default to OpenAI if unknown
        logger.warning(
            f"Unknown model provider for '{model_name}', defaulting to OpenAI"
        )
        return "openai"

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
        """Get client for default provider (from env or fallback to OpenAI)"""
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")

        return cls.create_client(model_name=default_model, provider=default_provider)


# Convenience function for backward compatibility
def get_llm_client(
    model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None
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
    """
    return ProviderClient.create_client(
        model_name=model_name, api_key=api_key, base_url=base_url
    )

"""
LLM Provider Client - Direct API Access
Replaces LiteLLM proxy with direct provider calls

Supported Providers (January 2026):
- OpenAI (GPT-4o, GPT-4.1, GPT-4.5, GPT-5.2)
- DeepSeek (R1, Chat, Reasoner)
- Anthropic (Claude 3/4 series)
- Google (Gemini 2.5/3 series)
- ZhipuAI (GLM-4 series) - direct ZhipuAI API
- ZhipuAI Coding (GLM-4.5/4.6/4.7) - direct ZhipuAI coding endpoint
- Z.ai (GLM-4.5/4.6/4.7) - Z.ai GLM Coding Plan (https://z.ai)
- Moonshot (Kimi K2)
- Ollama Cloud (Llama, Mistral, Mixtral)
- Antigravity via CLIProxyAPI (OpenAI-compatible proxy)
- MiniMax, Cohere
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


def _generate_zhipu_jwt(api_key: str) -> str:
    """Generate JWT token for ZhipuAI API authentication.

    ZhipuAI API keys are in format: id.secret
    This function generates a JWT token with HMAC-SHA256 signature.
    """
    import hashlib
    import hmac
    import base64
    import json
    import time

    if "." not in api_key:
        # Z.ai keys don't have dots, but Zhipu keys do.
        # If we routed to Zhipu but have a Z.ai key, this is a misconfiguration.
        raise ValueError(
            f"Invalid ZhipuAI API key format: {api_key[:8]}... "
            "ZhipuAI keys must be in 'id.secret' format. "
            "If this is a Z.ai key, ensure ZAI_API_KEY is set in environment."
        )

    api_id, api_secret = api_key.split(".", 1)

    # JWT Header
    header = {"alg": "HS256", "sign_type": "SIGN"}

    # JWT Payload
    timestamp = int(time.time())
    payload = {"api_key": api_id, "exp": timestamp + 3600, "timestamp": timestamp}

    # Encode
    header_encoded = (
        base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )

    payload_encoded = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )

    # Sign
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).digest()

    signature_encoded = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{message}.{signature_encoded}"


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
    def get_provider_for_model(cls, model_name: str) -> Optional[str]:
        """Detect provider from model name"""
        model_lower = model_name.lower()

        # CLIProxyAPI: Check FIRST when env is configured
        # This allows CLIProxyAPI models (gemini-*, claude-*, gpt-*, etc.) to route correctly
        # instead of falling through to native provider detection
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            cliproxyapi_models = cls.PROVIDERS.get("cliproxyapi", {}).get("models", [])
            for model_pattern in cliproxyapi_models:
                if (
                    model_pattern.lower() == model_lower
                    or model_pattern.lower() in model_lower
                ):
                    return "cliproxyapi"

        # Check specific providers first before generic loop
        if any(
            model_lower.startswith(prefix)
            for prefix in ["gemini-cli-", "codex-", "qwen-cli-"]
        ):
            return "cliproxyapi"

        # GLM coding models (4.5/4.6/4.7) - prefer Z.ai if ZAI_API_KEY is set
        # Z.ai is the GLM Coding Plan provider (https://z.ai)
        if any(x in model_lower for x in ["glm-4.5", "glm-4.6", "glm-4.7"]):
            if os.getenv("ZAI_API_KEY"):
                return "zai"
            return "zhipu-coding"

        for provider, config in cls.PROVIDERS.items():
            for model_pattern in config["models"]:
                if model_pattern.lower() in model_lower:
                    return provider

        if "antigravity" in model_lower:
            return "cliproxyapi"
        elif (
            "gpt" in model_lower
            or "openai" in model_lower
            or model_lower.startswith("o1")
        ):
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
            or "mistral" in model_lower
            or "mixtral" in model_lower
        ):
            if os.getenv("OLLAMA_CLOUD_API_KEY"):
                return "ollama-cloud"
            return "ollama-local"
        elif "phi" in model_lower or "gemma" in model_lower:
            return "ollama-cloud"

        logger.warning(
            f"Unknown model provider for '{model_name}', defaulting to OpenAI"
        )
        return "openai"

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
            raise ValueError(f"Cannot detect provider for model: {model_name}")

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

        # Generate JWT token for ZhipuAI (both regular and coding endpoints)
        if provider in ("zhipu", "zhipu-coding"):
            api_key = _generate_zhipu_jwt(api_key)

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
        """Get client for default provider (from env or fallback to OpenAI)"""
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")

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

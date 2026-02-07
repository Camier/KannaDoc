"""Backward-compatibility shim. All logic now lives in ProviderRegistry."""

from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from app.rag.provider_registry import (
    ProviderRegistry,
    get_llm_client,
    resolve_api_model_name,
    get_provider_for_model,
)


class ProviderClient:
    """Backward-compatibility shim for ProviderRegistry."""

    ProviderRegistry.load()
    PROVIDERS = ProviderRegistry._config.get("providers", {})
    VISION_MODELS = ProviderRegistry._config.get("vision_patterns", [])

    @classmethod
    def get_provider_for_model(cls, model_name, explicit_provider=None):
        return ProviderRegistry.get_provider_for_model(model_name, explicit_provider)

    @classmethod
    def get_env_hint_for_model(cls, model_name):
        return ProviderRegistry.get_env_hint_for_model(model_name)

    @classmethod
    def create_client(cls, model_name, api_key=None, base_url=None, provider=None):
        return ProviderRegistry.get_llm_client(model_name, api_key, base_url, provider)

    @classmethod
    def get_default_client(cls):
        return ProviderRegistry.get_default_client()

    @classmethod
    def get_all_providers(cls):
        return ProviderRegistry.get_all_providers()

    @classmethod
    def get_models_for_provider(cls, provider):
        return ProviderRegistry.get_models_for_provider(provider)

    @classmethod
    def is_vision_model(cls, model_name):
        return ProviderRegistry.is_vision_model(model_name)

    @classmethod
    def get_cliproxyapi_models_with_defaults(cls):
        return ProviderRegistry.get_cliproxyapi_models_with_defaults()

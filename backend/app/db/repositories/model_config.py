import os
import time
from typing import Optional, Dict, Any, List, cast

import httpx
from app.core.logging import logger
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from app.db.cache import cache_service


_CLIPROXY_MODELS_CACHE_TTL_S = 10.0
_cliproxy_models_cache: List[str] = []
_cliproxy_models_cache_reason: str = "not_checked"
_cliproxy_models_cache_at: float = 0.0


async def _fetch_cliproxyapi_live_models() -> tuple[List[str], str]:
    """Fetch live model IDs from CLIProxyAPI (OpenAI-compatible /v1/models).

    This is used to avoid advertising proxied models when CLIProxyAPI is not
    actually configured (e.g. /v1/models returns empty).

    Returns: (models, reason)
    - models: list of model ids
    - reason: short diagnostic string (non-sensitive)
    """

    global \
        _cliproxy_models_cache, \
        _cliproxy_models_cache_at, \
        _cliproxy_models_cache_reason

    now = time.time()
    if now - _cliproxy_models_cache_at < _CLIPROXY_MODELS_CACHE_TTL_S:
        return list(_cliproxy_models_cache), _cliproxy_models_cache_reason

    base_url = os.getenv("CLIPROXYAPI_BASE_URL", "").rstrip("/")
    if not base_url:
        _cliproxy_models_cache = []
        _cliproxy_models_cache_reason = "missing_base_url"
        _cliproxy_models_cache_at = now
        return [], _cliproxy_models_cache_reason

    api_key = os.getenv("CLIPROXYAPI_API_KEY", "")
    headers = {"User-Agent": "layra"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    models_url = f"{base_url}/models"

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(models_url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.TimeoutException:
        models = []
        reason = "timeout"
    except httpx.HTTPError as exc:
        models = []
        reason = f"http_error:{exc.__class__.__name__}"
    except (ValueError, TypeError):
        models = []
        reason = "invalid_response"
    else:
        data = payload.get("data", []) if isinstance(payload, dict) else []
        models = [
            str(item.get("id"))
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        reason = "ok" if models else "empty"

    _cliproxy_models_cache = list(models)
    _cliproxy_models_cache_reason = reason
    _cliproxy_models_cache_at = now
    return list(models), reason


class ModelConfigRepository(BaseRepository):
    def _build_model_dict(
        self,
        model_id: str,
        model_name: str,
        model_url: str,
        api_key: str,
        base_used: list,
        system_prompt: str,
        temperature: float,
        max_length: int,
        top_P: float,
        top_K: int,
        score_threshold: int,
        provider: Optional[str] = None,
    ) -> dict:
        result = {
            "model_id": model_id,
            "model_name": model_name,
            "model_url": model_url,
            "api_key": api_key,
            "base_used": base_used,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "max_length": max_length,
            "top_P": top_P,
            "top_K": top_K,
            "score_threshold": score_threshold,
        }
        if provider is not None:
            result["provider"] = provider
        return result

    async def create_model_config(
        self,
        username: str,
        selected_model: str,
        model_id: str,
        model_name: str,
        model_url: str,
        api_key: str,
        base_used: list,
        system_prompt: str,
        temperature: float,
        max_length: int,
        top_P: float,
        top_K: int,
        score_threshold: int,
        provider: Optional[str] = None,
    ):
        model_config = {
            "username": username,
            "selected_model": selected_model,
            "models": [
                self._build_model_dict(
                    model_id=model_id,
                    model_name=model_name,
                    model_url=model_url,
                    api_key=api_key,
                    base_used=base_used,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_length=max_length,
                    top_P=top_P,
                    top_K=top_K,
                    score_threshold=score_threshold,
                    provider=provider,
                )
            ],
        }

        try:
            await self.db.model_config.insert_one(model_config)
            return {"status": "success", "username": username}
        except DuplicateKeyError:
            logger.error(f"username already exist: username: {username}")
            return {"status": "error", "message": "username already exist"}
        except Exception as e:
            logger.error(f"create config failed: {str(e)}")
            return {"status": "error", "message": f"mongo error: {str(e)}"}

    async def update_selected_model(self, username: str, model_id: str):
        """
        更新用户选定的模型 (selected_model 字段)
        同时验证目标 model_id 是否存在于该用户的 models 数组中
        """
        # System models can be selected without being stored in the models array.
        if model_id.startswith("system_"):
            model_name = model_id[7:]
            from app.rag.provider_client import ProviderClient

            provider = ProviderClient.get_provider_for_model(model_name)
            if not provider:
                return {
                    "status": "error",
                    "message": f"Unknown model: {model_name}",
                }

            provider_config = ProviderClient.PROVIDERS.get(provider, {})
            env_key = provider_config.get("env_key", "")
            if env_key and not os.getenv(env_key):
                return {
                    "status": "error",
                    "message": f"Provider not configured: missing {env_key}",
                }

            if provider == "cliproxyapi":
                live_models, reason = await _fetch_cliproxyapi_live_models()
                if model_name not in live_models:
                    return {
                        "status": "error",
                        "message": f"CLIProxyAPI model not available ({reason})",
                    }

            result = await self.db.model_config.update_one(
                {"username": username}, {"$set": {"selected_model": model_id}}
            )
            if result.matched_count == 0:
                return {"status": "error", "message": "User not found"}
            await cache_service.invalidate_model_config(username)
            return {
                "status": "success",
                "username": username,
                "selected_model": model_id,
            }

        # 验证 model_id 是否存在
        model_exists = await self.db.model_config.find_one(
            {"username": username, "models.model_id": model_id}
        )

        if not model_exists:
            return {
                "status": "error",
                "message": f"Model ID {model_id} not found for user {username}",
            }

        # 更新 selected_model
        result = await self.db.model_config.update_one(
            {"username": username}, {"$set": {"selected_model": model_id}}
        )

        if result.matched_count == 0:
            return {"status": "error", "message": "User not found"}

        await cache_service.invalidate_model_config(username)
        return {"status": "success", "username": username, "selected_model": model_id}

    async def add_model_config(
        self,
        username: str,
        model_id: str,
        model_name: str,
        model_url: str,
        api_key: str,
        base_used: list,
        system_prompt: str,
        temperature: float,
        max_length: int,
        top_P: float,
        top_K: int,
        score_threshold: int,
        provider: Optional[str] = None,
    ):
        # 检查用户是否存在
        user_exists = await self.db.model_config.find_one({"username": username})
        if not user_exists:
            return {"status": "error", "message": "User not found"}

        # 检查 model_id 是否重复
        model_exists = await self.db.model_config.find_one(
            {"username": username, "models.model_id": model_id}
        )
        if model_exists:
            return {"status": "error", "message": "Model ID already exists"}

        # 构建新模型配置
        new_model = self._build_model_dict(
            model_id=model_id,
            model_name=model_name,
            model_url=model_url,
            api_key=api_key,
            base_used=base_used,
            system_prompt=system_prompt,
            temperature=temperature,
            max_length=max_length,
            top_P=top_P,
            top_K=top_K,
            score_threshold=score_threshold,
            provider=provider,
        )

        # 插入到数组
        result = await self.db.model_config.update_one(
            {"username": username}, {"$push": {"models": new_model}}
        )

        if result.modified_count == 1:
            await cache_service.invalidate_model_config(username)
            return {"status": "success", "username": username, "model_id": model_id}
        else:
            return {"status": "error", "message": "Failed to add model"}

    async def delete_model_config(self, username: str, model_id: str):
        # 删除操作
        result = await self.db.model_config.update_one(
            {"username": username}, {"$pull": {"models": {"model_id": model_id}}}
        )

        # 处理结果
        if result.matched_count == 0:
            return {"status": "error", "message": "User not found"}
        elif result.modified_count == 0:
            return {"status": "error", "message": "Model ID not found"}
        else:
            await cache_service.invalidate_model_config(username)
            return {"status": "success", "username": username, "model_id": model_id}

    async def update_model_config(
        self,
        username: str,
        model_id: str,
        model_name: Optional[str] = None,
        model_url: Optional[str] = None,
        api_key: Optional[str] = None,
        base_used: Optional[list] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_length: Optional[int] = None,
        top_P: Optional[float] = None,
        top_K: Optional[int] = None,
        score_threshold: Optional[int] = None,
        provider: Optional[str] = None,
    ):
        # For system models, upsert into the models array
        if model_id.startswith("system_"):
            return await self._upsert_system_model_config(
                username=username,
                model_id=model_id,
                model_name=model_name,
                model_url=model_url,
                api_key=api_key,
                base_used=base_used,
                system_prompt=system_prompt,
                temperature=temperature,
                max_length=max_length,
                top_P=top_P,
                top_K=top_K,
                score_threshold=score_threshold,
                provider=provider,
            )

        # 构建更新字段
        update_fields = {}
        if model_name is not None:
            update_fields["models.$[elem].model_name"] = model_name
        if model_url is not None:
            update_fields["models.$[elem].model_url"] = model_url
        if api_key is not None:
            update_fields["models.$[elem].api_key"] = api_key
        if base_used is not None:
            update_fields["models.$[elem].base_used"] = base_used
        if system_prompt is not None:
            update_fields["models.$[elem].system_prompt"] = system_prompt
        if temperature is not None:
            update_fields["models.$[elem].temperature"] = temperature
        if max_length is not None:
            update_fields["models.$[elem].max_length"] = max_length
        if top_P is not None:
            update_fields["models.$[elem].top_P"] = top_P
        if top_K is not None:
            update_fields["models.$[elem].top_K"] = top_K
        if score_threshold is not None:
            update_fields["models.$[elem].score_threshold"] = score_threshold
        if provider is not None:
            update_fields["models.$[elem].provider"] = provider

        # 执行更新
        try:
            result = await self.db.model_config.update_one(
                {"username": username},
                {"$set": update_fields},
                array_filters=[{"elem.model_id": model_id}],
            )
            if result.matched_count == 0:
                return {"status": "error", "message": "User not found"}
            elif result.modified_count == 0:
                return {"status": "success", "message": "No changes detected"}
            else:
                await cache_service.invalidate_model_config(username)
                return {"status": "success", "username": username, "model_id": model_id}
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _upsert_system_model_config(
        self,
        username: str,
        model_id: str,
        model_name: Optional[str] = None,
        model_url: Optional[str] = None,
        api_key: Optional[str] = None,
        base_used: Optional[list] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_length: Optional[int] = None,
        top_P: Optional[float] = None,
        top_K: Optional[int] = None,
        score_threshold: Optional[int] = None,
        provider: Optional[str] = None,
    ):
        """Upsert system model config - add if not exists, update if exists."""
        try:
            model_exists = await self.db.model_config.find_one(
                {"username": username, "models.model_id": model_id}
            )

            if model_exists:
                update_fields = {}
                if model_name is not None:
                    update_fields["models.$[elem].model_name"] = model_name
                if model_url is not None:
                    update_fields["models.$[elem].model_url"] = model_url
                if api_key is not None:
                    update_fields["models.$[elem].api_key"] = api_key
                if base_used is not None:
                    update_fields["models.$[elem].base_used"] = base_used
                if system_prompt is not None:
                    update_fields["models.$[elem].system_prompt"] = system_prompt
                if temperature is not None:
                    update_fields["models.$[elem].temperature"] = temperature
                if max_length is not None:
                    update_fields["models.$[elem].max_length"] = max_length
                if top_P is not None:
                    update_fields["models.$[elem].top_P"] = top_P
                if top_K is not None:
                    update_fields["models.$[elem].top_K"] = top_K
                if score_threshold is not None:
                    update_fields["models.$[elem].score_threshold"] = score_threshold
                if provider is not None:
                    update_fields["models.$[elem].provider"] = provider

                if update_fields:
                    await self.db.model_config.update_one(
                        {"username": username},
                        {"$set": update_fields},
                        array_filters=[{"elem.model_id": model_id}],
                    )
            else:
                cliproxyapi_url = os.getenv("CLIPROXYAPI_BASE_URL", "")
                cliproxyapi_key = os.getenv("CLIPROXYAPI_API_KEY", "")
                actual_model_name = (
                    model_id[7:] if model_id.startswith("system_") else model_id
                )

                new_model = self._build_model_dict(
                    model_id=model_id,
                    model_name=model_name if model_name else actual_model_name,
                    model_url=model_url if model_url else cliproxyapi_url,
                    api_key=api_key if api_key else cliproxyapi_key,
                    base_used=base_used if base_used is not None else [],
                    system_prompt=system_prompt if system_prompt is not None else "",
                    temperature=temperature if temperature is not None else -1,
                    max_length=max_length if max_length is not None else -1,
                    top_P=top_P if top_P is not None else -1,
                    top_K=top_K if top_K is not None else -1,
                    score_threshold=score_threshold
                    if score_threshold is not None
                    else -1,
                    provider=provider,
                )
                await self.db.model_config.update_one(
                    {"username": username}, {"$push": {"models": new_model}}
                )

            await cache_service.invalidate_model_config(username)
            return {"status": "success", "username": username, "model_id": model_id}
        except Exception as e:
            logger.error(f"Upsert system model failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _sanitize_system_model(self, model: dict) -> dict:
        """Sanitize system models coming from MongoDB to ensure they use environment-based routing."""
        model_id = str(model.get("model_id", ""))
        if not model_id.startswith("system_"):
            return model

        model_name = str(model.get("model_name", ""))
        if not model_name and len(model_id) > 7:
            model_name = model_id[7:]

        from app.rag.provider_client import ProviderClient

        # System models MUST use env keys and empty model_url for deterministic routing.
        model["model_url"] = ""
        model["api_key"] = None
        model["provider"] = ProviderClient.get_provider_for_model(model_name)
        return model

    async def get_selected_model_config(self, username: str):
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            return {"status": "error", "message": "User not found"}

        selected_id = str(user_config.get("selected_model") or "")
        if not selected_id:
            return {"status": "error", "message": "No selected model"}

        for model in user_config.get("models", []):
            if model.get("model_id") == selected_id:
                sanitized = self._sanitize_system_model(model)
                return {"status": "success", "select_model_config": sanitized}

        # System models (not necessarily persisted) can be synthesized.
        if selected_id.startswith("system_"):
            model_name = selected_id[7:]
            from app.rag.provider_client import ProviderClient

            provider = ProviderClient.get_provider_for_model(model_name)
            if provider == "cliproxyapi":
                live_models, reason = await _fetch_cliproxyapi_live_models()
                if model_name not in live_models:
                    return {
                        "status": "error",
                        "message": f"CLIProxyAPI model not available ({reason})",
                    }

            return {
                "status": "success",
                "select_model_config": {
                    "model_id": selected_id,
                    "model_name": model_name,
                    "model_url": "",
                    "api_key": None,
                    "base_used": [],
                    "system_prompt": "",
                    "temperature": -1,
                    "max_length": -1,
                    "top_P": -1,
                    "top_K": -1,
                    "score_threshold": -1,
                    "provider": provider,
                },
            }

        return {"status": "error", "message": "Selected model not found"}

    async def get_all_models_config(self, username: str):
        # 直接返回 models 数组
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            return {"status": "error", "message": "User not found"}

        user_models = user_config.get("models", [])
        persisted_model_ids = {m.get("model_id") for m in user_models}

        # If CLIProxyAPI is configured but returns empty /models, hide any stale
        # stored system_* proxy models to avoid presenting broken choices.
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            from app.rag.provider_client import ProviderClient

            live_models, _reason = await _fetch_cliproxyapi_live_models()
            live_set = set(live_models)

            filtered: List[dict] = []
            for m in user_models:
                model_id = str(m.get("model_id", ""))
                model_name = str(m.get("model_name", ""))
                if model_id.startswith("system_"):
                    provider = ProviderClient.get_provider_for_model(model_name)
                    if provider == "cliproxyapi" and model_name not in live_set:
                        continue
                    m = self._sanitize_system_model(m)
                filtered.append(m)
            user_models = filtered
            persisted_model_ids = {m.get("model_id") for m in user_models}
        else:
            # Even if CLIPROXYAPI_BASE_URL is not set, sanitize any existing system models
            user_models = [self._sanitize_system_model(m) for m in user_models]
            persisted_model_ids = {m.get("model_id") for m in user_models}

        system_models: List[dict] = []

        # Provider-backed system models (no keys sent to frontend; use env at runtime)
        if os.getenv("DEEPSEEK_API_KEY"):
            system_models.extend(
                [
                    {
                        "model_id": "system_deepseek-chat",
                        "model_name": "deepseek-chat",
                        "model_url": "",
                        "api_key": None,
                        "base_used": [],
                        "system_prompt": "",
                        "temperature": -1,
                        "max_length": -1,
                        "top_P": -1,
                        "top_K": -1,
                        "score_threshold": -1,
                        "provider": "deepseek",
                    },
                    {
                        "model_id": "system_deepseek-reasoner",
                        "model_name": "deepseek-reasoner",
                        "model_url": "",
                        "api_key": None,
                        "base_used": [],
                        "system_prompt": "",
                        "temperature": -1,
                        "max_length": -1,
                        "top_P": -1,
                        "top_K": -1,
                        "score_threshold": -1,
                        "provider": "deepseek",
                    },
                ]
            )

        if os.getenv("ZAI_API_KEY"):
            system_models.append(
                {
                    "model_id": "system_glm-4.7-flash",
                    "model_name": "glm-4.7-flash",
                    "model_url": "",
                    "api_key": None,
                    "base_used": [],
                    "system_prompt": "",
                    "temperature": -1,
                    "max_length": -1,
                    "top_P": -1,
                    "top_K": -1,
                    "score_threshold": -1,
                    "provider": "zai",
                }
            )

        if os.getenv("MINIMAX_API_KEY"):
            system_models.append(
                {
                    "model_id": "system_MiniMax-M2.1",
                    "model_name": "MiniMax-M2.1",
                    "model_url": "",
                    "api_key": None,
                    "base_used": [],
                    "system_prompt": "",
                    "temperature": -1,
                    "max_length": -1,
                    "top_P": -1,
                    "top_K": -1,
                    "score_threshold": -1,
                    "provider": "minimax",
                }
            )

        # Ollama Cloud models (open-source LLMs)
        if os.getenv("OLLAMA_CLOUD_API_KEY"):
            ollama_models = [
                "llama3.3",
                "llama3.2",
                "llama3.1",
                "qwen2.5",
                "qwen2.5-coder",
                "qwq",
                "mistral",
                "mixtral",
                "deepseek-r1",
                "deepseek-v3",
                "phi4",
                "gemma2",
                "codellama",
                "llama3.2-vision",
                "llava",
            ]
            for model_name in ollama_models:
                system_models.append(
                    {
                        "model_id": f"system_{model_name}",
                        "model_name": model_name,
                        "model_url": "",
                        "api_key": None,
                        "base_used": [],
                        "system_prompt": "",
                        "temperature": -1,
                        "max_length": -1,
                        "top_P": -1,
                        "top_K": -1,
                        "score_threshold": -1,
                        "provider": "ollama-cloud",
                    }
                )

        # CLIProxyAPI models: try live fetch, fallback to static list.
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            live_models, _reason = await _fetch_cliproxyapi_live_models()
            if not live_models:
                # Fallback: use static model list from providers.yaml
                live_models = [
                    # Claude (Anthropic via Antigravity)
                    "claude-opus-4-5-thinking",
                    "claude-sonnet-4-5-thinking",
                    "claude-sonnet-4-5",
                    "claude-sonnet-4-20250514",
                    "claude-3.5-sonnet",
                    # Gemini (Google via Antigravity)
                    "gemini-2.5-pro",
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-3-pro-preview",
                    "gemini-3-flash",
                ]
            for model_name in live_models:
                system_models.append(
                    {
                        "model_id": f"system_{model_name}",
                        "model_name": model_name,
                        "model_url": "",
                        "api_key": None,
                        "base_used": [],
                        "system_prompt": "",
                        "temperature": -1,
                        "max_length": -1,
                        "top_P": -1,
                        "top_K": -1,
                        "score_threshold": -1,
                        "provider": "cliproxyapi",
                    }
                )

        for sys_model in system_models:
            if sys_model["model_id"] not in persisted_model_ids:
                user_models.append(sys_model)

        selected_model = str(user_config.get("selected_model") or "")
        if selected_model:
            known_ids = {m.get("model_id") for m in user_models}
            if selected_model not in known_ids:
                selected_model = ""

        # Stabilize: if current selection is a cliproxyapi system model but proxy is empty,
        # fall back to a deterministic provider-backed system model.
        if selected_model.startswith("system_"):
            selected_name = selected_model[7:]
            from app.rag.provider_client import ProviderClient

            provider = ProviderClient.get_provider_for_model(selected_name)
            if provider == "cliproxyapi":
                live_models, _reason = await _fetch_cliproxyapi_live_models()
                if selected_name not in live_models:
                    # Prefer DeepSeek, then Z.ai, then MiniMax.
                    fallback = ""
                    if os.getenv("DEEPSEEK_API_KEY"):
                        fallback = "system_deepseek-chat"
                    elif os.getenv("ZAI_API_KEY"):
                        fallback = "system_glm-4.7-flash"
                    elif os.getenv("MINIMAX_API_KEY"):
                        fallback = "system_MiniMax-M2.1"
                    if fallback:
                        selected_model = fallback

        if not selected_model and user_models:
            selected_model = cast(str, user_models[0].get("model_id", ""))

        if selected_model and selected_model != user_config.get("selected_model"):
            await self.db.model_config.update_one(
                {"username": username}, {"$set": {"selected_model": selected_model}}
            )
            await cache_service.invalidate_model_config(username)

        return {
            "status": "success",
            "models": user_models,
            "selected_model": selected_model,
        }

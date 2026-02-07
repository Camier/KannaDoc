import os
from typing import Optional, Dict, Any, List, cast

from app.core.logging import logger
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from app.db.cache import cache_service


class ModelConfigRepository(BaseRepository):
    async def _ensure_user_model_config(self, username: str) -> None:
        """Ensure a model_config document exists for username.

        This repo runs with auth bypassed (default username). In fresh deployments,
        the config document may not exist yet; we auto-create it so provider-backed
        system models can be listed and selected without manual bootstrap.
        """

        try:
            await self.db.model_config.update_one(
                {"username": username},
                {
                    "$setOnInsert": {
                        "username": username,
                        "selected_model": "",
                        "models": [],
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            logger.error("ensure model_config failed: %s", exc)

    @staticmethod
    def _system_model_generation_defaults(
        *,
        model_name: str,
        provider: Optional[str],
    ) -> dict[str, object]:
        from app.rag.provider_registry import ProviderRegistry

        return ProviderRegistry.get_generation_defaults(provider, model_name)

    def _build_model_dict(
        self,
        model_id: str,
        model_name: str,
        model_url: str,
        api_key: Optional[str],
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
        api_key: Optional[str],
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
        await self._ensure_user_model_config(username)

        # System models can be selected without being stored in the models array.
        if model_id.startswith("system_"):
            model_name = model_id[7:]
            from app.rag.provider_registry import ProviderRegistry

            provider = ProviderRegistry.get_provider_for_model(model_name)
            if not provider:
                return {
                    "status": "error",
                    "message": f"Unknown model: {model_name}",
                }

            provider_config = ProviderRegistry.get_provider_config(provider)
            env_key = provider_config.env_key
            if env_key and not os.getenv(env_key):
                return {
                    "status": "error",
                    "message": f"Provider not configured: missing {env_key}",
                }

            if provider == "cliproxyapi":
                live_models, reason = await ProviderRegistry.fetch_cliproxyapi_models()
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
        api_key: Optional[str],
        base_used: list,
        system_prompt: str,
        temperature: float,
        max_length: int,
        top_P: float,
        top_K: int,
        score_threshold: int,
        provider: Optional[str] = None,
    ):
        # Ensure the user doc exists (fresh deployments may not have it yet)
        await self._ensure_user_model_config(username)

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
        await self._ensure_user_model_config(username)
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

    def _build_update_fields(self, **kwargs) -> dict:
        """Build MongoDB update dict from non-None kwargs."""
        return {f"models.$[elem].{k}": v for k, v in kwargs.items() if v is not None}

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
        await self._ensure_user_model_config(username)

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
        update_fields = self._build_update_fields(
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
                update_fields = self._build_update_fields(
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

        from app.rag.provider_registry import ProviderRegistry

        # System models MUST use env keys and empty model_url for deterministic routing.
        model["model_url"] = ""
        model["api_key"] = None
        provider = ProviderRegistry.get_provider_for_model(model_name)
        model["provider"] = provider

        # Apply tuned defaults only when the value is the -1 sentinel.
        defaults = self._system_model_generation_defaults(
            model_name=model_name,
            provider=provider,
        )
        if model.get("temperature", -1) == -1:
            model["temperature"] = defaults["temperature"]
        if model.get("max_length", -1) == -1:
            model["max_length"] = defaults["max_length"]
        # Keep top_P omitted by default unless explicitly set.
        if model.get("top_P", -1) == -1 and defaults.get("top_P", -1) != -1:
            model["top_P"] = defaults["top_P"]
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
            from app.rag.provider_registry import ProviderRegistry

            provider = ProviderRegistry.get_provider_for_model(model_name)
            if provider == "cliproxyapi":
                live_models, reason = await ProviderRegistry.fetch_cliproxyapi_models()
                if model_name not in live_models:
                    return {
                        "status": "error",
                        "message": f"CLIProxyAPI model not available ({reason})",
                    }

            defaults = self._system_model_generation_defaults(
                model_name=model_name,
                provider=provider,
            )
            return {
                "status": "success",
                "select_model_config": {
                    "model_id": selected_id,
                    "model_name": model_name,
                    "model_url": "",
                    "api_key": None,
                    "base_used": [],
                    "system_prompt": "",
                    "temperature": defaults["temperature"],
                    "max_length": defaults["max_length"],
                    "top_P": defaults["top_P"],
                    "top_K": -1,
                    "score_threshold": -1,
                    "provider": provider,
                },
            }

        return {"status": "error", "message": "Selected model not found"}

    async def _prune_stale_system_models(
        self, user_models: List[dict], persisted_model_ids: set
    ) -> tuple[List[dict], set]:
        # If CLIProxyAPI is configured but returns empty /models, hide any stale
        # stored system_* proxy models to avoid presenting broken choices.
        if os.getenv("CLIPROXYAPI_BASE_URL"):
            from app.rag.provider_registry import ProviderRegistry

            live_models, _reason = await ProviderRegistry.fetch_cliproxyapi_models()
            live_set = set(live_models)

            filtered: List[dict] = []
            for m in user_models:
                model_id = str(m.get("model_id", ""))
                model_name = str(m.get("model_name", ""))
                if model_id.startswith("system_"):
                    provider = ProviderRegistry.get_provider_for_model(model_name)
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

        from app.rag.provider_registry import ProviderRegistry

        ProviderRegistry.load()

        # Stale system_* pruning — CLIProxyAPI is already pruned above via live fetch.
        valid_system_ids: set[str] = set()
        for pid in ProviderRegistry.get_all_providers():
            if pid == "cliproxyapi":
                continue
            pcfg = ProviderRegistry.get_provider_config(pid)
            for mn in pcfg.models:
                valid_system_ids.add(f"system_{mn}")

        pruned: List[dict] = []
        for m in user_models:
            mid = str(m.get("model_id", ""))
            if mid.startswith("system_") and m.get("provider") != "cliproxyapi":
                if mid not in valid_system_ids:
                    logger.debug("Pruning stale system model: %s", mid)
                    continue
            pruned.append(m)

        user_models = pruned
        persisted_model_ids = {m.get("model_id") for m in user_models}

        return user_models, persisted_model_ids

    async def _synthesize_system_models(self, persisted_model_ids: set) -> List[dict]:
        from app.rag.provider_registry import ProviderRegistry

        system_models: List[dict] = []

        for provider_id in ProviderRegistry.get_all_providers():
            config = ProviderRegistry.get_provider_config(provider_id)

            if provider_id == "cliproxyapi":
                if os.getenv("CLIPROXYAPI_BASE_URL"):
                    (
                        live_models,
                        _reason,
                    ) = await ProviderRegistry.fetch_cliproxyapi_models()
                    model_list = live_models if live_models else list(config.models)
                else:
                    continue
            else:
                if not config.env_key or not os.getenv(config.env_key):
                    continue
                model_list = list(config.models)

            for model_name in model_list:
                defaults = self._system_model_generation_defaults(
                    model_name=model_name,
                    provider=provider_id,
                )
                system_models.append(
                    {
                        "model_id": f"system_{model_name}",
                        "model_name": model_name,
                        "model_url": "",
                        "api_key": None,
                        "base_used": [],
                        "system_prompt": "",
                        "temperature": defaults["temperature"],
                        "max_length": defaults["max_length"],
                        "top_P": defaults["top_P"],
                        "top_K": -1,
                        "score_threshold": -1,
                        "provider": provider_id,
                    }
                )
        return system_models

    async def _resolve_selected_model(
        self, user_models: List[dict], user_config: dict, username: str
    ) -> str:
        selected_model = str(user_config.get("selected_model") or "")
        if selected_model:
            known_ids = {m.get("model_id") for m in user_models}
            if selected_model not in known_ids:
                selected_model = ""

        # Stabilize: if current selection is a cliproxyapi system model but proxy is empty,
        # fall back to a deterministic provider-backed system model.
        if selected_model.startswith("system_"):
            selected_name = selected_model[7:]
            from app.rag.provider_registry import ProviderRegistry

            provider = ProviderRegistry.get_provider_for_model(selected_name)
            if provider == "cliproxyapi":
                live_models, _reason = await ProviderRegistry.fetch_cliproxyapi_models()
                if selected_name not in live_models:
                    fallback = ""
                    for pid in ProviderRegistry.get_all_providers():
                        if pid == "cliproxyapi":
                            continue
                        pcfg = ProviderRegistry.get_provider_config(pid)
                        if pcfg.env_key and os.getenv(pcfg.env_key) and pcfg.models:
                            fallback = f"system_{pcfg.models[0]}"
                            break
                    if fallback:
                        selected_model = fallback

        if not selected_model and user_models:
            selected_model = cast(str, user_models[0].get("model_id", ""))

        if selected_model and selected_model != user_config.get("selected_model"):
            await self.db.model_config.update_one(
                {"username": username}, {"$set": {"selected_model": selected_model}}
            )
            await cache_service.invalidate_model_config(username)

        return selected_model

    async def get_all_models_config(self, username: str):
        # 直接返回 models 数组
        await self._ensure_user_model_config(username)
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            # Should not happen after upsert, but keep a safe fallback.
            user_config = {"username": username, "selected_model": "", "models": []}

        user_models = user_config.get("models", [])
        persisted_model_ids = {m.get("model_id") for m in user_models}

        user_models, persisted_model_ids = await self._prune_stale_system_models(
            user_models, persisted_model_ids
        )

        new_system_models = await self._synthesize_system_models(persisted_model_ids)
        for sys_model in new_system_models:
            if sys_model["model_id"] not in persisted_model_ids:
                user_models.append(sys_model)

        selected_model = await self._resolve_selected_model(
            user_models, user_config, username
        )

        return {
            "status": "success",
            "models": user_models,
            "selected_model": selected_model,
        }

import os
from typing import Optional, Dict, Any, List
from app.core.logging import logger
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from app.db.cache import cache_service


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
        # Check if it's a CLIProxyAPI system model (not stored in DB, but valid)
        if model_id.startswith("system_"):
            cliproxyapi_url = os.getenv("CLIPROXYAPI_BASE_URL")
            if cliproxyapi_url:
                model_name = model_id[7:]
                from app.rag.provider_client import ProviderClient

                cliproxyapi_models = ProviderClient.PROVIDERS.get(
                    "cliproxyapi", {}
                ).get("models", [])
                if model_name in cliproxyapi_models:
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

    async def get_selected_model_config(self, username: str):
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            return {"status": "error", "message": "User not found"}

        selected_id = user_config.get("selected_model")
        if not selected_id:
            return {"status": "error", "message": "No selected model"}

        for model in user_config.get("models", []):
            if model.get("model_id") == selected_id:
                return {"status": "success", "select_model_config": model}

        if selected_id.startswith("system_"):
            cliproxyapi_url = os.getenv("CLIPROXYAPI_BASE_URL")
            if cliproxyapi_url:
                model_name = selected_id[7:]
                from app.rag.provider_client import ProviderClient

                cliproxyapi_models = ProviderClient.PROVIDERS.get(
                    "cliproxyapi", {}
                ).get("models", [])
                if model_name in cliproxyapi_models:
                    return {
                        "status": "success",
                        "select_model_config": {
                            "model_id": selected_id,
                            "model_name": model_name,
                            "model_url": cliproxyapi_url,
                            "api_key": os.getenv("CLIPROXYAPI_API_KEY"),
                            "base_used": [],
                            "system_prompt": "",
                            "temperature": -1,
                            "max_length": -1,
                            "top_P": -1,
                            "top_K": -1,
                            "score_threshold": -1,
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

        cliproxyapi_url = os.getenv("CLIPROXYAPI_BASE_URL")
        if cliproxyapi_url:
            from app.rag.provider_client import ProviderClient

            cliproxyapi_models = ProviderClient.PROVIDERS.get("cliproxyapi", {}).get(
                "models", []
            )
            for model_name in cliproxyapi_models:
                system_model_id = f"system_{model_name}"
                if system_model_id not in persisted_model_ids:
                    system_model = {
                        "model_id": system_model_id,
                        "model_name": model_name,
                        "model_url": cliproxyapi_url,
                        "api_key": os.getenv("CLIPROXYAPI_API_KEY"),
                        "base_used": [],
                        "system_prompt": "",
                        "temperature": -1,
                        "max_length": -1,
                        "top_P": -1,
                        "top_K": -1,
                        "score_threshold": -1,
                    }
                    user_models.append(system_model)

        return {
            "status": "success",
            "models": user_models,
            "selected_model": user_config.get("selected_model", ""),
        }

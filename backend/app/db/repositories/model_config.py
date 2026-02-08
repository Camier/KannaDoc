from typing import Optional, List

from app.core.logging import logger
from pymongo.errors import DuplicateKeyError
from .base import BaseRepository
from app.db.cache import cache_service


class ModelConfigRepository(BaseRepository):
    async def _ensure_user_model_config(self, username: str) -> None:
        """Ensure a model_config document exists for username."""
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
    ) -> dict:
        return {
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
        await self._ensure_user_model_config(username)

        model_exists = await self.db.model_config.find_one(
            {"username": username, "models.model_id": model_id}
        )

        if not model_exists:
            return {
                "status": "error",
                "message": f"Model ID {model_id} not found for user {username}",
            }

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
    ):
        await self._ensure_user_model_config(username)

        model_exists = await self.db.model_config.find_one(
            {"username": username, "models.model_id": model_id}
        )
        if model_exists:
            return {"status": "error", "message": "Model ID already exists"}

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
        )

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
        result = await self.db.model_config.update_one(
            {"username": username}, {"$pull": {"models": {"model_id": model_id}}}
        )

        if result.matched_count == 0:
            return {"status": "error", "message": "User not found"}
        elif result.modified_count == 0:
            return {"status": "error", "message": "Model ID not found"}
        else:
            await cache_service.invalidate_model_config(username)
            return {"status": "success", "username": username, "model_id": model_id}

    def _build_update_fields(self, **kwargs) -> dict:
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
    ):
        await self._ensure_user_model_config(username)

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
        )

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

    async def get_selected_model_config(self, username: str):
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            return {"status": "error", "message": "User not found"}

        selected_id = str(user_config.get("selected_model") or "")
        if not selected_id:
            return {"status": "error", "message": "No selected model"}

        for model in user_config.get("models", []):
            if model.get("model_id") == selected_id:
                return {"status": "success", "select_model_config": model}

        return {"status": "error", "message": "Selected model not found"}

    async def get_all_models_config(self, username: str):
        await self._ensure_user_model_config(username)
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            user_config = {"username": username, "selected_model": "", "models": []}

        user_models = user_config.get("models", [])
        selected_model = str(user_config.get("selected_model") or "")

        if selected_model:
            known_ids = {m.get("model_id") for m in user_models}
            if selected_model not in known_ids:
                selected_model = ""

        if not selected_model and user_models:
            selected_model = str(user_models[0].get("model_id", ""))
            await self.db.model_config.update_one(
                {"username": username}, {"$set": {"selected_model": selected_model}}
            )
            await cache_service.invalidate_model_config(username)

        return {
            "status": "success",
            "models": user_models,
            "selected_model": selected_model,
        }

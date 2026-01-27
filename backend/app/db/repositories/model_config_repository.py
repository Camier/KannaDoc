"""
Model Configuration Repository

Handles all operations related to user model configurations.
Lines 109-358 from original mongo.py
"""

from typing import Dict, Any, List, Optional
from pymongo.errors import DuplicateKeyError
from app.core.logging import logger
from app.db.repositories.base_repository import BaseRepository
from app.db.cache import cache_service


class ModelConfigRepository(BaseRepository):
    """Repository for model configuration operations."""

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
    ) -> dict:
        """Build a model configuration dictionary."""
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
        api_key: str,
        base_used: list,
        system_prompt: str,
        temperature: float,
        max_length: int,
        top_P: float,
        top_K: int,
        score_threshold: int,
    ):
        """Create a new model configuration for a user."""
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
            await cache_service.invalidate_model_config(username)
            await cache_service.invalidate_model_config(f"{username}:all")
            return {"status": "success", "username": username}
            logger.error(f"username already exist: username: {username}")
            return {"status": "error", "message": "username already exist"}
        except Exception as e:
            logger.error(f"create config failed: {str(e)}")
            return {"status": "error", "message": f"mongo error: {str(e)}"}

    async def update_selected_model(self, username: str, model_id: str):
        """
        Update the selected model for a user.
        Validates that the target model_id exists in the user's models array.
        """
        # Verify model_id exists
        model_exists = await self.db.model_config.find_one(
            {"username": username, "models.model_id": model_id}
        )

        if not model_exists:
            return {
                "status": "error",
                "message": f"Model ID {model_id} not found for user {username}",
            }

        # Update selected_model
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
    ):
        """Add a new model configuration to a user's models array."""
        # Check if user exists
        user_exists = await self.db.model_config.find_one({"username": username})
        if not user_exists:
            return {"status": "error", "message": "User not found"}

        # Check if model_id already exists
        model_exists = await self.db.model_config.find_one(
            {"username": username, "models.model_id": model_id}
        )
        if model_exists:
            return {"status": "error", "message": "Model ID already exists"}

        # Build new model configuration
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

        # Insert into array
        result = await self.db.model_config.update_one(
            {"username": username}, {"$push": {"models": new_model}}
        )

        if result.modified_count == 1:
            await cache_service.invalidate_model_config(username)
            await cache_service.invalidate_model_config(f"{username}:all")
            return {"status": "success", "username": username, "model_id": model_id}
        else:
            return {"status": "error", "message": "Failed to add model"}

    async def delete_model_config(self, username: str, model_id: str):
        """Delete a model configuration from a user's models array."""
        result = await self.db.model_config.update_one(
            {"username": username}, {"$pull": {"models": {"model_id": model_id}}}
        )

        if result.matched_count == 0:
            return {"status": "error", "message": "User not found"}
        elif result.modified_count == 0:
            return {"status": "error", "message": "Model ID not found"}
        else:
            await cache_service.invalidate_model_config(username)
            await cache_service.invalidate_model_config(f"{username}:all")
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
    ):
        """Update fields in a specific model configuration."""
        # Build update fields
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

        # Execute update
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
                await cache_service.invalidate_model_config(f"{username}:all")
                return {"status": "success", "username": username, "model_id": model_id}
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
        return {"status": "error", "message": str(e)}

    async def get_selected_model_config(self, username: str):
        """Get the selected model configuration for a user with caching."""
        # Try cache first
        cached = await cache_service.get_model_config(username)
        if cached:
            logger.debug(f"Cache hit: model_config for {username}")
            return {"status": "success", "select_model_config": cached.get("select_model_config")}

        # Get user config
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            return {"status": "error", "message": "User not found"}

        # Extract selected model_id
        selected_id = user_config.get("selected_model")
        if not selected_id:
            return {"status": "error", "message": "No selected model"}

        # Use aggregation to find selected model (replaces O(n) array search)
        pipeline = [
            {"$match": {"username": username}},
            {"$unwind": "$models"},
            {"$match": {"models.model_id": selected_id}},
            {"$replaceRoot": {"newRoot": "$models"}},
        ]

        cursor = self.db.model_config.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if result:
            response = {"status": "success", "select_model_config": result[0]}
            await cache_service.set_model_config(username, response)
            return response

        return {"status": "error", "message": "Selected model not found"}

    async def get_all_models_config(self, username: str):
        """Get all model configurations for a user with caching."""
        # Try cache first
        cached = await cache_service.get_model_config(f"{username}:all")
        if cached:
            logger.debug(f"Cache hit: all model_configs for {username}")
            return cached

        # Return models array directly
        user_config = await self.db.model_config.find_one({"username": username})
        if not user_config:
            return {"status": "error", "message": "User not found"}

        response = {
            "status": "success",
            "models": user_config.get("models", []),
            "selected_model": user_config.get("selected_model", ""),
        }
        await cache_service.set_model_config(f"{username}:all", response)
        return response

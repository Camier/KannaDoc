import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query  # type: ignore[reportMissingImports]
from app.models.model_config import (
    ModelCreate,
    ModelUpdate,
    SelectedModelResponse,
    UpdateSelectedModelRequest,
)
from app.core.config import settings
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.rag.provider_registry import ProviderRegistry

router = APIRouter()


@router.get("/cliproxyapi-models")
async def get_cliproxyapi_models():
    """获取 CLIProxyAPI 默认模型列表 (Public)"""
    models = ProviderRegistry.get_cliproxyapi_models_with_defaults()
    return models


@router.get("/available-models")
async def get_available_models():
    """Get provider-backed models with configuration hints."""
    ProviderRegistry.load()
    providers = []
    for provider_id in ProviderRegistry.get_all_providers():
        config = ProviderRegistry.get_provider_config(provider_id)
        env_key_name = config.env_key
        env_key_present = bool(os.getenv(env_key_name)) if env_key_name else False
        base_url = (
            os.getenv("CLIPROXYAPI_BASE_URL", "")
            if provider_id == "cliproxyapi"
            else config.base_url
        )
        models = list(config.models)
        is_configured = env_key_present
        model_url_hint = (
            "leave empty; uses CLIPROXYAPI_BASE_URL"
            if provider_id == "cliproxyapi"
            else "leave empty; uses provider base_url"
        )
        cliproxy_reason = None

        if provider_id == "cliproxyapi":
            cliproxy_models, reason = await ProviderRegistry.fetch_cliproxyapi_models()
            ok = reason == "ok"
            cliproxy_reason = reason
            if ok:
                models = cliproxy_models
            else:
                models = []
                is_configured = False

        provider_data = {
            "provider_id": provider_id,
            "models": models,
            "base_url": base_url,
            "env_key": env_key_name,
            "requires_env_key": bool(env_key_name),
            "is_configured": is_configured,
            "model_url_hint": model_url_hint,
        }
        if cliproxy_reason:
            provider_data["cliproxy_reason"] = cliproxy_reason

        providers.append(provider_data)

    return {"providers": providers}


@router.get("/resolve-provider")
async def resolve_provider(model: str = Query(..., min_length=1)):
    """Resolve provider details for a given model name."""
    provider_id = ProviderRegistry.get_provider_for_model(model)
    if not provider_id:
        return {
            "model": model,
            "provider_id": None,
            "base_url": "",
            "env_key_name": None,
            "is_env_key_present": False,
            "reason": "unknown_model",
        }

    config = ProviderRegistry.get_provider_config(provider_id)
    env_key_name = config.env_key
    is_env_key_present = bool(os.getenv(env_key_name)) if env_key_name else False
    base_url = (
        os.getenv("CLIPROXYAPI_BASE_URL", "")
        if provider_id == "cliproxyapi"
        else config.base_url
    )

    cliproxy_reason = None

    if not is_env_key_present:
        reason = "missing_env_key"
    elif provider_id == "cliproxyapi" and not base_url:
        reason = "missing_base_url"
    elif provider_id == "cliproxyapi":
        _models, cliproxy_reason = await ProviderRegistry.fetch_cliproxyapi_models()
        reason = "ok" if cliproxy_reason == "ok" else "cliproxy_no_models"
    else:
        reason = "ok"

    payload = {
        "model": model,
        "provider_id": provider_id,
        "base_url": base_url,
        "env_key_name": env_key_name,
        "is_env_key_present": is_env_key_present,
        "reason": reason,
    }
    if cliproxy_reason:
        payload["cliproxy_reason"] = cliproxy_reason
    return payload


@router.post("/", status_code=201)
async def add_model_config(
    model_data: ModelCreate,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """添加新的模型配置"""
    username = settings.default_username
    model_id = username + "_" + str(uuid.uuid4())
    result = await repo_manager.model_config.add_model_config(
        username=username, model_id=model_id, **model_data.model_dump()
    )

    if result["status"] == "error":
        if "already exists" in result["message"]:
            raise HTTPException(status_code=409, detail=result["message"])
        elif "User not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    return {"message": "Model added successfully", "model_id": result["model_id"]}


@router.delete("/{model_id}")
async def delete_model_config(
    model_id: str,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """删除指定模型配置"""
    username = settings.default_username
    result = await repo_manager.model_config.delete_model_config(username, model_id)

    if result["status"] == "error":
        if "User not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        elif "Model ID not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])

    return {"message": "Model deleted successfully"}


@router.patch("/{model_id}")
async def update_model_config(
    model_id: str,
    update_data: ModelUpdate,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """更新模型配置（部分更新）"""
    username = settings.default_username
    result = await repo_manager.model_config.update_model_config(
        username=username,
        model_id=model_id,
        **update_data.model_dump(exclude_unset=True),
    )
    await repo_manager.model_config.update_selected_model(
        username=username, model_id=model_id
    )
    if result["status"] == "error":
        if "User not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    return {"message": "Model updated successfully"}


@router.get("/selected", response_model=SelectedModelResponse)
async def get_selected_model(
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """获取用户选定的模型配置"""
    username = settings.default_username
    result = await repo_manager.model_config.get_selected_model_config(username)

    if result["status"] == "error":
        if "User not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        elif "No selected model" in result["message"]:
            return {"status": "error", "message": result["message"]}

    return result


@router.get("/all", response_model=dict)
async def get_all_models(
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """获取用户所有模型配置"""
    username = settings.default_username
    result = await repo_manager.model_config.get_all_models_config(username)

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@router.put("/select-model", status_code=200)
async def update_selected_model(
    request: UpdateSelectedModelRequest,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """更新用户选定的模型"""
    username = settings.default_username
    result = await repo_manager.model_config.update_selected_model(
        username=username, model_id=request.model_id
    )

    if result["status"] == "error":
        if "User not found" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        elif "not found" in result["message"]:
            raise HTTPException(status_code=400, detail=result["message"])

    return {
        "message": "Selected model updated successfully",
        "selected_model": result["selected_model"],
    }

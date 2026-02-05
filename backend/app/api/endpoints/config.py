import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.models.model_config import (
    ModelCreate,
    ModelUpdate,
    SelectedModelResponse,
    UpdateSelectedModelRequest,
)
from app.db.repositories.repository_manager import (
    RepositoryManager,
    get_repository_manager,
)
from app.rag.provider_client import ProviderClient

router = APIRouter()


@router.get("/cliproxyapi-models")
async def get_cliproxyapi_models():
    """获取 CLIProxyAPI 默认模型列表 (Public)"""
    models = ProviderClient.get_cliproxyapi_models_with_defaults()
    return models


@router.post("/", status_code=201)
async def add_model_config(
    model_data: ModelCreate,
    repo_manager: RepositoryManager = Depends(get_repository_manager),
):
    """添加新的模型配置"""
    username = "miko"  # Temporary hardcoded username
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
    username = "miko"  # Temporary hardcoded username
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
    username = "miko"  # Temporary hardcoded username
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
    username = "miko"  # Temporary hardcoded username
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
    username = "miko"  # Temporary hardcoded username
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
    username = "miko"  # Temporary hardcoded username
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

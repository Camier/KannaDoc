from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter()


# 创建新会话
@router.get("/check", response_model=dict)
async def create_conversation():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "UP", "details": "All systems operational"},
    )

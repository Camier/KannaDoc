# Pydantic 模型，用于输入数据验证
from typing import List
from pydantic import BaseModel
from app.models.shared import TurnOutput


class ChatflowCreate(BaseModel):
    chatflow_id: str
    username: str
    chatflow_name: str
    workflow_id:str


class ChatflowRenameInput(BaseModel):
    chatflow_id: str
    chatflow_new_name: str


class ChatflowOutput(BaseModel):
    chatflow_id: str
    chatflow_name: str
    username: str
    turns: List[TurnOutput]
    created_at: str
    last_modify_at: str


class ChatflowSummary(BaseModel):
    chatflow_id: str
    created_at: str
    chatflow_name: str
    is_read: bool
    last_modify_at: str
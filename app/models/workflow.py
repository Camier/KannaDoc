# Pydantic 模型，用于输入数据验证
from typing import Any, Dict, List
from pydantic import BaseModel


class TestFunctionCode(BaseModel):
    username: str
    node_id: str
    code: str
    name: str
    pip: dict = {}
    image_url: str = ""
    global_variables: dict

class TestConditionNode(BaseModel):
    username: str
    node_id: str
    name: str
    conditions: dict
    global_variables: dict

class Workflow(BaseModel):
    username: str
    nodes: list
    edges: list
    start_node: str
    global_variables: dict

class WorkflowCreate(BaseModel):
    username: str
    workflow_id: str
    workflow_name: str
    workflow_config: dict
    start_node: str
    global_variables: dict
    nodes: list
    edges: list

class WorkflowRenameInput(BaseModel):
    workflow_id: str
    workflow_new_name: str
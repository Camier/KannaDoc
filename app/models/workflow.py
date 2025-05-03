# Pydantic 模型，用于输入数据验证
from typing import Any, Dict, List
from pydantic import BaseModel


class TestFunctionCode(BaseModel):
    username: str
    node_id: str
    code: str
    global_variables: dict

class TestConditionNode(BaseModel):
    username: str
    node_id: str
    conditions: dict
    global_variables: dict

class Workflow(BaseModel):
    username: str
    nodes: list
    edges: list
    start_node: str
    global_variables: dict

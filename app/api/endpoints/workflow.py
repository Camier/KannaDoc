from fastapi import APIRouter, Depends
from app.core.security import get_current_user, verify_username_match
from app.models.workflow import TestConditionNode, TestFunctionCode, Workflow
from app.workflow.workflow_engine import WorkflowEngine
from app.models.user import User

router = APIRouter()


# 修改知识库名称
@router.post("/execute", response_model=dict)
async def execute_workflow(
    workflow: Workflow,
    # current_user: User = Depends(get_current_user),
):
    # await verify_username_match(current_user, workflow.username)
    engine = WorkflowEngine(
        nodes=workflow.nodes,
        edges=workflow.edges,
        global_variables=workflow.global_variables,
        start_node=workflow.start_node,
    )
    if engine.graph[0] == True:
        try:
            await engine.start()
            return {"code": 0, "result": engine.context, "msg": ""}
        except ValueError as e:
            return {"code": -2, "result": "", "msg": str(e)}
    else:
        return {"code": -1, "result": "", "msg": engine.graph[-1]}


# 测试python代码
@router.post("/test_code", response_model=dict)
async def execute_workflow(
    function_node: TestFunctionCode,
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, function_node.username)
    test_workflow = {
        "global_variables": function_node.global_variables,
        "nodes": [
            {
                "id": "node_start",
                "type": "start",
                "data": {},
            },
            {
                "id": function_node.node_id,
                "type": "code",
                "data": {"code": function_node.code},
            },
        ],
        "edges": [
            {"source": "node_start", "target": function_node.node_id},
        ],
    }

    engine = WorkflowEngine(
        nodes=test_workflow["nodes"],
        edges=test_workflow["edges"],
        global_variables=test_workflow["global_variables"],
    )
    if engine.graph[0] == True:
        try:
            await engine.start()
            return {"code": 0, "result": engine.context, "msg": ""}
        except ValueError as e:
            return {"code": -2, "result": "", "msg": str(e)}
    else:
        return {"code": -1, "result": "", "msg": engine.graph[-1]}


# 测试条件节点
@router.post("/test_condition", response_model=dict)
async def execute_workflow(
    condition_node: TestConditionNode,
    current_user: User = Depends(get_current_user),
):
    await verify_username_match(current_user, condition_node.username)
    test_workflow = {
        "global_variables": condition_node.global_variables,
        "nodes": [
            {
                "id": "node_start",
                "type": "start",
                "data": {},
            },
            {
                "id": condition_node.node_id,
                "type": "condition",
                "data": {"conditions": condition_node.conditions},
            },
        ],
        "edges": [
            {"source": "node_start", "target": condition_node.node_id},
        ],
    }

    engine = WorkflowEngine(
        nodes=test_workflow["nodes"],
        edges=test_workflow["edges"],
        global_variables=test_workflow["global_variables"],
    )
    if engine.graph[0] == True:
        try:
            await engine.start()
            return {"code": 0, "result": engine.context, "msg": ""}
        except ValueError as e:
            return {"code": -2, "result": "", "msg": str(e)}
    else:
        return {"code": -1, "result": "", "msg": engine.graph[-1]}

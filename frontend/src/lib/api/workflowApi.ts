"use client";
import { CustomEdge, CustomNode, sendEdges, sendNode } from "@/types/types";
import { AxiosProgressEvent } from "axios";
import { apiClient as api } from "./apiClient";

export const runPythonTest = async (
  username: string,
  node: CustomNode,
  globalVariables: {
    [key: string]: string;
  },
  sendSaveImage: string,
  DockerImageUse: string
) => {
  return api.post("/workflow/test_code", {
    username: username,
    node_id: node.id,
    name: node.data.label,
    code: node.data.code,
    pip: node.data.pip,
    image_url: node.data.imageUrl,
    global_variables: globalVariables,
    send_save_image: sendSaveImage,
    docker_image_use: DockerImageUse,
  });
};

export const runConditionTest = async (
  username: string,
  node: CustomNode,
  globalVariables: {
    [key: string]: string;
  },
  conditions: {
    [key: string]: string;
  }
) => {
  return api.post("/workflow/test_condition", {
    username: username,
    name: node.data.label,
    node_id: node.id,
    conditions: conditions,
    global_variables: globalVariables,
  });
};

export const executeWorkflow = async (
  username: string,
  nodes: sendNode[],
  edges: sendEdges[],
  startNode: string,
  globalVariables: {
    [key: string]: string;
  },
  debugResumetTaskId: string,
  inputResumetTaskId: string,
  breakpoints: string[],
  userMessage: string,
  parentId: string,
  tempBaseId: string,
  chatflowId: string,
  saveImage: string,
  DockerImageUse: string
) => {
  return api.post("/workflow/execute", {
    username: username,
    nodes: nodes,
    edges: edges,
    start_node: startNode,
    global_variables: globalVariables,
    breakpoints: breakpoints,
    debug_resume_task_id: debugResumetTaskId,
    input_resume_task_id: inputResumetTaskId,
    user_message: userMessage,
    parent_id: parentId,
    temp_db_id: tempBaseId,
    chatflow_id: chatflowId,
    docker_image_use: DockerImageUse,
    need_save_image: saveImage,
  });
};

export const deleteWorkflow = async (workflowId: string) => {
  return api.delete("/workflow/workflows/" + workflowId);
};

export const createWorkflow = async (
  workflowId: string,
  username: string,
  workflowName: string,
  workflowConfig: {},
  startNode: string,
  globalVariables: {
    [key: string]: string;
  },
  nodes: CustomNode[],
  edges: CustomEdge[]
) => {
  return api.post("/workflow/workflows", {
    workflow_id: workflowId,
    username: username,
    workflow_name: workflowName,
    workflow_config: workflowConfig,
    start_node: startNode,
    global_variables: globalVariables,
    nodes: nodes,
    edges: edges,
  });
};

export const getAllWorkflow = async (_username?: string) => {
  return api.get("/workflow/workflows");
};

export const renameWorkflow = async (
  workflowId: string,
  workflowName: string
) => {
  return api.post("/workflow/workflows/rename", {
    workflow_id: workflowId,
    workflow_new_name: workflowName,
  });
};

export const getWorkflowDetails = async (workflowId: string) => {
  return api.get("/workflow/workflows/" + workflowId);
};

export const getCustomNodes = async (_username?: string) => {
  return api.get("/workflow/nodes");
};

export const saveCustomNodes = async (
  username: string,
  customNodeName: string,
  customNode: CustomNode
) => {
  return api.post("/workflow/nodes", {
    username: username,
    custom_node_name: customNodeName,
    custom_node: customNode,
  });
};

export const deleteCustomNodes = async (
  _username: string,
  custom_node_name: string
) => {
  return api.delete(`/workflow/nodes/${custom_node_name}`);
};

export const cancelWorkflow = async (_username: string, taskId: string) => {
  return api.get(`/workflow/${taskId}/cancel`);
};

export const getMcpToolList = async (
  username:string,
  mcpUrl:string,
  headers:{[key: string]: string},
  timeout:number,
  sseReadTimeout:number
) => {
  return api.post(`/workflow/mcp_tool_list`, {
    username: username,
    mcp_url: mcpUrl,
    mcp_headers: headers,
    mcp_timeout: timeout,
    mcp_sse_read_timeout: sseReadTimeout,
  });
};

export const getDockerImages = async (_username?: string) => {
  return api.get(`/workflow/docker_image_list`);
};

export const deleteDockerImages = async (
  _username: string,
  imageName: string
) => {
  return api.delete(`/workflow/${imageName}/docker_image/`);
};

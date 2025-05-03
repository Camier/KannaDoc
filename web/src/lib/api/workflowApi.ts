"use client";
import { CustomEdge, CustomNode, sendEdges, sendNode } from "@/types/types";
import axios, { AxiosProgressEvent } from "axios";
import Cookies from "js-cookie";

const api = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_BASE_URL}`,
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle failed token verification globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Redirect to login if token is invalid or expired
      Cookies.remove("token");
      window.location.href = "/sign-in";
    }
    return Promise.reject(error);
  }
);

export const runPythonTest = async (
  username: string,
  node: CustomNode,
  globalVariables: {
    [key: string]: string;
  }
) => {
  return api.post("/workflow/test_code", {
    username: username,
    node_id: node.id,
    code: node.data.code,
    global_variables: globalVariables,
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
  }
) => {
  return api.post("/workflow/execute", {
    username: username,
    nodes: nodes,
    edges: edges,
    start_node: startNode,
    global_variables: globalVariables,
  });
};

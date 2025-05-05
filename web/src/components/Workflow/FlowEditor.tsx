// components/FlowEditor.tsx
import {
  useCallback,
  useRef,
  useEffect,
  Dispatch,
  SetStateAction,
  useState,
  useMemo,
} from "react";
import {
  ReactFlow,
  addEdge,
  MiniMap,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  type Connection,
  NodeChange,
  EdgeChange,
} from "@xyflow/react";
import {
  CustomNode,
  nodeTypesInfo,
  NodeTypeKey,
  CustomEdge,
  WorkflowAll,
  KnowledgeBase,
  ModelConfig,
} from "@/types/types";
import Cookies from "js-cookie";
import { useFlowStore } from "@/stores/flowStore";
import CustomEdgeComponent from "@/components/Workflow/CustomEdge";
import CustomNodeComponent from "@/components/Workflow/CustomNode";
import "@xyflow/react/dist/base.css";
import ConnectionLine from "@/components/Workflow/ConnectionLine";
import FunctionNodeComponent from "@/components/Workflow/NodeSettings/FunctionNode";
import StartNodeComponent from "@/components/Workflow/NodeSettings/StartNode";
import { useAuthStore } from "@/stores/authStore";
import { v4 as uuidv4 } from "uuid";
import { createWorkflow, executeWorkflow } from "@/lib/api/workflowApi";
import { useGlobalStore } from "@/stores/pythonVariableStore";
import ConditionNodeComponent from "@/components/Workflow/NodeSettings/ConditionNode";
import LoopNodeComponent from "@/components/Workflow/NodeSettings/LoopNode";
import { EventSourceParserStream } from "eventsource-parser/stream";
import VlmNodeComponent from "@/components/Workflow/NodeSettings/VlmNode";
import useModelConfigStore from "@/stores/configStore";
import { getAllKnowledgeBase } from "@/lib/api/knowledgeBaseApi";
import { getAllModelConfig } from "@/lib/api/configApi";

const getId = (type: string): string => `node_${type}_${uuidv4()}`;

interface NodeTypeSelectorProps {
  workflowName: string;
  addNode: (key: NodeTypeKey) => void;
}

const NodeTypeSelector: React.FC<NodeTypeSelectorProps> = ({
  addNode,
  workflowName,
}) => {
  const selectedType = useFlowStore((state) => state.selectedType);
  const setSelectedType = useFlowStore((state) => state.setSelectedType);

  return (
    <div className="space-y-2">
      <ul className="space-y-2">
        <div className="flex items-center justify-start px-2 gap-1 pb-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="size-5"
          >
            <path
              fillRule="evenodd"
              d="M2.25 6a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3V6Zm3.97.97a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06l-2.25 2.25a.75.75 0 0 1-1.06-1.06l1.72-1.72-1.72-1.72a.75.75 0 0 1 0-1.06Zm4.28 4.28a.75.75 0 0 0 0 1.5h3a.75.75 0 0 0 0-1.5h-3Z"
              clipRule="evenodd"
            />
          </svg>

          <span className="whitespace-nowrap overflow-auto text-sm font-semibold">
            {workflowName}
          </span>
        </div>
        <div className="pt-2 border-b-2 border-gray-200 text-center">
          Base Node
        </div>
        {Object.entries(nodeTypesInfo).map(([key, type]) => (
          <li
            key={key}
            className={`cursor-pointer p-2 rounded-full text-center hover:bg-indigo-300 hover:text-white ${
              selectedType === key ? "bg-indigo-500 text-white" : ""
            }`}
            onClick={() => {
              const typeKey = key as NodeTypeKey;
              if (selectedType === typeKey) {
                addNode(typeKey);
              } else {
                setSelectedType(typeKey);
                addNode(typeKey);
              }
            }}
          >
            <div className="flex items-center justify-start gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12a7.5 7.5 0 0 0 15 0m-15 0a7.5 7.5 0 1 1 15 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077 1.41-.513m14.095-5.13 1.41-.513M5.106 17.785l1.15-.964m11.49-9.642 1.149-.964M7.501 19.795l.75-1.3m7.5-12.99.75-1.3m-6.063 16.658.26-1.477m2.605-14.772.26-1.477m0 17.726-.26-1.477M10.698 4.614l-.26-1.477M16.5 19.794l-.75-1.299M7.5 4.205 12 12m6.894 5.785-1.149-.964M6.256 7.178l-1.15-.964m15.352 8.864-1.41-.513M4.954 9.435l-1.41-.514M12.002 12l-3.75 6.495"
                />
              </svg>
              {type.label}
            </div>
          </li>
        ))}
        <div className="pt-2 border-b-2 border-gray-200 text-center">
          Custom Node
        </div>
        {/* {Object.entries(nodeTypesInfo).map(([key, type]) => (
          <li
            key={key}
            className={`cursor-pointer p-2 rounded-full text-center hover:bg-indigo-300 hover:text-white ${
              selectedType === key ? "bg-indigo-500 text-white" : ""
            }`}
            onClick={() => {
              const typeKey = key as NodeTypeKey;
              if (selectedType === typeKey) {
                addNode(typeKey);
              } else {
                setSelectedType(typeKey);
                addNode(typeKey);
              }
            }}
          >
            <div className="flex items-center justify-start gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-6"
              >
                <path d="M17.004 10.407c.138.435-.216.842-.672.842h-3.465a.75.75 0 0 1-.65-.375l-1.732-3c-.229-.396-.053-.907.393-1.004a5.252 5.252 0 0 1 6.126 3.537ZM8.12 8.464c.307-.338.838-.235 1.066.16l1.732 3a.75.75 0 0 1 0 .75l-1.732 3c-.229.397-.76.5-1.067.161A5.23 5.23 0 0 1 6.75 12a5.23 5.23 0 0 1 1.37-3.536ZM10.878 17.13c-.447-.098-.623-.608-.394-1.004l1.733-3.002a.75.75 0 0 1 .65-.375h3.465c.457 0 .81.407.672.842a5.252 5.252 0 0 1-6.126 3.539Z" />
                <path
                  fillRule="evenodd"
                  d="M21 12.75a.75.75 0 1 0 0-1.5h-.783a8.22 8.22 0 0 0-.237-1.357l.734-.267a.75.75 0 1 0-.513-1.41l-.735.268a8.24 8.24 0 0 0-.689-1.192l.6-.503a.75.75 0 1 0-.964-1.149l-.6.504a8.3 8.3 0 0 0-1.054-.885l.391-.678a.75.75 0 1 0-1.299-.75l-.39.676a8.188 8.188 0 0 0-1.295-.47l.136-.77a.75.75 0 0 0-1.477-.26l-.136.77a8.36 8.36 0 0 0-1.377 0l-.136-.77a.75.75 0 1 0-1.477.26l.136.77c-.448.121-.88.28-1.294.47l-.39-.676a.75.75 0 0 0-1.3.75l.392.678a8.29 8.29 0 0 0-1.054.885l-.6-.504a.75.75 0 1 0-.965 1.149l.6.503a8.243 8.243 0 0 0-.689 1.192L3.8 8.216a.75.75 0 1 0-.513 1.41l.735.267a8.222 8.222 0 0 0-.238 1.356h-.783a.75.75 0 0 0 0 1.5h.783c.042.464.122.917.238 1.356l-.735.268a.75.75 0 0 0 .513 1.41l.735-.268c.197.417.428.816.69 1.191l-.6.504a.75.75 0 0 0 .963 1.15l.601-.505c.326.323.679.62 1.054.885l-.392.68a.75.75 0 0 0 1.3.75l.39-.679c.414.192.847.35 1.294.471l-.136.77a.75.75 0 0 0 1.477.261l.137-.772a8.332 8.332 0 0 0 1.376 0l.136.772a.75.75 0 1 0 1.477-.26l-.136-.771a8.19 8.19 0 0 0 1.294-.47l.391.677a.75.75 0 0 0 1.3-.75l-.393-.679a8.29 8.29 0 0 0 1.054-.885l.601.504a.75.75 0 0 0 .964-1.15l-.6-.503c.261-.375.492-.774.69-1.191l.735.267a.75.75 0 1 0 .512-1.41l-.734-.267c.115-.439.195-.892.237-1.356h.784Zm-2.657-3.06a6.744 6.744 0 0 0-1.19-2.053 6.784 6.784 0 0 0-1.82-1.51A6.705 6.705 0 0 0 12 5.25a6.8 6.8 0 0 0-1.225.11 6.7 6.7 0 0 0-2.15.793 6.784 6.784 0 0 0-2.952 3.489.76.76 0 0 1-.036.098A6.74 6.74 0 0 0 5.251 12a6.74 6.74 0 0 0 3.366 5.842l.009.005a6.704 6.704 0 0 0 2.18.798l.022.003a6.792 6.792 0 0 0 2.368-.004 6.704 6.704 0 0 0 2.205-.811 6.785 6.785 0 0 0 1.762-1.484l.009-.01.009-.01a6.743 6.743 0 0 0 1.18-2.066c.253-.707.39-1.469.39-2.263a6.74 6.74 0 0 0-.408-2.309Z"
                  clipRule="evenodd"
                />
              </svg>
              {type.label}
            </div>
          </li>
        ))} */}
      </ul>
    </div>
  );
};

interface FlowEditorProps {
  workFlow: WorkflowAll;
  setFullScreenFlow: Dispatch<SetStateAction<boolean>>;
  fullScreenFlow: boolean;
}

const FlowEditor: React.FC<FlowEditorProps> = ({
  workFlow,
  setFullScreenFlow,
  fullScreenFlow,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [codeFullScreenFlow, setCodeFullScreenFlow] = useState<boolean>(false);
  const { user } = useAuthStore();
  const { globalVariables } = useGlobalStore();
  const {
    nodes,
    edges,
    history,
    future,
    selectedNodeId,
    setSelectedEdgeId,
    setSelectedNodeId,
    setNodes,
    setEdges,
    pushHistory,
    undo,
    redo,
    deleteNode,
    deleteEdge,
    setSelectedType,
    getConditionCount,
    updateConditions,
    removeCondition,
    updateOutput,
    updateConditionCount,
    updateStatus,
  } = useFlowStore();
  const [taskId, setTaskId] = useState("");
  const [running, setRunning] = useState(false);
  const { vlmModelConfig, setVlmModelConfig } = useModelConfigStore();

  // 使用 useMemo 优化查找
  const currentNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId),
    [nodes, selectedNodeId] // 依赖精准控制
  );

  // 初始化历史记录
  useEffect(() => {
    if (history.length === 0) {
      pushHistory();
    }
  }, []);

  const splitFirstColon = (str: string) => {
    const index = str.indexOf(":");
    if (index === -1) return [str, ""]; // 没有冒号时返回原字符串和空字符串
    return [str.substring(0, index), str.substring(index + 1)];
  };

  useEffect(() => {
    if (taskId !== "") {
      const workFlowSSE = async () => {
        if (user?.name) {
          const token = Cookies.get("token"); // 确保已引入cookie库
          try {
            const response = await fetch(
              `${process.env.NEXT_PUBLIC_API_BASE_URL}/sse/workflow/${user.name}/${taskId}`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            if (!response.ok) throw new Error("Request failed");
            if (!response.body) return;

            // 使用EventSourceParserStream处理流
            const eventStream = response.body
              ?.pipeThrough(new TextDecoderStream())
              .pipeThrough(new EventSourceParserStream());

            const eventReader = eventStream.getReader();
            while (true) {
              const { done, value } = (await eventReader?.read()) || {};
              if (done) break;
              const payload = JSON.parse(value.data);

              //处理事件数据
              if (payload.event === "workflow") {
                if (payload.workflow.status == "failed") {
                  const errorNode = splitFirstColon(payload.workflow.error);
                  const errorNodeId = errorNode[0];
                  const errorNodeMsg = splitFirstColon(errorNode[1])[1];
                  updateOutput(errorNodeId, errorNodeMsg);
                  updateStatus(errorNodeId, "failed");
                }
                if (["completed", "failed"].includes(payload.workflow.status)) {
                  eventReader.cancel();
                  break;
                }
              } else if (payload.event === "node") {
                if (payload.node.status === true) {
                  if (payload.node.result !== '""') {
                    const resultList: any[] = JSON.parse(payload.node.result);
                    let result: string;
                    if (resultList.length > 1) {
                      result = resultList
                        .map(
                          (item, index) => `Loop ${index + 1}:\n${item.result}`
                        )
                        .join("\n");
                    } else {
                      result = resultList[0].result;
                    }
                    updateOutput(payload.node.id, result);
                  } else {
                    updateOutput(payload.node.id, "Node running success!");
                  }
                  updateStatus(payload.node.id, "ok");
                }
              }
            }
          } catch (error) {
            console.error("SSE错误:", error);
          } finally {
            setRunning(false);
            alert("Running Compelete!");
          }
        }
      };
      workFlowSSE();
    }
  }, [taskId]);

  const fetchModelConfig = 
    async (nodeId: string) => {
      if (user?.name) {
        const responseBase = await getAllKnowledgeBase(user.name);
        const bases: KnowledgeBase[] = responseBase.data.map((item: any) => ({
          name: item.knowledge_base_name,
          id: item.knowledge_base_id,
          selected: false,
        }));

        const response = await getAllModelConfig(user.name);

        const modelConfigsResponse: ModelConfig[] = response.data.models.map(
          (item: any) => ({
            modelId: item.model_id,
            modelName: item.model_name,
            modelURL: item.model_url,
            apiKey: item.api_key,
            baseUsed: item.base_used,
            systemPrompt: item.system_prompt,
            temperature: item.temperature === -1 ? 0.1 : item.temperature,
            maxLength: item.max_length === -1 ? 8192 : item.max_length,
            topP: item.top_P === -1 ? 0.01 : item.top_P,
            topK: item.top_K === -1 ? 3 : item.top_K,
            useTemperatureDefault: item.temperature === -1 ? true : false,
            useMaxLengthDefault: item.max_length === -1 ? true : false,
            useTopPDefault: item.top_P === -1 ? true : false,
            useTopKDefault: item.top_K === -1 ? true : false,
          })
        );

        const selected = modelConfigsResponse.find(
          (m) => m.modelId === response.data.selected_model
        );

        if (selected) {
          const filter_select = selected.baseUsed.filter((item) =>
            bases.some((base) => base.id === item.baseId)
          );
          setVlmModelConfig(nodeId, (prev) => ({
            ...prev,
            ...selected,
            baseUsed: filter_select,
          }));
        }
      }
    };

  const onNodesChange = useCallback(
    (changes: NodeChange<CustomNode>[]) => {
      setNodes(applyNodeChanges(changes, nodes));
      if (
        changes.find((change) =>
          ["dimensions", "remove", "replace", "add"].includes(change.type)
        )
      ) {
        pushHistory();
      }
    },
    [nodes, setNodes, pushHistory]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<CustomEdge>[]) => {
      setEdges(applyEdgeChanges(changes, edges));
      if (
        changes.find((change) =>
          ["remove", "replace", "add"].includes(change.type)
        )
      ) {
        pushHistory();
      }
    },
    [edges, setEdges, pushHistory]
  );

  const onEdgesDelete = (edges: CustomEdge[]) => {
    edges.map((edge) => {
      if (edge.data?.conditionLabel) {
        const conditionNodeId = edge.source;
        removeCondition(conditionNodeId, parseInt(edge.data.conditionLabel));
      }
    });
  };

  const onConnect = useCallback(
    (connection: Connection) => {
      console.log(vlmModelConfig);
      let newConnection;
      if (
        edges.find(
          (edge) =>
            edge.source === connection.source &&
            edge.target === connection.target
        )
      ) {
        return;
      }
      if (connection.source.startsWith("node_condition")) {
        const count = getConditionCount(connection.source);
        newConnection = {
          ...connection,
          data: {
            conditionLabel: `${count ? count + 1 : 1}`,
          },
        };
        setEdges(addEdge(newConnection, edges));
        updateConditionCount(connection.source, count ? count + 1 : 1);
        updateConditions(connection.source, count ? count + 1 : 1, "");
      } else if (connection.targetHandle === "target") {
        newConnection = {
          ...connection,
          data: {
            loopType: "next",
          },
        };
        setEdges(addEdge(newConnection, edges));
      } else if (connection.sourceHandle === "source") {
        newConnection = {
          ...connection,
          data: {
            loopType: "body",
          },
        };
        setEdges(addEdge(newConnection, edges));
      } else {
        setEdges(addEdge(connection, edges));
      }
      pushHistory();
    },
    [edges, setEdges, pushHistory]
  );

  const addNode = (type: NodeTypeKey) => {
    let data;
    let id;
    if (type === "code") {
      data = {
        status: "init",
        label: nodeTypesInfo[type].label,
        nodeType: type,
        code: 'def my_func():\n    print("Hello Layra!")\n\nmy_func()\n',
        output: "Output will be show here",
      };
    } else if (type === "loop") {
      data = {
        status: "init",
        label: nodeTypesInfo[type].label,
        nodeType: type,
        loopType: "count",
        maxCount: 1,
        condition: "",
        output: "Output will be show here",
      };
    } else if (type === "vlm") {
      data = {
        status: "init",
        label: nodeTypesInfo[type].label,
        nodeType: type,
        output: "Output will be show here",
        selectedModelId: "",
      };
    } else {
      data = {
        status: "init",
        label: nodeTypesInfo[type].label,
        nodeType: type,
        output: "Output will be show here",
      };
    }
    if (type === "start") {
      if (nodes.find((node) => node.data.nodeType === "start")) {
        alert("Start node already exist!");
        return;
      }
      id = "node_start";
    } else {
      id = getId(type);
    }
    const newNode: CustomNode = {
      id: id,
      type: "default",
      position: { x: Math.random() * 100, y: Math.random() * 100 },
      data: data,
    };
    if (type === "vlm") {
      fetchModelConfig(id);
    }
    setNodes([...nodes, newNode]);
  };

  const onNodeClick = (_: any, node: CustomNode) => {
    setSelectedType(node.data.nodeType);
    setSelectedNodeId(node.id);
  };

  const onEdgeClick = (_: any, edge: CustomEdge) => {
    setSelectedEdgeId(edge.id);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Delete") {
      const selectedNode = nodes.find((n) => n.selected);
      if (selectedNode) {
        deleteNode(selectedNode.id);
      }
      const selectedEdge = edges.find((e) => e.selected);
      if (selectedEdge) {
        deleteEdge(selectedEdge.id);
      }
    }
  };

  const handleRunWorkflow = async () => {
    if (user?.name) {
      setRunning(true);
      nodes.forEach((node) => {
        updateOutput(node.id, "Await for running...");
        updateStatus(node.id, "init");
      });
      try {
        const sendNodes = nodes.map((node) => ({
          id: node.id,
          type: node.data.nodeType,
          data: {
            name: node.data.label,
            code: node.data.code,
            conditions: node.data.conditions,
            loopType: node.data.loopType,
            maxCount: node.data.maxCount,
            condition: node.data.condition,
            pip: node.data.pip,
            imageUrl: node.data.imageUrl,
          },
        }));

        const sendEdges = edges.map((edge) => {
          if (edge.data?.conditionLabel) {
            return {
              source: edge.source,
              target: edge.target,
              sourceHandle: "condition-" + edge.data?.conditionLabel,
            };
          } else if (edge.sourceHandle === "source") {
            return {
              source: edge.source,
              target: edge.target,
              sourceHandle: "loop_body",
            };
          } else if (edge.targetHandle === "target") {
            return {
              source: edge.source,
              target: edge.target,
              sourceHandle: "loop_next",
            };
          } else {
            return {
              source: edge.source,
              target: edge.target,
            };
          }
        });
        const response = await executeWorkflow(
          user.name,
          sendNodes,
          sendEdges,
          "node_start",
          globalVariables
        );
        if (response.data.code === 0) {
          setTaskId(response.data.task_id);
        } else {
          alert(response.data.msg);
        }
      } catch (error) {
        console.error("Error connect:", error);
        setRunning(false);
      } finally {
      }
    }
  };

  const handleSaveWorkFlow = async () => {
    if (user?.name) {
      try {
        const response = await createWorkflow(
          workFlow.workflowId,
          user.name,
          workFlow.workflowName,
          workFlow.workflowConfig,
          workFlow.startNode,
          globalVariables,
          nodes,
          edges
        );
        if (response.status == 200) {
          alert("save success!");
        }
      } catch (error) {
        console.error("Error fetching chat history:", error);
      }
    }
  };

  return (
    <div
      className="flex-1 h-full flex items-center justify-center bg-white rounded-3xl shadow-sm p-6"
      ref={reactFlowWrapper}
      tabIndex={0}
      onKeyDown={onKeyDown}
    >
      <div className="w-[15%] bg-white pr-4 h-full overflow-scroll">
        <NodeTypeSelector
          workflowName={workFlow.workflowName}
          addNode={addNode}
        />
      </div>

      <div className="h-full flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center justify-center gap-1">
            <button
              onClick={undo}
              disabled={history.length <= 1}
              className="cursor-pointer disabled:cursor-not-allowed p-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3"
                />
              </svg>
              <span>({Math.min(history.length - 1, 50)})</span>
            </button>
            <button
              onClick={redo}
              disabled={future.length === 0}
              className="cursor-pointer disabled:cursor-not-allowed p-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
            >
              <span>({Math.min(future.length, 50)})</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m15 15 6-6m0 0-6-6m6 6H9a6 6 0 0 0 0 12h3"
                />
              </svg>
            </button>
          </div>

          <button
            className="cursor-pointer disabled:cursor-not-allowed px-4 py-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
            onClick={() => setFullScreenFlow((prev: boolean) => !prev)}
          >
            {fullScreenFlow ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 9V4.5M9 9H4.5M9 9 3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5 5.25 5.25"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                />
              </svg>
            )}
          </button>

          <div className="flex items-center justify-center gap-2">
            <div className="flex items-center justify-center gap-1">
              <button
                disabled={running}
                onClick={handleRunWorkflow}
                className={`cursor-pointer disabled:cursor-not-allowed p-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
                  />
                </svg>

                <span>Run</span>
              </button>
              {/* <button className="cursor-pointer disabled:cursor-not-allowed p-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 12.75c1.148 0 2.278.08 3.383.237 1.037.146 1.866.966 1.866 2.013 0 3.728-2.35 6.75-5.25 6.75S6.75 18.728 6.75 15c0-1.046.83-1.867 1.866-2.013A24.204 24.204 0 0 1 12 12.75Zm0 0c2.883 0 5.647.508 8.207 1.44a23.91 23.91 0 0 1-1.152 6.06M12 12.75c-2.883 0-5.647.508-8.208 1.44.125 2.104.52 4.136 1.153 6.06M12 12.75a2.25 2.25 0 0 0 2.248-2.354M12 12.75a2.25 2.25 0 0 1-2.248-2.354M12 8.25c.995 0 1.971-.08 2.922-.236.403-.066.74-.358.795-.762a3.778 3.778 0 0 0-.399-2.25M12 8.25c-.995 0-1.97-.08-2.922-.236-.402-.066-.74-.358-.795-.762a3.734 3.734 0 0 1 .4-2.253M12 8.25a2.25 2.25 0 0 0-2.248 2.146M12 8.25a2.25 2.25 0 0 1 2.248 2.146M8.683 5a6.032 6.032 0 0 1-1.155-1.002c.07-.63.27-1.222.574-1.747m.581 2.749A3.75 3.75 0 0 1 15.318 5m0 0c.427-.283.815-.62 1.155-.999a4.471 4.471 0 0 0-.575-1.752M4.921 6a24.048 24.048 0 0 0-.392 3.314c1.668.546 3.416.914 5.223 1.082M19.08 6c.205 1.08.337 2.187.392 3.314a23.882 23.882 0 0 1-5.223 1.082"
                  />
                </svg>

                <span>Debug</span>
              </button> */}
            </div>
            <div className="flex items-center justify-center gap-1">
              <button
                onClick={handleSaveWorkFlow}
                className="cursor-pointer disabled:cursor-not-allowed p-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="size-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                  />
                </svg>
                <span>Save</span>
              </button>
              {/* <button className="cursor-pointer disabled:cursor-not-allowed p-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                  />
                </svg>

                <span>Clear</span>
              </button> */}
            </div>
          </div>
        </div>

        <div className="flex-1 rounded-3xl shadow-sm bg-white relative overflow-hidden">
          {currentNode && (
            <div
              className={`p-2 absolute z-10 max-h-[calc(100%-16px)] ${
                codeFullScreenFlow
                  ? "w-[96%] h-[98%] fixed  top-[1%] right-[2%]"
                  : "w-[40%]  h-[98%] absolute m-2 top-0 right-0"
              } shadow-lg rounded-3xl bg-white`}
            >
              {{
                code: (
                  <FunctionNodeComponent
                    node={currentNode}
                    codeFullScreenFlow={codeFullScreenFlow}
                    setCodeFullScreenFlow={setCodeFullScreenFlow}
                  />
                ),
                start: (
                  <StartNodeComponent
                    node={currentNode}
                    codeFullScreenFlow={codeFullScreenFlow}
                    setCodeFullScreenFlow={setCodeFullScreenFlow}
                  />
                ),
                vlm: (
                  <VlmNodeComponent
                    node={currentNode}
                    codeFullScreenFlow={codeFullScreenFlow}
                    setCodeFullScreenFlow={setCodeFullScreenFlow}
                  />
                ),
                condition: (
                  <ConditionNodeComponent
                    node={currentNode}
                    codeFullScreenFlow={codeFullScreenFlow}
                    setCodeFullScreenFlow={setCodeFullScreenFlow}
                  />
                ),
                end: <div></div>,
                loop: (
                  <LoopNodeComponent
                    node={currentNode}
                    codeFullScreenFlow={codeFullScreenFlow}
                    setCodeFullScreenFlow={setCodeFullScreenFlow}
                  />
                ),
              }[currentNode.data.nodeType] || <div></div>}
            </div>
          )}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onEdgesDelete={onEdgesDelete}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={() => {
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
            }} // 添加这一行
            nodeTypes={{ default: CustomNodeComponent }}
            edgeTypes={{ default: CustomEdgeComponent }}
            connectionLineComponent={ConnectionLine}
            connectionRadius={20}
            fitView
            fitViewOptions={{
              padding: 0.2,
            }}
            className="!border-0 !bg-gray-50"
          >
            <MiniMap />
            <Controls />
            <Background gap={12} size={1} />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
};

export default FlowEditor;

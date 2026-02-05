/**
 * FlowEditor (Refactored)
 *
 * Main workflow editor component providing a visual node-based workflow interface.
 * Coordinates between canvas, toolbar, panels, and execution handlers.
 *
 * Decomposed from original 2259-line component into focused sub-components:
 * - WorkflowExecutionHandler: SSE and real-time updates
 * - WorkflowToolbar: Control buttons and actions
 * - WorkflowCanvasPanel: Node settings and output display
 * - WorkflowImportExport: Import/export functionality
 * - WorkflowSaveHandler: Manual and auto-save operations
 * - WorkflowNodeOperations: Node creation and management
 *
 * Main responsibilities:
 * - ReactFlow canvas management
 * - Node/edge state coordination
 * - Keyboard shortcuts
 * - Dialog/alert management
 */

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
  CustomEdge,
  WorkflowAll,
  Message,
  FileResponse,
} from "@/types/types";
import { useFlowStore } from "@/stores/flowStore";
import { logger } from "@/lib/logger";
import CustomEdgeComponent from "@/components/Workflow/CustomEdge";
import CustomNodeComponent from "@/components/Workflow/CustomNode";
import "@xyflow/react/dist/base.css";
import ConnectionLine from "@/components/Workflow/ConnectionLine";
import { v4 as uuidv4 } from "uuid";
import {
  cancelWorkflow,
  executeWorkflow,
} from "@/lib/api/workflowApi";
import { useGlobalStore } from "@/stores/WorkflowVariableStore";
import { deleteTempKnowledgeBase } from "@/lib/api/knowledgeBaseApi";
import ConfirmAlert from "../ConfirmAlert";
import NodeTypeSelector from "./NodeTypeSelector";
import SaveCustomNode from "./SaveNode";
import useChatStore from "@/stores/chatStore";
import { getFileExtension } from "@/utils/file";
import { createChatflow } from "@/lib/api/chatflowApi";
import ConfirmDialog from "../ConfirmDialog";
import { useTranslations } from "next-intl";
import { ANONYMOUS_USER } from "@/lib/constants";

// Extracted components
import { WorkflowExecutionHandler } from "./FlowEditor/WorkflowExecutionHandler";
import { WorkflowToolbar } from "./FlowEditor/WorkflowToolbar";
import { WorkflowCanvasPanel } from "./FlowEditor/WorkflowCanvasPanel";
import { useWorkflowImportExport } from "./FlowEditor/WorkflowImportExport";
import { useWorkflowSaveHandler } from "./FlowEditor/WorkflowSaveHandler";
import { useWorkflowNodeOperations } from "./FlowEditor/WorkflowNodeOperations";

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
  const t = useTranslations("FlowEditor");
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [codeFullScreenFlow, setCodeFullScreenFlow] = useState<boolean>(false);
  const user = ANONYMOUS_USER;

  const {
    globalVariables,
    reset,
    setGlobalDebugVariables,
    globalDebugVariables,
    DockerImageUse,
  } = useGlobalStore();

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
    updateChat,
    updateConditionCount,
    updateStatus,
    updateVlmModelConfig,
    updateVlmInput,
  } = useFlowStore();

  // State management
  const [taskId, setTaskId] = useState("");
  const [running, setRunning] = useState(false);
  const [resumeDebugTaskId, setResumeDebugTaskId] = useState("");
  const [resumeInputTaskId, setResumeInputTaskId] = useState("");
  const [showAlert, setShowAlert] = useState(false);
  const [workflowMessage, setWorkflowMessage] = useState("");
  const [workflowStatus, setWorkflowStatus] = useState("");
  const [customNodes, setCustomNodes] = useState<{ [key: string]: CustomNode }>(
    {}
  );
  const [showAddNode, setShowAddNode] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [newNodeName, setNewNodeName] = useState("");
  const [newCustomNode, setNewCustomNode] = useState<CustomNode | null>(null);
  const [canceling, setCanceling] = useState(false);
  const [showOutput, setShowOutput] = useState(false);
  const [messages, setMessages] = useState<{ [key: string]: Message[] }>({});
  const [sendInputDisabled, setSendInputDisabled] = useState(true);
  const [sendingFiles, setSendingFiles] = useState<FileResponse[]>([]);
  const [tempBaseId, setTempBaseId] = useState<string>("");
  const [cleanTempBase, setCleanTempBase] = useState<boolean>(false);
  const [currentInputNodeId, setCurrentInputNodeId] = useState<string>();
  const [fileMessages, setFileMessages] = useState<Message[]>([]);
  const { chatflowId, setChatflowId } = useChatStore();
  const [showConfirmClear, setShowConfirmClear] = useState(false);
  const [saveImage, setSaveImage] = useState<boolean>(false);
  const [saveImageName, setSaveImageName] = useState<string>("");
  const [saveImageTag, setSaveImageTag] = useState<string>("");
  const [saveStatus, setSaveStatus] = useState<{
    visible: boolean;
    message: string;
    type: "success" | "error";
  }>({ visible: false, message: "", type: "success" });
  const [refreshDockerImages, setRefreshDockerImages] =
    useState<boolean>(false);
  const [runningChatflowLLMNodes, setRunningChatflowLLMNodes] = useState<
    CustomNode[]
  >([]);
  const [eachMessages, setEachMessages] = useState<{
    [key: string]: Message[];
  }>({});

  // Refs
  const countRef = useRef(1);
  const countListRef = useRef<string[]>([]);
  const eachMessagesRef = useRef(eachMessages);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  useEffect(() => {
    edgesRef.current = edges;
  }, [edges]);

  // Computed values
  const currentNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId),
    [nodes, selectedNodeId]
  );

  // Clear handlers
  const confirmClear = () => {
    if (showConfirmClear) {
      setNodes([]);
      setEdges([]);
      reset();
      setShowConfirmClear(false);
    }
  };

  const cancelClear = () => {
    if (showConfirmClear) {
      setShowConfirmClear(false);
    }
  };

  // Alert handler
  const handleShowAlert = (message: string, status: string) => {
    setWorkflowMessage(message);
    setWorkflowStatus(status);
    setShowAlert(true);
  };

  // Import/Export
  const { fileInputRef, triggerImport, handleExportWorkflow, handleImportWorkflow } = useWorkflowImportExport({
    workflowName: workFlow.workflowName,
    nodes,
    edges,
    globalVariables,
    onImport: (importedNodes, importedEdges, importedVars) => {
      setNodes(importedNodes);
      setEdges(importedEdges);
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      pushHistory();
    },
    onError: (error) => handleShowAlert(error, "error"),
  });

  // Save handler
  const { handleSaveWorkFlow } = useWorkflowSaveHandler({
    workflowId: workFlow.workflowId,
    workflowName: workFlow.workflowName,
    startNode: workFlow.startNode,
    userName: user?.name,
    dockerImageUse: DockerImageUse,
    globalVariables,
    nodes,
    edges,
    onSaveStatusChange: setSaveStatus,
  });

  // Node operations
  const {
    addNode,
    addCustomNode,
    fetchAllCustomNodes,
    handleDeleteCustomNode,
  } = useWorkflowNodeOperations({
    user,
    customNodes,
    setCustomNodes,
    nodes,
    setNodes,
    onUpdateVlmModelConfig: updateVlmModelConfig,
    onShowAlert: handleShowAlert,
    pushHistory,
  });

  // Effects
  useEffect(() => {
    const cleanTempKnowledgeBase = async () => {
      if (user?.name) {
        try {
          setCleanTempBase(true);
          await deleteTempKnowledgeBase(user.name);
        } catch (error) {
          logger.error("Error clean temp knowledge base:", error);
        } finally {
          setCleanTempBase(false);
        }
      }
    };
    cleanTempKnowledgeBase();
  }, [user?.name]);

  useEffect(() => {
    setSendingFiles([]);
    setTempBaseId("");
  }, [chatflowId]);

  const handleNewChatflow = useCallback(() => {
    setChatflowId("");
  }, [setChatflowId]);

  // Refresh page
  useEffect(() => {
    const { history } = useFlowStore.getState();

    if (history.length === 0) {
      pushHistory();
    }
    handleNewChatflow();
    setMessages({});
    setEachMessages({});
    setSendInputDisabled(true);
    setResumeDebugTaskId("");
    setResumeInputTaskId("");
    countListRef.current = [];
    setCurrentInputNodeId(undefined);
    setRunningChatflowLLMNodes([]);
    countRef.current = 1;
    nodesRef.current.forEach((node) => {
      if (node.data.nodeType == "vlm") {
        updateOutput(node.id, t("vlmOutputPlaceholder"));
      } else {
        updateOutput(node.id, t("awaitRunning"));
      }
      updateStatus(node.id, "init");
      if (node.data.nodeType == "vlm") {
        updateChat(node.id, t("vlmChatPlaceholder"));
      } else {
        updateChat(node.id, t("awaitRunning"));
      }
    });
  }, 
  // eslint-disable-next-line react-hooks/exhaustive-deps -- Using nodesRef.current to prevent infinite render loop (React #185)
  [
    workFlow,
    handleNewChatflow,
    pushHistory,
    updateChat,
    updateOutput,
    updateStatus,
    t,
  ]);

  // Refresh button
  const handleRefresh = () => {
    if (history.length === 0) {
      pushHistory();
    }
    handleNewChatflow();
    setMessages({});
    setEachMessages({});
    setSendInputDisabled(true);
    setResumeDebugTaskId("");
    setResumeInputTaskId("");
    countListRef.current = [];
    setCurrentInputNodeId(undefined);
    setRunningChatflowLLMNodes([]);
    countRef.current = 1;
    nodes.forEach((node) => {
      if (node.data.nodeType == "vlm") {
        updateOutput(node.id, t("vlmOutputPlaceholder"));
      } else {
        updateOutput(node.id, t("awaitRunning"));
      }
      updateStatus(node.id, "init");
      if (node.data.nodeType == "vlm") {
        updateChat(node.id, t("vlmChatPlaceholder"));
      } else {
        updateChat(node.id, t("awaitRunning"));
      }
    });
  };

  useEffect(() => {
    if (chatflowId === "") {
      const uniqueId = uuidv4();
      setChatflowId(user?.name + "_" + uniqueId);
    }
  }, [user?.name, chatflowId, setChatflowId]);

  useEffect(() => {
    setShowOutput(false);
  }, [workFlow]);

  useEffect(() => {
    fetchAllCustomNodes();
  }, [user?.name, fetchAllCustomNodes]);

  const onNodesChange = useCallback(
    (changes: NodeChange<CustomNode>[]) => {
      setNodes(applyNodeChanges(changes, nodesRef.current));
      if (
        changes.find((change) =>
          ["remove", "replace", "add"].includes(change.type)
        )
      ) {
        pushHistory();
      }
    },
    [setNodes, pushHistory]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<CustomEdge>[]) => {
      setEdges(applyEdgeChanges(changes, edgesRef.current));
      if (
        changes.find((change) =>
          ["remove", "replace", "add"].includes(change.type)
        )
      ) {
        pushHistory();
      }
    },
    [setEdges, pushHistory]
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
    [
      edges,
      setEdges,
      pushHistory,
      getConditionCount,
      updateConditionCount,
      updateConditions,
    ]
  );

  const onNodeClick = (_: any, node: CustomNode) => {
    setSelectedType(node.data.nodeType);
    setSelectedNodeId(node.id);
    setShowOutput(false);
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

  // Workflow execution
  const handleRunWorkflow = async (
    debug: boolean = false,
    input_resume: boolean = false,
    userMessage: string = "",
    files: FileResponse[] = [],
    tempBaseId: string = ""
  ) => {
    if (saveImage) {
      if (saveImageName === "" || saveImageTag === "") {
        handleShowAlert(t("imageNameVersionRequired"), "error");
        return;
      }
    }

    const sendSaveImage = saveImage ? saveImageName + ":" + saveImageTag : "";

    for (let node of nodes) {
      if (
        node.data.nodeType === "vlm" &&
        node.data.isChatflowInput === false &&
        node.data.vlmInput === ""
      ) {
        handleShowAlert(
          t("questionRequiredForNode", { nodeName: node.data.label }),
          "error"
        );
        return;
      }
    }

    if (user?.name) {
      setRunning(true);
      if (
        (debug === false && input_resume === false) ||
        (resumeDebugTaskId === "" && resumeInputTaskId === "")
      ) {
        handleNewChatflow();
        setMessages({});
        setEachMessages({});
        countListRef.current = [];
        setCurrentInputNodeId(undefined);
        setRunningChatflowLLMNodes([]);
        countRef.current = 1;
        nodes.forEach((node) => {
          updateOutput(node.id, t("awaitRunning"));
          updateStatus(node.id, "init");
          updateChat(node.id, t("awaitRunning"));
        });
      }

      if (files.length > 0) {
        const newFileMessages: Message[] = files.map((file) => {
          const fileType: string = getFileExtension(file.filename);
          if (["png", "jpg", "jpeg", "gif"].includes(fileType)) {
            return {
              type: "image",
              content: file.filename,
              minioUrl: file.url,
              from: "user",
            };
          } else {
            return {
              type: "file",
              content: userMessage,
              fileName: file.filename,
              fileType: fileType,
              minioUrl: file.url,
              from: "user",
            };
          }
        });
        setFileMessages(newFileMessages);
      } else {
        setFileMessages([]);
      }

      try {
        const sendNodes = nodes.map((node) => {
          const modelConfig = {
            model_name: node.data.modelConfig?.modelName,
            model_url: node.data.modelConfig?.modelURL,
            api_key: node.data.modelConfig?.apiKey,
            base_used: node.data.modelConfig?.baseUsed,
            system_prompt: node.data.modelConfig?.systemPrompt,
            temperature: node.data.modelConfig?.useTemperatureDefault
              ? -1
              : node.data.modelConfig?.temperature,
            max_length: node.data.modelConfig?.useMaxLengthDefault
              ? -1
              : node.data.modelConfig?.maxLength,
            top_P: node.data.modelConfig?.useTopPDefault
              ? -1
              : node.data.modelConfig?.topP,
            top_K: node.data.modelConfig?.useTopKDefault
              ? -1
              : node.data.modelConfig?.topK,
            score_threshold: node.data.modelConfig?.useScoreThresholdDefault
              ? -1
              : node.data.modelConfig?.scoreThreshold,
          };

          const filterMcpConfig = (
            mcpConfig: {
              [key: string]: any;
            },
            mcpUse: {
              [key: string]: string[];
            }
          ) => {
            const filteredConfig: {
              [key: string]: any;
            } = {};
            for (const key of Object.keys(mcpUse)) {
              if (mcpConfig[key]) {
                const originalConfig = mcpConfig[key];
                const filteredTools = originalConfig.mcpTools.filter((tool: any) =>
                  mcpUse[key].includes(tool.name)
                );
                filteredConfig[key] = {
                  ...originalConfig,
                  mcpTools: filteredTools,
                };
              }
            }
            return filteredConfig;
          };

          let mcpUse: { [key: string]: any };
          if (node.data.mcpConfig && node.data.mcpUse) {
            mcpUse = filterMcpConfig(node.data.mcpConfig, node.data.mcpUse);
          } else {
            mcpUse = {};
          }

          return {
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
              modelConfig: modelConfig,
              prompt: node.data.prompt,
              vlmInput: node.data.vlmInput,
              chatflowOutputVariable: node.data.chatflowOutputVariable,
              isChatflowInput: node.data.isChatflowInput,
              isChatflowOutput: node.data.isChatflowOutput,
              useChatHistory: node.data.useChatHistory,
              mcpUse: mcpUse,
            },
          };
        });

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

        let sendBreakpoints: string[];
        let sendDebugResumeTaskId: string;
        let sendInputResumeTaskId: string;
        let sendGlobalVariables = globalVariables;
        if (debug && !input_resume) {
          sendBreakpoints = nodes
            .filter((node) => node.data.debug === true)
            .map((node) => node.id);
          sendDebugResumeTaskId = resumeDebugTaskId;
          if (resumeDebugTaskId !== "") {
            sendGlobalVariables = globalDebugVariables;
          }
          sendInputResumeTaskId = "";
        } else if (input_resume && debug) {
          sendBreakpoints = nodes
            .filter((node) => node.data.debug === true)
            .map((node) => node.id);
          sendDebugResumeTaskId = "";
          if (resumeInputTaskId !== "") {
            sendGlobalVariables = globalDebugVariables;
          }
          sendInputResumeTaskId = resumeInputTaskId;
        } else if (input_resume && !debug) {
          sendDebugResumeTaskId = "";
          sendInputResumeTaskId = resumeInputTaskId;
          sendBreakpoints = [];
        } else {
          sendBreakpoints = [];
          sendDebugResumeTaskId = "";
          sendInputResumeTaskId = "";
        }

        let parentId: string = "";
        if (countListRef.current.length > 0) {
          const lastNodeMessages =
            eachMessagesRef.current[
              countListRef.current[countListRef.current.length - 1]
            ];
          if (lastNodeMessages.length > 0) {
            if (lastNodeMessages[lastNodeMessages.length - 1].from === "ai") {
              parentId =
                lastNodeMessages[lastNodeMessages.length - 1].messageId || "";
            }
          }
        }

        const response = await executeWorkflow(
          user.name,
          sendNodes,
          sendEdges,
          workFlow.startNode || "node_start",
          sendGlobalVariables,
          sendDebugResumeTaskId,
          sendInputResumeTaskId,
          sendBreakpoints,
          userMessage,
          parentId,
          tempBaseId,
          chatflowId,
          sendSaveImage,
          DockerImageUse
        );
        if (response.data.code === 0) {
          setTaskId(response.data.task_id);
        } else {
          handleShowAlert(response.data.msg, "error");
          setRunning(false);
        }
      } catch (error) {
        logger.error("Error connect:", error);
        setRunning(false);
      }
    }
  };

  const handleStopWorkflow = async () => {
    if (user?.name) {
      try {
        await cancelWorkflow(user.name, taskId);
        setCanceling(true);
      } catch (error) {
        logger.error("Cancel failed: ", error);
        handleShowAlert(t("cancelFailed") + error, "error");
      }
    }
  };

  const handleSaveNodes = (newNode: CustomNode) => {
    setShowAddNode(true);
    setNewCustomNode(newNode);
  };

  const handleCreateConfirm = async () => {
    if (!newNodeName.trim()) {
      setNameError(t("emptyNodeName"));
      return;
    }
    if (newNodeName.includes(" ")) {
      setNameError(t("spaceNodeName"));
      return;
    }
    if (
      Object.entries(customNodes).find(([name, node]) => name === newNodeName)
    ) {
      setNameError(t("duplicateNodeName"));
      return;
    }
    // Save logic here
    setShowAddNode(false);
    setNewNodeName("");
    setNameError(null);
  };

  const handleSendMessage = async (
    message: string,
    files: FileResponse[],
    tempBaseId: string
  ) => {
    setSendInputDisabled(true);
    if (currentInputNodeId) {
      updateVlmInput(currentInputNodeId, message);
      if (user?.name) {
        try {
          await createChatflow(
            chatflowId,
            user?.name,
            "chatflow",
            workFlow.workflowId
          );
        } catch (error) {
          logger.error("Error delete file:", error);
        }
      }
      resumeDebugTaskId
        ? handleRunWorkflow(true, true, message, files, tempBaseId)
        : handleRunWorkflow(false, true, message, files, tempBaseId);
    }
  };

  return (
    <div
      className="grid grid-cols-[15%_1fr] h-full w-full bg-white dark:bg-gray-900 text-gray-900 dark:text-white rounded-3xl shadow-sm p-6"
      ref={reactFlowWrapper}
      tabIndex={0}
      onKeyDown={onKeyDown}
    >
      <div className="bg-white dark:bg-gray-900 pr-4 h-full overflow-auto">
        <NodeTypeSelector
          deleteCustomNode={handleDeleteCustomNode}
          customNodes={customNodes}
          setCustomNodes={setCustomNodes}
          addCustomNode={addCustomNode}
          workflowName={workFlow.workflowName}
          lastModifyTime={workFlow.lastModifyTime}
          addNode={addNode}
        />
      </div>

      <div className="h-full flex flex-col">
        <WorkflowToolbar
          historyLength={history.length}
          futureLength={future.length}
          nodesLength={nodes.length}
          running={running}
          resumeDebugTaskId={resumeDebugTaskId}
          selectedNodeId={selectedNodeId}
          sendInputDisabled={sendInputDisabled}
          showOutput={showOutput}
          fullScreenFlow={fullScreenFlow}
          fileInputRef={fileInputRef}
          handleImportWorkflow={handleImportWorkflow}
          onUndo={undo}
          onRedo={redo}
          onImport={triggerImport}
          onExport={handleExportWorkflow}
          onRefresh={handleRefresh}
          onToggleFullScreen={() => setFullScreenFlow((prev) => !prev)}
          onToggleOutput={() => {
            if (selectedNodeId) {
              setShowOutput(true);
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
            } else {
              setShowOutput((prev) => !prev);
            }
          }}
          onRun={() => handleRunWorkflow(false)}
          onDebug={() => handleRunWorkflow(true)}
          onSave={handleSaveWorkFlow}
          onStop={handleStopWorkflow}
          onClear={() => setShowConfirmClear(true)}
        />

        <div className="flex-1 rounded-3xl shadow-sm bg-gray-50 dark:bg-gray-900 relative overflow-hidden">
          <WorkflowCanvasPanel
            currentNode={currentNode}
            showOutput={showOutput}
            codeFullScreenFlow={codeFullScreenFlow}
            setCodeFullScreenFlow={setCodeFullScreenFlow}
            resumeDebugTaskId={resumeDebugTaskId}
            messages={messages}
            setMessages={setMessages}
            onSaveNode={handleSaveNodes}
            showError={(error) => handleShowAlert(error, "error")}
            workFlow={workFlow}
            tempBaseId={tempBaseId}
            setTempBaseId={setTempBaseId}
            sendingFiles={sendingFiles}
            setSendingFiles={setSendingFiles}
            cleanTempBase={cleanTempBase}
            onSendMessage={handleSendMessage}
            sendDisabled={sendInputDisabled}
            messagesWithCount={eachMessages}
            runningLLMNodes={runningChatflowLLMNodes}
            refreshDockerImages={refreshDockerImages}
            saveImage={saveImage}
            setSaveImage={setSaveImage}
            saveImageName={saveImageName}
            setSaveImageName={setSaveImageName}
            saveImageTag={saveImageTag}
            setSaveImageTag={setSaveImageTag}
          />

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onEdgesDelete={onEdgesDelete}
            deleteKeyCode={[]}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={() => {
              setSelectedNodeId(null);
              setSelectedEdgeId(null);
              setShowOutput(false);
            }}
            nodeTypes={{ default: CustomNodeComponent }}
            edgeTypes={{ default: CustomEdgeComponent }}
            connectionLineComponent={ConnectionLine}
            connectionRadius={20}
            fitView
            fitViewOptions={{
              padding: 0.2,
            }}
            className="!border-0 !bg-gray-50 dark:!bg-gray-900"
          >
            <MiniMap />
            <Controls />
            <Background gap={12} size={1} />
          </ReactFlow>
        </div>
      </div>

      <WorkflowExecutionHandler
        taskId={taskId}
        user={user}
        nodes={nodes}
        selectedNodeId={selectedNodeId}
        fileMessages={fileMessages}
        globalDebugVariables={globalDebugVariables}
        onRunningChange={setRunning}
        onCancelingChange={setCanceling}
        onTaskIdChange={setTaskId}
        onUpdateOutput={updateOutput}
        onUpdateStatus={updateStatus}
        onSetSelectedNodeId={setSelectedNodeId}
        onSetSelectedEdgeId={setSelectedEdgeId}
        onSetGlobalDebugVariables={setGlobalDebugVariables}
        onSetMessages={setMessages}
        onSetEachMessages={setEachMessages}
        onSetResumeDebugTaskId={setResumeDebugTaskId}
        onSetResumeInputTaskId={setResumeInputTaskId}
        onSetCurrentInputNodeId={setCurrentInputNodeId}
        onSetShowOutput={setShowOutput}
        onSetSendInputDisabled={setSendInputDisabled}
        onSetRunningChatflowLLMNodes={setRunningChatflowLLMNodes}
        onShowAlert={handleShowAlert}
        countRef={countRef}
        countListRef={countListRef}
        eachMessagesRef={eachMessagesRef}
      />

      {showAlert && (
        <ConfirmAlert
          type={workflowStatus}
          message={workflowMessage}
          onCancel={() => setShowAlert(false)}
        />
      )}
      {showAddNode && (
        <SaveCustomNode
          setShowSaveNode={setShowAddNode}
          nameError={nameError}
          setNameError={setNameError}
          newNodeName={newNodeName}
          setNewNodeName={setNewNodeName}
          onCreateConfirm={handleCreateConfirm}
        />
      )}
      {showConfirmClear && (
        <ConfirmDialog
          message={t("confirmClearChatflow")}
          onConfirm={confirmClear}
          onCancel={cancelClear}
        />
      )}
      {saveStatus.visible && (
        <div
          className={`
          fixed top-16 left-1/2 transform -translate-x-1/2 px-4 py-2 rounded-lg shadow-lg text-sm
          transition-opacity duration-500
          ${
            saveStatus.type === "success"
              ? "bg-indigo-100 text-indigo-700"
              : "bg-red-100 text-red-700"
          }
          animate-fade-in-out
        `}
        >
          {saveStatus.message}
        </div>
      )}
    </div>
  );
};

export default FlowEditor;

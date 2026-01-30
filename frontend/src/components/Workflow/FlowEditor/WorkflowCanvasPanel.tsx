/**
 * WorkflowCanvasPanel
 *
 * Right-side panel component that displays node settings or workflow output.
 * Shows different node type configurations based on selected node.
 *
 * Responsibilities:
 * - Display node-specific settings panel
 * - Display workflow output/chat panel
 * - Handle fullscreen mode for code editor
 * - Render appropriate component based on node type
 */

import React from "react";
import { CustomNode, Message, FileResponse } from "@/types/types";
import FunctionNodeComponent from "../NodeSettings/FunctionNode";
import StartNodeComponent from "../NodeSettings/StartNode";
import VlmNodeComponent from "../NodeSettings/VlmNode";
import ConditionNodeComponent from "../NodeSettings/ConditionNode";
import LoopNodeComponent from "../NodeSettings/LoopNode";
import WorkflowOutputComponent from "../NodeSettings/WorkflowOutput";

interface WorkflowCanvasPanelProps {
  currentNode: CustomNode | undefined;
  showOutput: boolean;
  codeFullScreenFlow: boolean;
  setCodeFullScreenFlow: React.Dispatch<React.SetStateAction<boolean>>;
  resumeDebugTaskId: string;
  // VLM Node props
  messages: { [key: string]: Message[] };
  setMessages: React.Dispatch<React.SetStateAction<{ [key: string]: Message[] }>>;
  onSaveNode: (node: CustomNode) => void;
  showError: (error: string) => void;
  // Output props
  workFlow: any;
  tempBaseId: string;
  setTempBaseId: React.Dispatch<React.SetStateAction<string>>;
  sendingFiles: FileResponse[];
  setSendingFiles: React.Dispatch<React.SetStateAction<FileResponse[]>>;
  cleanTempBase: boolean;
  onSendMessage: (message: string, files: FileResponse[], tempBaseId: string) => void;
  sendDisabled: boolean;
  messagesWithCount: { [key: string]: Message[] };
  runningLLMNodes: CustomNode[];
  // Docker image props
  refreshDockerImages: boolean;
  saveImage: boolean;
  setSaveImage: React.Dispatch<React.SetStateAction<boolean>>;
  saveImageName: string;
  setSaveImageName: React.Dispatch<React.SetStateAction<string>>;
  saveImageTag: string;
  setSaveImageTag: React.Dispatch<React.SetStateAction<string>>;
}

export const WorkflowCanvasPanel: React.FC<WorkflowCanvasPanelProps> = ({
  currentNode,
  showOutput,
  codeFullScreenFlow,
  setCodeFullScreenFlow,
  resumeDebugTaskId,
  messages,
  setMessages,
  onSaveNode,
  showError,
  workFlow,
  tempBaseId,
  setTempBaseId,
  sendingFiles,
  setSendingFiles,
  cleanTempBase,
  onSendMessage,
  sendDisabled,
  messagesWithCount,
  runningLLMNodes,
  refreshDockerImages,
  saveImage,
  setSaveImage,
  saveImageName,
  setSaveImageName,
  saveImageTag,
  setSaveImageTag,
}) => {
  const isDebugMode = resumeDebugTaskId !== "";

  const getPanelContent = () => {
    if (currentNode) {
      switch (currentNode.data.nodeType) {
        case "code":
          return (
            <FunctionNodeComponent
              refreshDockerImages={refreshDockerImages}
              saveImage={saveImage}
              setSaveImage={setSaveImage}
              saveImageName={saveImageName}
              setSaveImageName={setSaveImageName}
              saveImageTag={saveImageTag}
              setSaveImageTag={setSaveImageTag}
              saveNode={onSaveNode}
              isDebugMode={isDebugMode}
              node={currentNode}
              codeFullScreenFlow={codeFullScreenFlow}
              setCodeFullScreenFlow={setCodeFullScreenFlow}
            />
          );
        case "start":
          return (
            <StartNodeComponent
              isDebugMode={isDebugMode}
              node={currentNode}
              codeFullScreenFlow={codeFullScreenFlow}
              setCodeFullScreenFlow={setCodeFullScreenFlow}
            />
          );
        case "vlm":
          return (
            <VlmNodeComponent
              showError={showError}
              messages={messages[currentNode.id]}
              setMessages={setMessages}
              saveNode={onSaveNode}
              isDebugMode={isDebugMode}
              node={currentNode}
              codeFullScreenFlow={codeFullScreenFlow}
              setCodeFullScreenFlow={setCodeFullScreenFlow}
            />
          );
        case "condition":
          return (
            <ConditionNodeComponent
              saveNode={onSaveNode}
              isDebugMode={isDebugMode}
              node={currentNode}
              codeFullScreenFlow={codeFullScreenFlow}
              setCodeFullScreenFlow={setCodeFullScreenFlow}
            />
          );
        case "loop":
          return (
            <LoopNodeComponent
              saveNode={onSaveNode}
              isDebugMode={isDebugMode}
              node={currentNode}
              codeFullScreenFlow={codeFullScreenFlow}
              setCodeFullScreenFlow={setCodeFullScreenFlow}
            />
          );
        default:
          return <div></div>;
      }
    }

    if (showOutput) {
      return (
        <WorkflowOutputComponent
          workflow={workFlow}
          tempBaseId={tempBaseId}
          setTempBaseId={setTempBaseId}
          sendingFiles={sendingFiles}
          setSendingFiles={setSendingFiles}
          cleanTempBase={cleanTempBase}
          onSendMessage={onSendMessage}
          sendDisabled={sendDisabled}
          messagesWithCount={messagesWithCount}
          runningLLMNodes={runningLLMNodes}
          isDebugMode={isDebugMode}
          codeFullScreenFlow={codeFullScreenFlow}
          setCodeFullScreenFlow={setCodeFullScreenFlow}
        />
      );
    }

    return null;
  };

  if (!currentNode && !showOutput) {
    return null;
  }

  return (
    <div
      className={`p-2 z-10 max-h-[calc(100%-16px)] ${
        codeFullScreenFlow
          ? "w-[96%] h-[98%] fixed top-[1%] right-[2%]"
          : "w-[40%] h-[98%] absolute m-2 top-0 right-0"
      } shadow-lg rounded-3xl bg-white dark:bg-gray-900`}
    >
      {getPanelContent()}
    </div>
  );
};

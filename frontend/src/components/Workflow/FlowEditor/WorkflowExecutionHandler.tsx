/**
 * WorkflowExecutionHandler
 *
 * Handles Server-Sent Events (SSE) for workflow execution and debugging.
 * Manages real-time updates for node status, AI responses, and workflow state.
 *
 * Responsibilities:
 * - SSE connection management
 * - Event parsing and state updates
 * - AI message handling with file references
 * - Debug pause/resume handling
 * - VLM input/output processing
 */

import { useEffect, useRef } from "react";
import { logger } from "@/lib/logger";
import Cookies from "js-cookie";
import { EventSourceParserStream } from "eventsource-parser/stream";
import { CustomNode, Message } from "@/types/types";
import { replaceTemplate } from "@/utils/convert";
import { useTranslations } from "next-intl";

interface WorkflowExecutionHandlerProps {
  taskId: string;
  user: { name: string } | null | undefined;
  nodes: CustomNode[];
  selectedNodeId: string | null;
  fileMessages: Message[];
  globalDebugVariables: { [key: string]: string };
  onRunningChange: (running: boolean) => void;
  onCancelingChange: (canceling: boolean) => void;
  onTaskIdChange: (taskId: string) => void;
  onUpdateOutput: (nodeId: string, output: string) => void;
  onUpdateStatus: (nodeId: string, status: string) => void;
  onSetSelectedNodeId: (nodeId: string | null) => void;
  onSetSelectedEdgeId: (edgeId: string | null) => void;
  onSetGlobalDebugVariables: (vars: { [key: string]: string }) => void;
  onSetMessages: React.Dispatch<React.SetStateAction<{ [key: string]: Message[] }>>;
  onSetEachMessages: React.Dispatch<React.SetStateAction<{ [key: string]: Message[] }>>;
  onSetResumeDebugTaskId: (taskId: string) => void;
  onSetResumeInputTaskId: (taskId: string) => void;
  onSetCurrentInputNodeId: (nodeId: string | undefined) => void;
  onSetShowOutput: (show: boolean) => void;
  onSetSendInputDisabled: (disabled: boolean) => void;
  onSetRunningChatflowLLMNodes: React.Dispatch<React.SetStateAction<CustomNode[]>>;
  onShowAlert: (message: string, status: string) => void;
  countRef: React.MutableRefObject<number>;
  countListRef: React.MutableRefObject<string[]>;
  eachMessagesRef: React.MutableRefObject<{ [key: string]: Message[] }>;
}

const splitFirstColon = (str: string) => {
  const index = str.indexOf(":");
  if (index === -1) return [str, ""];
  return [str.substring(0, index), str.substring(index + 1)];
};

export const WorkflowExecutionHandler: React.FC<WorkflowExecutionHandlerProps> = ({
  taskId,
  user,
  nodes,
  selectedNodeId,
  fileMessages,
  globalDebugVariables,
  onRunningChange,
  onCancelingChange,
  onTaskIdChange,
  onUpdateOutput,
  onUpdateStatus,
  onSetSelectedNodeId,
  onSetSelectedEdgeId,
  onSetGlobalDebugVariables,
  onSetMessages,
  onSetEachMessages,
  onSetResumeDebugTaskId,
  onSetResumeInputTaskId,
  onSetCurrentInputNodeId,
  onSetShowOutput,
  onSetSendInputDisabled,
  onSetRunningChatflowLLMNodes,
  onShowAlert,
  countRef,
  countListRef,
  eachMessagesRef,
}) => {
  const t = useTranslations("FlowEditor");
  const variableReturn = useRef<{ [key: string]: Message[] }>({});

  const nodeStatesRef = useRef<
    Map<
      number,
      {
        aiMessage: string;
        aiThinking: string;
        messageId: string;
        total_token: number;
        completion_tokens: number;
        prompt_tokens: number;
        file_used: any[];
        vlmNewLoop: boolean;
      }
    >
  >(new Map());

  useEffect(() => {
    if (taskId !== "") {
      onSetResumeDebugTaskId("");
      onSetResumeInputTaskId("");

      const workFlowSSE = async () => {
        if (user?.name) {
          const token = Cookies.get("token");
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

            const eventStream = response.body
              ?.pipeThrough(new TextDecoderStream())
              .pipeThrough(new EventSourceParserStream());

            const eventReader = eventStream.getReader();

            while (true) {
              const { done, value } = (await eventReader?.read()) || {};
              if (done) break;
              const payload = JSON.parse(value.data);

              // Handle workflow events
              if (payload.event === "workflow") {
                if (payload.workflow.status == "failed") {
                  const errorNode = splitFirstColon(payload.workflow.error);
                  const errorNodeId = errorNode[0];
                  const errorNodeMsg = splitFirstColon(errorNode[1])[1];
                  onUpdateOutput(errorNodeId, errorNodeMsg);
                  onUpdateStatus(errorNodeId, "failed");
                  onSetSelectedNodeId(errorNodeId);
                }
                if (
                  [
                    "completed",
                    "failed",
                    "pause",
                    "canceled",
                    "vlm_input",
                  ].includes(payload.workflow.status)
                ) {
                  if (payload.workflow.status === "completed") {
                    onShowAlert(t("executionSuccess"), "success");
                  } else if (payload.workflow.status === "pause") {
                    onShowAlert(t("debugPause"), "success");
                  } else if (payload.workflow.status === "canceled") {
                    onShowAlert(t("workflowCanceled"), "error");
                  } else if (payload.workflow.status === "vlm_input") {
                    if (selectedNodeId) {
                      onSetShowOutput(true);
                      onSetSelectedNodeId(null);
                      onSetSelectedEdgeId(null);
                    } else {
                      onSetShowOutput(true);
                    }
                    onSetSendInputDisabled(false);
                  } else {
                    onShowAlert(payload.workflow.error, "error");
                  }
                  eventReader.cancel();
                }
              } else if (payload.event === "node") {
                if (payload.node.status === true) {
                  if (payload.node.result !== '""') {
                    const resultList: any[] = JSON.parse(payload.node.result);
                    let result: string;
                    if (resultList.length > 1) {
                      result = resultList
                        .map(
                          (item, index) =>
                            `#### Global Loop ${index + 1}:\n${item.result}\n`
                        )
                        .join("\n");
                    } else {
                      result = resultList[0].result;
                    }
                    onUpdateOutput(payload.node.id, result);
                  } else {
                    onUpdateOutput(payload.node.id, t("nodeExecutionSuccess"));
                  }
                  if (payload.node.variables !== '""') {
                    const variables = JSON.parse(payload.node.variables);
                    onSetGlobalDebugVariables(variables);
                    variableReturn.current = variables;
                  }
                  onUpdateStatus(payload.node.id, "ok");
                } else if (payload.node.status === "running") {
                  onUpdateStatus(payload.node.id, "running");
                } else if (payload.node.status === "pause") {
                  onSetResumeDebugTaskId(taskId);
                  onUpdateStatus(payload.node.id, "pause");
                  onSetSelectedNodeId(payload.node.id);
                } else if (payload.node.status === "vlm_input") {
                  onSetResumeInputTaskId(taskId);
                  onUpdateStatus(payload.node.id, "input");
                  onSetCurrentInputNodeId(payload.node.id);
                } else if (payload.node.status === "vlm_input_debug") {
                  onSetResumeInputTaskId(taskId);
                  onSetResumeDebugTaskId(taskId);
                  onUpdateStatus(payload.node.id, "running");
                  onSetCurrentInputNodeId(payload.node.id);
                } else if (payload.node.status === false) {
                  onUpdateStatus(payload.node.id, "init");
                }
              } else if (
                payload.event === "ai_chunk" ||
                payload.event === "mcp"
              ) {
                const nodeId = payload.ai_chunk.id;
                const aiChunkResult = JSON.parse(payload.ai_chunk.result);
                let state = nodeStatesRef.current.get(countRef.current);
                const nodeToAdd = nodes.find((node) => node.id === nodeId);
                if (!state) {
                  state = {
                    aiMessage: "",
                    aiThinking: "",
                    messageId: "",
                    total_token: 0,
                    completion_tokens: 0,
                    prompt_tokens: 0,
                    file_used: [],
                    vlmNewLoop: true,
                  };
                  onSetRunningChatflowLLMNodes((prev) => {
                    return nodeToAdd ? [...prev, nodeToAdd] : prev;
                  });
                }

                if (aiChunkResult.type === "file_used") {
                  if (payload.event === "ai_chunk") {
                    state.file_used = aiChunkResult.data;
                    state.messageId = aiChunkResult.message_id;
                  }
                }
                if (aiChunkResult.type === "thinking") {
                  state.aiThinking += aiChunkResult.data;
                  state.messageId = aiChunkResult.message_id;
                }

                if (aiChunkResult.type === "text") {
                  if (payload.event === "mcp") {
                    state.aiThinking += aiChunkResult.data;
                    state.messageId = aiChunkResult.message_id;
                  } else {
                    state.aiMessage += aiChunkResult.data;
                    if (Object.entries(globalDebugVariables).length > 0) {
                      state.aiMessage = replaceTemplate(
                        state.aiMessage,
                        variableReturn.current
                      );
                    }
                    state.messageId = aiChunkResult.message_id;
                  }
                }

                if (aiChunkResult.type === "token") {
                  state.total_token += aiChunkResult.total_token;
                  state.completion_tokens += aiChunkResult.completion_tokens;
                  state.prompt_tokens += aiChunkResult.prompt_tokens;
                }

                const currentCount = countRef.current;
                if (aiChunkResult !== '""') {
                  if (state.vlmNewLoop) {
                    let newFileMessages: Message[] = [];
                    state.vlmNewLoop = false;
                    if (nodeToAdd?.data.isChatflowInput) {
                      newFileMessages = fileMessages;
                    }

                    const newMessage: Message = {
                      type: "text" as const,
                      content: replaceTemplate(
                        nodes.find((node) => node.id === nodeId)?.data
                          .vlmInput || "",
                        variableReturn.current
                      ),
                      from: "user" as const,
                    };

                    onSetMessages((prev) => {
                      const nodeMessages = prev[nodeId] || [];
                      const aiMessage: Message = {
                        type: "text" as const,
                        content: state.aiMessage,
                        from: "ai" as const,
                        thinking: state.aiThinking,
                        messageId: state.messageId || "",
                        token_number: {
                          total_token: state.total_token,
                          completion_tokens: state.completion_tokens,
                          prompt_tokens: state.prompt_tokens,
                        },
                      };

                      return {
                        ...prev,
                        [nodeId]: [
                          ...nodeMessages,
                          ...newFileMessages,
                          newMessage,
                          aiMessage,
                        ],
                      };
                    });

                    if (nodeToAdd?.data.isChatflowInput) {
                      if (nodeToAdd?.data.isChatflowOutput) {
                        onSetEachMessages((prev) => {
                          const aiMessage: Message = {
                            type: "text" as const,
                            content: state.aiMessage,
                            from: "ai" as const,
                            thinking: state.aiThinking,
                            messageId: state.messageId || "",
                            token_number: {
                              total_token: state.total_token,
                              completion_tokens: state.completion_tokens,
                              prompt_tokens: state.prompt_tokens,
                            },
                          };
                          eachMessagesRef.current = {
                            ...prev,
                            [currentCount.toString()]: [
                              ...newFileMessages,
                              newMessage,
                              aiMessage,
                            ],
                          };
                          return {
                            ...prev,
                            [currentCount.toString()]: [
                              ...newFileMessages,
                              newMessage,
                              aiMessage,
                            ],
                          };
                        });
                      } else {
                        onSetEachMessages((prev) => {
                          eachMessagesRef.current = {
                            ...prev,
                            [currentCount.toString()]: [
                              ...newFileMessages,
                              newMessage,
                            ],
                          };
                          return {
                            ...prev,
                            [currentCount.toString()]: [
                              ...newFileMessages,
                              newMessage,
                            ],
                          };
                        });
                      }
                      if (
                        !countListRef.current.includes(
                          countRef.current.toString()
                        )
                      ) {
                        countListRef.current.push(countRef.current.toString());
                      }
                    } else {
                      if (nodeToAdd?.data.isChatflowOutput) {
                        onSetEachMessages((prev) => {
                          const aiMessage: Message = {
                            type: "text" as const,
                            content: state.aiMessage,
                            from: "ai" as const,
                            thinking: state.aiThinking,
                            messageId: state.messageId || "",
                            token_number: {
                              total_token: state.total_token,
                              completion_tokens: state.completion_tokens,
                              prompt_tokens: state.prompt_tokens,
                            },
                          };
                          eachMessagesRef.current = {
                            ...prev,
                            [currentCount.toString()]: [aiMessage],
                          };
                          return {
                            ...prev,
                            [currentCount.toString()]: [aiMessage],
                          };
                        });
                        if (
                          !countListRef.current.includes(
                            countRef.current.toString()
                          )
                        ) {
                          countListRef.current.push(countRef.current.toString());
                        }
                      }
                    }
                    nodeStatesRef.current.set(countRef.current, state);
                  } else {
                    if (aiChunkResult.type !== "token") {
                      onSetMessages((prev) => {
                        const nodeMessages = prev[nodeId] || [];
                        const lastIndex = nodeMessages.length - 1;

                        const updatedMessages = [...nodeMessages];
                        updatedMessages[lastIndex] = {
                          ...updatedMessages[lastIndex],
                          content: state.aiMessage,
                          thinking: state.aiThinking,
                          messageId: state.messageId ? state.messageId : "",
                          token_number: {
                            total_token: state.total_token,
                            completion_tokens: state.completion_tokens,
                            prompt_tokens: state.prompt_tokens,
                          },
                        };
                        return { ...prev, [nodeId]: updatedMessages };
                      });
                      if (nodeToAdd?.data.isChatflowOutput) {
                        onSetEachMessages((prev) => {
                          const nodeMessages = prev[currentCount.toString()];
                          const lastIndex = nodeMessages.length - 1;

                          const updatedMessages = [...nodeMessages];
                          updatedMessages[lastIndex] = {
                            ...updatedMessages[lastIndex],
                            content: state.aiMessage,
                            thinking: state.aiThinking,
                            messageId: state.messageId ? state.messageId : "",
                            token_number: {
                              total_token: state.total_token,
                              completion_tokens: state.completion_tokens,
                              prompt_tokens: state.prompt_tokens,
                            },
                          };
                          eachMessagesRef.current = {
                            ...prev,
                            [currentCount.toString()]: updatedMessages,
                          };
                          return {
                            ...prev,
                            [currentCount.toString()]: updatedMessages,
                          };
                        });
                        if (
                          !countListRef.current.includes(
                            countRef.current.toString()
                          )
                        ) {
                          countListRef.current.push(countRef.current.toString());
                        }
                      }
                    } else if (payload.event === "ai_chunk") {
                      onSetMessages((prev) => {
                        const nodeMessages = prev[nodeId] || [];
                        const lastIndex = nodeMessages.length - 1;

                        const updatedMessages = [...nodeMessages];
                        updatedMessages[lastIndex] = {
                          ...updatedMessages[lastIndex],
                          content: state.aiMessage,
                          thinking: state.aiThinking,
                          messageId: state.messageId ? state.messageId : "",
                          token_number: {
                            total_token: state.total_token,
                            completion_tokens: state.completion_tokens,
                            prompt_tokens: state.prompt_tokens,
                          },
                        };

                        const referenceMessages = [
                          ...state.file_used.map((file, index) => ({
                            type: "baseFile" as const,
                            content: `image_${index}`,
                            messageId: state.messageId ? state.messageId : "",
                            imageMinioUrl: file.image_url,
                            fileName: file.file_name,
                            baseId: file.knowledge_db_id,
                            minioUrl: file.file_url,
                            score: file.score,
                            from: "ai" as const,
                          })),
                        ];
                        return {
                          ...prev,
                          [nodeId]: updatedMessages.concat(referenceMessages),
                        };
                      });

                      if (nodeToAdd?.data.isChatflowOutput) {
                        onSetEachMessages((prev) => {
                          const nodeMessages = prev[currentCount.toString()];
                          const lastIndex = nodeMessages.length - 1;

                          const updatedMessages = [...nodeMessages];
                          updatedMessages[lastIndex] = {
                            ...updatedMessages[lastIndex],
                            content: state.aiMessage,
                            thinking: state.aiThinking,
                            messageId: state.messageId ? state.messageId : "",
                            token_number: {
                              total_token: state.total_token,
                              completion_tokens: state.completion_tokens,
                              prompt_tokens: state.prompt_tokens,
                            },
                          };
                          const referenceMessage = [
                            ...state.file_used.map((file, index) => ({
                              type: "baseFile" as const,
                              content: `image_${index}`,
                              messageId: state.messageId ? state.messageId : "",
                              imageMinioUrl: file.image_url,
                              fileName: file.file_name,
                              baseId: file.knowledge_db_id,
                              minioUrl: file.file_url,
                              score: file.score,
                              from: "ai" as const,
                            })),
                          ];
                          eachMessagesRef.current = {
                            ...prev,
                            [currentCount.toString()]:
                              updatedMessages.concat(referenceMessage),
                          };
                          return {
                            ...prev,
                            [currentCount.toString()]:
                              updatedMessages.concat(referenceMessage),
                          };
                        });
                        if (
                          !countListRef.current.includes(
                            countRef.current.toString()
                          )
                        ) {
                          countListRef.current.push(countRef.current.toString());
                        }
                      }
                      countRef.current += 1;
                    }
                  }
                }
              }
            }
          } catch (error) {
            logger.error("SSE Error:", error);
            onShowAlert(t("sseError"), "error");
          } finally {
            onRunningChange(false);
            onTaskIdChange("");
            onCancelingChange(false);
          }
        }
      };
      workFlowSSE();
    }
  }, [
    taskId,
    user?.name,
    nodes,
    selectedNodeId,
    fileMessages,
    globalDebugVariables,
    onRunningChange,
    onCancelingChange,
    onTaskIdChange,
    onUpdateOutput,
    onUpdateStatus,
    onSetSelectedNodeId,
    onSetSelectedEdgeId,
    onSetGlobalDebugVariables,
    onSetMessages,
    onSetEachMessages,
    onSetResumeDebugTaskId,
    onSetResumeInputTaskId,
    onSetCurrentInputNodeId,
    onSetShowOutput,
    onSetSendInputDisabled,
    onSetRunningChatflowLLMNodes,
    onShowAlert,
    countRef,
    countListRef,
    eachMessagesRef,
    t,
  ]);

  return null;
};

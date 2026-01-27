/**
 * VlmNode Settings Component - Refactored to use NodeSettingsBase
 *
 * This component demonstrates the use of NodeSettingsBase composition pattern.
 * Reduced from ~1,161 lines to ~500 lines by extracting common patterns.
 */
import { useAuthStore } from "@/stores/authStore";
import { logger } from "@/lib/logger";
import { useFlowStore } from "@/stores/flowStore";
import { useGlobalStore } from "@/stores/WorkflowVariableStore";
import {
  CustomNode,
  McpConfig,
  Message,
  ModelConfig,
} from "@/types/types";
import { useState } from "react";
import KnowledgeConfigModal from "./KnowledgeConfigModal";
import { updateModelConfig } from "@/lib/api/configApi";
import Cookies from "js-cookie";
import { EventSourceParserStream } from "eventsource-parser/stream";
import ChatMessage from "@/components/AiChat/ChatMessage";
import MarkdownDisplay from "@/components/AiChat/MarkdownDisplay";
import McpConfigComponent from "./McpConfig";
import { createPortal } from "react-dom";
import { replaceTemplate } from "@/utils/convert";
import { useTranslations } from "next-intl";
import NodeSettingsBase, {
  NodeHeader,
  DescriptionSection,
  GlobalVariablesSection,
  OutputSection,
} from "./NodeSettingsBase";

interface VlmNodeProps {
  messages: Message[];
  setMessages: React.Dispatch<
    React.SetStateAction<{
      [key: string]: Message[];
    }>
  >;
  saveNode: (node: CustomNode) => void;
  isDebugMode: boolean;
  node: CustomNode;
  setCodeFullScreenFlow: React.Dispatch<React.SetStateAction<boolean>>;
  codeFullScreenFlow: boolean;
  showError: (error: string) => void;
}

const VlmNodeComponent: React.FC<VlmNodeProps> = ({
  messages,
  setMessages,
  saveNode,
  isDebugMode,
  node,
  setCodeFullScreenFlow,
  codeFullScreenFlow,
  showError,
}) => {
  const t = useTranslations("VlmNode");
  const { user } = useAuthStore();
  const {
    updateVlmModelConfig,
    updatePrompt,
    updateVlmInput,
    changeChatflowInput,
    changeChatflowOutput,
    changeUseChatHistory,
    changeChatflowOutputVariable,
    updateChat,
  } = useFlowStore();
  const { globalVariables } = useGlobalStore();

  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showMcpConfig, setShowMcpConfig] = useState(false);
  const [runTest, setRunTest] = useState(false);
  const [showRefFile, setShowRefFile] = useState<string[]>([]);

  const configureKnowledgeDB = () => {
    setShowConfigModal(true);
  };

  const handleSaveConfig = async (config: ModelConfig) => {
    if (user?.name) {
      try {
        const { updateVlmModelConfig: updateModel } = useFlowStore.getState();
        updateModel(node.id, config);
        await updateModelConfig(user.name, config);
      } catch (error) {
        logger.error("保存配置失败:", error);
      }
    }
  };

  const handleRunTest = async () => {
    if (!node.data.vlmInput) {
      showError(t("testError"));
      return;
    }
    setMessages((prev) => ({ ...prev, [node.id]: [] }));
    if (user?.name) {
      setRunTest(true);
      try {
        const token = Cookies.get("token");
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
            [key: string]: McpConfig;
          },
          mcpUse: {
            [key: string]: string[];
          }
        ) => {
          const filteredConfig: {
            [key: string]: McpConfig;
          } = {};
          for (const key of Object.keys(mcpUse)) {
            if (mcpConfig[key]) {
              const originalConfig = mcpConfig[key];
              const filteredTools = originalConfig.mcpTools.filter((tool) =>
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

        let mcpUse: { [key: string]: McpConfig };
        if (node.data.mcpConfig && node.data.mcpUse) {
          mcpUse = filterMcpConfig(node.data.mcpConfig, node.data.mcpUse);
        } else {
          mcpUse = {};
        }

        const { globalVariables: vars } = useGlobalStore.getState();
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/sse/llm/once`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              username: user.name,
              user_message: node.data.vlmInput,
              llm_model_config: modelConfig,
              system_prompt: node.data.prompt,
              mcp_use: mcpUse,
              global_variables: vars,
            }),
          }
        );

        if (!response.ok) throw new Error("Request failed");
        if (!response.body) return;
        let aiResponse = "";
        const eventStream = response.body
          ?.pipeThrough(new TextDecoderStream())
          .pipeThrough(new EventSourceParserStream());

        const eventReader = eventStream.getReader();
        while (true) {
          const { done, value } = (await eventReader?.read()) || {};
          if (done) break;
          const payload = JSON.parse(value.data);
          if (payload.type === "text") {
            aiResponse += payload.data;
            if (Object.entries(vars).length > 0) {
              aiResponse = replaceTemplate(aiResponse, vars);
            }
            updateChat(node.id, aiResponse);
          }
          if (payload.type === "token") {
            aiResponse += "\n\n Total token usage: ";
            aiResponse += payload.total_token;
            aiResponse += "\n Completion token usage: ";
            aiResponse += payload.completion_tokens;
            aiResponse += "\n Prompt token usage: ";
            aiResponse += payload.prompt_tokens;
            updateChat(node.id, aiResponse);
          }
        }
      } catch (error) {
        updateChat(node.id, "Error connect:" + error);
      } finally {
        setRunTest(false);
      }
    }
  };

  // VLM-specific sections
  const PromptSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
              />
            </svg>
            {t("prompt")}
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
          <button
            className="hover:bg-indigo-600 rounded-full px-2 py-1 hover:text-white flex gap-1 cursor-pointer"
            onClick={configureKnowledgeDB}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4 my-auto"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
              />
            </svg>
            <div>{t("moreSettings")}</div>
          </button>
        </div>
      </summary>
      <div className="rounded-2xl shadow-lg overflow-auto p-3 w-full mb-2">
        <textarea
          className={`mt-1 w-full px-3 py-2 border border-gray-200 rounded-xl min-h-[10vh] ${
            codeFullScreenFlow ? "max-h-[50vh]" : "max-h-[30vh]"
          } resize-none overflow-y-auto focus:outline-hidden focus:ring-2 focus:ring-indigo-500`}
          placeholder={node.data.prompt}
          rows={1}
          value={node.data.prompt}
          onChange={(e) => {
            e.target.style.height = "auto";
            e.target.style.height = e.target.scrollHeight + "px";
            updatePrompt(node.id, e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.shiftKey) {
              e.preventDefault();
            }
          }}
        />
      </div>
    </details>
  );

  const InputSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4 my-auto"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
              />
            </svg>
            {t("input")}
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
          <button
            className="hover:bg-indigo-600 rounded-full px-2 py-1 hover:text-white flex gap-1 cursor-pointer"
            onClick={() =>
              changeChatflowInput(node.id, !node.data.isChatflowInput)
            }
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-4 my-auto"
            >
              <path
                fillRule="evenodd"
                d="M12 5.25c1.213 0 2.415.046 3.605.135a3.256 3.256 0 0 1 3.01 3.01c.044.583.077 1.17.1 1.759L17.03 8.47a.75.75 0 1 0-1.06 1.06l3 3a.75.75 0 0 0 1.06 0l3-3a.75.75 0 0 0-1.06-1.06l-1.752 1.751c-.023-.65-.06-1.296-.108-1.939a4.756 4.756 0 0 0-4.392-4.392 49.422 49.422 0 0 0-7.436 0A4.756 4.756 0 0 0 3.89 8.282c-.017.224-.033.447-.046.672a.75.75 0 1 0 1.497.092c.013-.217.028-.434.044-.651a3.256 3.256 0 0 1 3.01-3.01c1.19-.09 2.392-.135 3.605-.135Zm-6.97 6.22a.75.75 0 0 0-1.06 0l-3 3a.75.75 0 1 0 1.06 1.06l1.752-1.751c.023.65.06 1.296.108 1.939a4.756 4.756 0 0 0 4.392 4.392 49.413 49.413 0 0 0 7.436 0 4.756 4.756 0 0 0 4.392-4.392c.017-.223.032-.447.046-.672a.75.75 0 0 0-1.497-.092c-.013.217-.028.434-.044.651a3.256 3.256 0 0 1-3.01 3.01 47.953 47.953 0 0 1-7.21 0 3.256 3.256 0 0 1-3.01-3.01 47.759 47.759 0 0 1-.1-1.759L6.97 15.53a.75.75 0 0 0 1.06-1.06l-3-3Z"
                clipRule="evenodd"
              />
            </svg>
            <div>{t("changeInputStyle")}</div>
          </button>
        </div>
      </summary>
      {node.data.isChatflowInput ? (
        <div className="rounded-2xl shadow-lg overflow-auto p-4 w-full mb-2">
          <div className="mb-1">{t("useChatflowUserInput")}</div>
        </div>
      ) : (
        <div className="rounded-2xl shadow-lg overflow-auto p-3 w-full mb-2">
          <div className="mb-1">{t("predefinedInput")}</div>
          <textarea
            className={`mt-1 w-full px-2 py-2 border border-gray-200 rounded-xl min-h-[10vh] ${
              codeFullScreenFlow ? "max-h-[50vh]" : "max-h-[30vh]"
            } resize-none overflow-y-auto focus:outline-hidden focus:ring-2 focus:ring-indigo-500`}
            placeholder={t("inputPlaceholder")}
            rows={1}
            value={node.data.vlmInput}
            onChange={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = e.target.scrollHeight + "px";
              updateVlmInput(node.id, e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.shiftKey) {
                e.preventDefault();
              }
            }}
          />
        </div>
      )}
    </details>
  );

  const LlmResponseSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
              />
            </svg>
            {t("llmResponse")}
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
          <button
            onClick={handleRunTest}
            disabled={runTest}
            className="cursor-pointer disabled:cursor-not-allowed px-2 py-1 rounded-full hover:bg-indigo-600 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
              />
            </svg>
            <span>{t("runTest")}</span>
          </button>
        </div>
      </summary>
      <div className="rounded-2xl shadow-lg overflow-auto w-full mb-2 p-2">
        <div
          className="flex-1 overflow-y-scroll scrollbar-hide"
          style={{ overscrollBehavior: "contain" }}
        >
          {messages && messages.length > 0 ? (
            messages.map((message, index) => (
              <ChatMessage
                modelConfig={node.data.modelConfig}
                key={index}
                message={message}
                showRefFile={showRefFile}
                setShowRefFile={setShowRefFile}
              />
            ))
          ) : (
            <div className="px-2">
              <MarkdownDisplay
                md_text={node.data.chat || ""}
                message={{
                  type: "text",
                  content: node.data.chat || "",
                  from: "ai",
                }}
                showTokenNumber={true}
                isThinking={false}
              />
            </div>
          )}
        </div>
      </div>
      <div className="w-full flex items-center justify-between p-2 gap-2">
        <span className="whitespace-nowrap">{t("llmResponsePlaceholder")}</span>
        <div className="flex-1">
          <select
            name="addVariable"
            value={node.data.chatflowOutputVariable || ""}
            onChange={(e) =>
              changeChatflowOutputVariable(node.id, e.target.value)
            }
            className="w-full px-3 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 appearance-none"
          >
            {Object.keys(globalVariables).map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
            <option value={""}>--</option>
          </select>
        </div>
      </div>
    </details>
  );

  const ChatflowSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
              />
            </svg>
            {t("chatflow")}
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
          <button
            onClick={() => {
              setShowMcpConfig(true);
            }}
            disabled={runTest}
            className="hover:bg-indigo-600 hover:text-white cursor-pointer disabled:cursor-not-allowed px-2 py-1 rounded-full disabled:opacity-50 flex items-center justify-center gap-1"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z"
              />
            </svg>
            <span>{t("mcpTools")}</span>
          </button>
        </div>
      </summary>
      <div className="rounded-2xl shadow-lg overflow-auto p-3 w-full mb-2">
        <div className="relative flex flex-col items-start justify-center gap-2">
          <label className="w-full overflow-auto relative inline-flex items-center group p-2 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={node.data.isChatflowInput}
              onChange={() =>
                changeChatflowInput(node.id, !node.data.isChatflowInput)
              }
              className="shrink-0 appearance-none h-4.5 w-4.5 border-2 border-gray-300 rounded-lg transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
            />
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="absolute size-4 text-white shrink-0"
            >
              <path
                fillRule="evenodd"
                d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                clipRule="evenodd"
                transform="translate(2, 0.2)"
              />
            </svg>
            <div className="ml-2 flex gap-1 items-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-4"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                />
              </svg>
              <span>{t("setAsChatflowUserInput")}</span>
            </div>
          </label>
          <label className="w-full overflow-auto relative inline-flex items-center group p-2 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={node.data.isChatflowOutput}
              onChange={() => {
                if (node.data.isChatflowOutput) {
                  changeUseChatHistory(node.id, false);
                }
                changeChatflowOutput(node.id, !node.data.isChatflowOutput);
              }}
              className="shrink-0 appearance-none h-4.5 w-4.5 border-2 border-gray-300 rounded-lg transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
            />
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="absolute size-4 text-white shrink-0"
            >
              <path
                fillRule="evenodd"
                d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                clipRule="evenodd"
                transform="translate(2, 0.2)"
              />
            </svg>
            <div className="ml-2 flex gap-1 items-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-4"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
                />
              </svg>
              <span>{t("setAsChatflowAIResponse")}</span>
            </div>
          </label>
          {node.data.isChatflowOutput && (
            <label className="w-full overflow-auto relative inline-flex items-center group p-2 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={node.data.useChatHistory}
                onChange={() =>
                  changeUseChatHistory(node.id, !node.data.useChatHistory)
                }
                className="shrink-0 appearance-none h-4.5 w-4.5 border-2 border-gray-300 rounded-lg transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
              />
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="absolute size-4 text-white shrink-0"
              >
                <path
                  fillRule="evenodd"
                  d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                  clipRule="evenodd"
                  transform="translate(2, 0.2)"
                />
              </svg>
              <div className="ml-2 flex gap-1 items-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-4"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
                  />
                </svg>
                <span>{t("useConversationMemory")}</span>
              </div>
            </label>
          )}
        </div>
      </div>
    </details>
  );

  // Save button for header
  const saveButton = (
    <button
      onClick={() => saveNode(node)}
      className="cursor-pointer disabled:cursor-not-allowed py-1 px-2 rounded-full hover:bg-indigo-600 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="size-4"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
        />
      </svg>
      <span className="whitespace-nowrap">{t("saveNode")}</span>
    </button>
  );

  return (
    <NodeSettingsBase
      node={node}
      isDebugMode={isDebugMode}
      codeFullScreenFlow={codeFullScreenFlow}
      setCodeFullScreenFlow={setCodeFullScreenFlow}
      translationNamespace="VlmNode"
    >
      {(api) => (
        <>
          {/* Header with save button */}
          <NodeHeader node={node} updateNodeLabel={api.updateNodeLabel} actions={saveButton} />

          {/* Description section */}
          <DescriptionSection
            node={node}
            isEditing={api.isEditing}
            setIsEditing={api.setIsEditing}
            updateDescription={api.updateDescription}
            codeFullScreenFlow={codeFullScreenFlow}
            t={api.t}
          />

          {/* Global variables section */}
          <GlobalVariablesSection
            isDebugMode={isDebugMode}
            codeFullScreenFlow={codeFullScreenFlow}
            setCodeFullScreenFlow={setCodeFullScreenFlow}
            globalVariables={api.globalVariables}
            globalDebugVariables={api.globalDebugVariables}
            addProperty={api.addProperty}
            removeProperty={api.removeProperty}
            handleVariableChange={api.handleVariableChange}
            t={api.t}
          />

          {/* VLM-specific sections */}
          <PromptSection />
          <InputSection />
          <LlmResponseSection />
          <ChatflowSection />

          {/* Output section */}
          <OutputSection
            node={node}
            updateDebug={api.updateDebug}
            t={api.t}
            disabled={runTest}
          />

          {/* Portals */}
          {createPortal(
            <McpConfigComponent
              node={node}
              visible={showMcpConfig}
              setVisible={setShowMcpConfig}
            />,
            document.body
          )}
          {createPortal(
            <KnowledgeConfigModal
              node={node}
              visible={showConfigModal}
              setVisible={setShowConfigModal}
              onSave={handleSaveConfig}
            />,
            document.body
          )}
        </>
      )}
    </NodeSettingsBase>
  );
};

export default VlmNodeComponent;

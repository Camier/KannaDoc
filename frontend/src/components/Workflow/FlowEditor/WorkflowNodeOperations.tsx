/**
 * WorkflowNodeOperations
 *
 * Handles node and edge operations including creation, connection, and deletion.
 * Manages node type selection and custom node handling.
 *
 * Responsibilities:
 * - Add new nodes of various types
 * - Add custom nodes
 * - Handle node connections
 * - Validate node creation
 * - Fetch model configs for VLM nodes
 */

import { useCallback } from "react";
import { logger } from "@/lib/logger";
import { v4 as uuidv4 } from "uuid";
import { CustomNode, NodeTypeKey, KnowledgeBase, ModelConfig } from "@/types/types";
import { getCustomNodes, deleteCustomNodes } from "@/lib/api/workflowApi";
import { getAllKnowledgeBase } from "@/lib/api/knowledgeBaseApi";
import { getAllModelConfig } from "@/lib/api/configApi";
import { useTranslations } from "next-intl";

interface WorkflowNodeOperationsProps {
  user: { name: string } | null | undefined;
  customNodes: { [key: string]: CustomNode };
  setCustomNodes: (nodes: { [key: string]: CustomNode }) => void;
  nodes: CustomNode[];
  setNodes: (nodes: CustomNode[]) => void;
  onUpdateVlmModelConfig: (nodeId: string, updater: (prev: any) => any) => void;
  onShowAlert: (message: string, status: string) => void;
  pushHistory: () => void;
}

const getId = (type: string): string => `node_${type}_${uuidv4()}`;

export const useWorkflowNodeOperations = ({
  user,
  customNodes,
  setCustomNodes,
  nodes,
  setNodes,
  onUpdateVlmModelConfig,
  onShowAlert,
  pushHistory,
}: WorkflowNodeOperationsProps) => {
  const t = useTranslations("FlowEditor");

  const fetchModelConfig = useCallback(
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
            scoreThreshold:
              item.score_threshold === -1 ? 10 : item.score_threshold,
            useTemperatureDefault: item.temperature === -1 ? true : false,
            useMaxLengthDefault: item.max_length === -1 ? true : false,
            useTopPDefault: item.top_P === -1 ? true : false,
            useTopKDefault: item.top_K === -1 ? true : false,
            useScoreThresholdDefault: item.score_threshold === -1 ? true : false,
          })
        );

        const selected = modelConfigsResponse.find(
          (m) => m.modelId === response.data.selected_model
        );

        if (selected) {
          const filter_select = selected.baseUsed.filter((item) =>
            bases.some((base) => base.id === item.baseId)
          );
          onUpdateVlmModelConfig(nodeId, (prev: any) => ({
            ...prev,
            ...selected,
            baseUsed: filter_select,
          }));
        }
      }
    },
    [user?.name, onUpdateVlmModelConfig]
  );

  const addNode = useCallback(
    (type: NodeTypeKey) => {
      let data: any;
      let id: string;

      if (type === "code") {
        data = {
          status: "init",
          label: t("label." + type),
          nodeType: type,
          code: 'def my_func():\n    print("Hello Layra!")\n\nmy_func()\n',
          output: t("defaultOutput"),
          pip: {},
        };
      } else if (type === "loop") {
        data = {
          status: "init",
          label: t("label." + type),
          nodeType: type,
          loopType: "count",
          maxCount: 1,
          condition: "",
          output: t("defaultOutput"),
        };
      } else if (type === "vlm") {
        data = {
          status: "init",
          label: t("label." + type),
          nodeType: type,
          output: t("vlmOutputPlaceholder"),
          prompt: "Your are a helpful assistant.",
          vlmInput: "",
          chatflowOutputVariable: "",
          isChatflowInput: false,
          isChatflowOutput: false,
          useChatHistory: false,
          chat: t("vlmChatPlaceholder"),
        };
      } else if (type === "condition") {
        data = {
          status: "init",
          label: t("label." + type),
          nodeType: type,
          output: t("defaultOutput"),
          conditions: {}
        };
      } else {
        data = {
          status: "init",
          label: t("label." + type),
          nodeType: type,
          output: t("defaultOutput"),
        };
      }

      if (type === "start") {
        if (nodes.find((node) => node.data.nodeType === "start")) {
          onShowAlert(t("startNodeExist"), "error");
          return;
        }
        id = "node_start";
      } else {
        id = getId(type);
      }

      const newNode: CustomNode = {
        id: id,
        type: "default",
        position: { x: Math.random() * 100 - 100, y: Math.random() * 100 },
        data: data,
      };
      setNodes([...nodes, newNode]);

      if (type === "vlm") {
        fetchModelConfig(id);
      }
    },
    [nodes, setNodes, fetchModelConfig, onShowAlert, t]
  );

  const addCustomNode = useCallback(
    (name: string) => {
      const type = customNodes[name].type;
      if (type) {
        const id = getId(type);
        const newNode: CustomNode = {
          id: id,
          type: customNodes[name].type,
          position: { x: Math.random() * 100 - 100, y: Math.random() * 100 },
          data: { ...customNodes[name].data, label: name },
        };
        setNodes([...nodes, newNode]);
      } else {
        alert("Node Error");
      }
    },
    [customNodes, nodes, setNodes]
  );

  const fetchAllCustomNodes = useCallback(async () => {
    if (user?.name) {
      try {
        const response = await getCustomNodes(user.name);
        const reponseNodes: { [key: string]: CustomNode } = response.data;
        setCustomNodes(reponseNodes);
      } catch (error) {
        logger.error("Error fetching custom nodes:", error);
      }
    }
  }, [user?.name, setCustomNodes]);

  const handleDeleteCustomNode = async (custom_node_name: string) => {
    if (user?.name) {
      try {
        await deleteCustomNodes(user.name, custom_node_name);
        fetchAllCustomNodes();
      } catch (error) {
        logger.error("Error deleting custom node:", error);
      }
    }
  };

  return {
    addNode,
    addCustomNode,
    fetchAllCustomNodes,
    handleDeleteCustomNode,
    fetchModelConfig,
  };
};

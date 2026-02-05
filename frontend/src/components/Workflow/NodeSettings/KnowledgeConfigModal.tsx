// components/Workflow/NodeSettings/KnowledgeConfigModal.tsx
/**
 * Knowledge Configuration Modal for Workflow Nodes
 *
 * This is a thin wrapper around KnowledgeConfigModalBase that provides:
 * - Workflow-specific state management (useFlowStore)
 * - Node-level configuration context
 * - Workflow translations
 */
import React, {
  Dispatch,
  SetStateAction,
  useEffect,
  useState,
} from "react";
import { CustomNode, ModelConfig } from "@/types/types";
import { useFlowStore } from "@/stores/flowStore";
import { useTranslations } from "next-intl";
import { useKnowledgeConfigData } from "@/components/AiChat/hooks/useKnowledgeConfigData";
import { useModelConfigActions } from "@/components/AiChat/hooks/useModelConfigActions";
import { KnowledgeConfigModalBase } from "@/components/shared/modals/KnowledgeConfigModalBase";
import { ANONYMOUS_USER } from "@/lib/constants";

interface ConfigModalProps {
  node: CustomNode;
  visible: boolean;
  setVisible: Dispatch<SetStateAction<boolean>>;
  onSave: (newModelConfig: ModelConfig) => void;
}

const KnowledgeConfigModal: React.FC<ConfigModalProps> = ({
  node,
  visible,
  setVisible,
  onSave,
}) => {
  const t = useTranslations("WorkflowKnowledgeConfigModal");
  const user = ANONYMOUS_USER;
  const { updateVlmModelConfig } = useFlowStore();

  // Get current model config from node
  const currentModelConfig = node.data.modelConfig;

  // Custom hooks for data management
  const {
    knowledgeBases,
    setKnowledgeBases,
    modelConfigs,
    setModelConfigs,
    refreshData,
  } = useKnowledgeConfigData({
    username: user?.name,
    selectedModelId: currentModelConfig?.modelId,
  });

  const { createModelConfig, deleteModelConfigById } = useModelConfigActions({
    username: user?.name,
  });

  // Refresh data when modal opens
  useEffect(() => {
    if (visible) {
      refreshData();
    }
  }, [visible, refreshData]);

  // Handle model selection change
  const handleModelChange = (value: string) => {
    const selected = modelConfigs.find((m) => m.modelId === value);
    if (selected) {
      updateVlmModelConfig(node.id, selected);
    }
  };

  const handleConfigChange = (updates: Partial<ModelConfig>) => {
    updateVlmModelConfig(node.id, (prev) => ({ ...prev, ...updates }));
  };

  const handleDeleteConfig = async (config: ModelConfig) => {
    await deleteModelConfigById(config.modelId);
  };

  const handleCreateConfig = async (newModel: ModelConfig): Promise<ModelConfig | null> => {
    const created = await createModelConfig(newModel, modelConfigs);
    if (created) {
      updateVlmModelConfig(node.id, created);
    }
    return created;
  };

  if (!currentModelConfig) return null;

  return (
    <KnowledgeConfigModalBase
      visible={visible}
      setVisible={setVisible}
      onSave={onSave}
      currentModelConfig={currentModelConfig}
      knowledgeBases={knowledgeBases}
      modelConfigs={modelConfigs}
      setKnowledgeBases={setKnowledgeBases}
      setModelConfigs={setModelConfigs}
      onModelChange={handleModelChange}
      onConfigChange={handleConfigChange}
      onDeleteConfig={handleDeleteConfig}
      onCreateConfig={handleCreateConfig}
      onRefreshData={refreshData}
      translations={{
        title: t("title"),
        addKnowledgeBase: t("addKnowledgeBase"),
        tutorials: t("tutorials"),
        chooseDB: t("chooseDB"),
        cancel: t("cancel"),
        save: t("save"),
        deleteModelConfigConfirmation: t("deleteModelConfigConfirmation"),
      }}
      showSystemPrompt={false}
    />
  );
};

export default KnowledgeConfigModal;

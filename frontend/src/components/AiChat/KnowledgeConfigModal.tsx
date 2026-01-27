// components/AiChat/KnowledgeConfigModal.tsx
/**
 * Knowledge Configuration Modal for Chat Interface
 *
 * This is a thin wrapper around KnowledgeConfigModalBase that provides:
 * - Chat-specific state management (useModelConfigStore)
 * - System prompt section (unique to chat context)
 * - Chat translations
 */
import React, {
  Dispatch,
  SetStateAction,
  useEffect,
  useState,
} from "react";
import { useAuthStore } from "@/stores/authStore";
import { ModelConfig } from "@/types/types";
import useModelConfigStore from "@/stores/configStore";
import { useTranslations } from "next-intl";
import { useKnowledgeConfigData } from "./hooks/useKnowledgeConfigData";
import { useModelConfigActions } from "./hooks/useModelConfigActions";
import { KnowledgeConfigModalBase } from "@/components/shared/modals/KnowledgeConfigModalBase";

interface ConfigModalProps {
  visible: boolean;
  setVisible: Dispatch<SetStateAction<boolean>>;
  onSave: (newModelConfig: ModelConfig) => void;
}

const KnowledgeConfigModal: React.FC<ConfigModalProps> = ({
  visible,
  setVisible,
  onSave,
}) => {
  const t = useTranslations("ChatKnowledgeConfigModal");
  const { user } = useAuthStore();
  const { modelConfig, setModelConfig } = useModelConfigStore();

  // Custom hooks for data management
  const {
    knowledgeBases,
    setKnowledgeBases,
    modelConfigs,
    setModelConfigs,
    refreshData,
  } = useKnowledgeConfigData({
    username: user?.name,
    selectedModelId: modelConfig?.modelId,
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
      setModelConfig(selected);
    }
  };

  const handleConfigChange = (updates: Partial<ModelConfig>) => {
    setModelConfig((prev) => ({ ...prev, ...updates }));
  };

  const handleDeleteConfig = async (config: ModelConfig) => {
    await deleteModelConfigById(config.modelId);
  };

  const handleCreateConfig = async (newModel: ModelConfig): Promise<ModelConfig | null> => {
    return await createModelConfig(newModel, modelConfigs);
  };

  return (
    <KnowledgeConfigModalBase
      visible={visible}
      setVisible={setVisible}
      onSave={onSave}
      currentModelConfig={modelConfig}
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
        systemPrompt: t("systemPrompt"),
        cancel: t("cancel"),
        save: t("save"),
        deleteModelConfigConfirmation: t("deleteModelConfigConfirmation"),
      }}
      showSystemPrompt={true}
    />
  );
};

export default KnowledgeConfigModal;

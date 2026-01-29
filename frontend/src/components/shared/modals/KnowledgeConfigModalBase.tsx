// components/shared/modals/KnowledgeConfigModalBase.tsx
/**
 * Unified Knowledge Configuration Modal Base
 *
 * Consolidates the common logic between chat and workflow knowledge config modals.
 * Differences are handled via props and adapter functions.
 *
 * This is a pure presentational component that receives all data and handlers
 * as props, allowing it to be reused across different state management contexts.
 */
import React, { useState } from "react";
import { KnowledgeBase, ModelConfig } from "@/types/types";
import AddLLMEngine from "@/components/AiChat/AddLLMEngine";
import ConfirmDialog from "@/components/ConfirmDialog";
import { LlmSettingsSection } from "@/components/AiChat/components/LlmSettingsSection";
import { KnowledgeBaseSelector } from "@/components/AiChat/components/KnowledgeBaseSelector";
import { AdvancedSettings } from "@/components/AiChat/components/AdvancedSettings";

// ============================================================================
// Types
// ============================================================================

export interface KnowledgeConfigModalBaseProps {
  // Visibility control
  visible: boolean;
  setVisible: (visible: boolean) => void;
  onSave: (newModelConfig: ModelConfig) => void;

  // Data
  currentModelConfig: ModelConfig | undefined;
  knowledgeBases: KnowledgeBase[];
  modelConfigs: ModelConfig[];

  // State setters
  setKnowledgeBases: React.Dispatch<React.SetStateAction<KnowledgeBase[]>>;
  setModelConfigs: React.Dispatch<React.SetStateAction<ModelConfig[]>>;

  // Handlers
  onModelChange: (value: string) => void;
  onConfigChange: (updates: Partial<ModelConfig>) => void;
  onDeleteConfig: (config: ModelConfig) => void;
  onCreateConfig: (newModel: ModelConfig) => Promise<ModelConfig | null>;
  onRefreshData: () => void;

  // Translations
  translations: {
    title: string;
    addKnowledgeBase: string;
    tutorials: string;
    chooseDB: string;
    systemPrompt?: string;
    cancel: string;
    save: string;
    deleteModelConfigConfirmation: string;
  };

  // Optional: System prompt section (only for chat context)
  showSystemPrompt?: boolean;
}

interface ModalHeaderProps {
  title: string;
  addKnowledgeBaseLabel: string;
  tutorialsLabel: string;
}

interface ModalActionsProps {
  onCancel: () => void;
  onSave: () => void;
  cancelLabel: string;
  saveLabel: string;
}

// ============================================================================
// Sub-components (shared UI structure)
// ============================================================================

export const ModalHeader: React.FC<ModalHeaderProps> = ({
  title,
  addKnowledgeBaseLabel,
  tutorialsLabel,
}) => (
  <>
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="2.5"
          stroke="currentColor"
          className="size-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
          />
        </svg>
        <span className="text-lg font-medium">{title}</span>
      </div>
      <a
        href="/knowledge-base"
        className="px-3 py-2 text-indigo-500 hover:text-indigo-700 text-base flex items-center cursor-pointer"
        target="_blank"
        rel="noopener noreferrer"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5 mr-1"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        {addKnowledgeBaseLabel}
      </a>
    </div>

    <p className="text-gray-500 text-sm mb-2 flex">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="2"
        stroke="currentColor"
        className="size-4 mr-[2px] my-auto"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
        />
      </svg>
      {tutorialsLabel}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth="1.5"
        stroke="currentColor"
        className="mx-1 size-5 my-auto"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
        />
      </svg>
    </p>
  </>
);

export const ModalActions: React.FC<ModalActionsProps> = ({
  onCancel,
  onSave,
  cancelLabel,
  saveLabel,
}) => (
  <div className="mt-2 flex justify-end gap-2 pt-2">
    <button
      onClick={onCancel}
      className="px-4 py-2 text-gray-700 border border-gray-300 rounded-full hover:bg-gray-100 cursor-pointer"
    >
      {cancelLabel}
    </button>
    <button
      onClick={onSave}
      className="px-4 py-2 bg-indigo-500 text-white rounded-full hover:bg-indigo-700 cursor-pointer"
    >
      {saveLabel}
    </button>
  </div>
);

// ============================================================================
// Main Modal Component
// ============================================================================

export const KnowledgeConfigModalBase: React.FC<KnowledgeConfigModalBaseProps> = ({
  visible,
  setVisible,
  onSave,
  currentModelConfig,
  knowledgeBases,
  modelConfigs,
  setKnowledgeBases,
  setModelConfigs,
  onModelChange,
  onConfigChange,
  onDeleteConfig,
  onCreateConfig,
  onRefreshData,
  translations,
  showSystemPrompt = false,
}) => {
  // Local state
  const [showAddLLM, setShowAddLLM] = useState<boolean>(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [newModelName, setNewModelName] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [showConfirmDeleteConfig, setShowConfirmDeleteConfig] = useState<{
    config: ModelConfig;
  } | null>(null);

  const handleBaseToggle = (id: string) => {
    setKnowledgeBases((bases) =>
      bases.map((base) =>
        base.id === id ? { ...base, selected: !base.selected } : base
      )
    );
  };

  const handleSubmit = () => {
    if (!currentModelConfig) return;

    const selectedIds = knowledgeBases
      .filter((base) => base.selected)
      .map((base) => base.id);
    const selectedNames = knowledgeBases
      .filter((base) => base.selected)
      .map((base) => base.name);

    const newModelConfig: ModelConfig = {
      ...currentModelConfig,
      baseUsed: selectedIds.map((item, index) => ({
        name: selectedNames[index],
        baseId: item,
      })),
    };

    onSave(newModelConfig);
    setVisible(false);
  };

  const onClose = () => {
    setVisible(false);
    onRefreshData();
  };

  const handleDeleteConfig = (config: ModelConfig) => {
    setShowConfirmDeleteConfig({ config });
  };

  const confirmDeleteConfig = async () => {
    if (showConfirmDeleteConfig) {
      await onDeleteConfig(showConfirmDeleteConfig.config);
      setModelConfigs((prev) =>
        prev.filter((item) => item.modelId !== showConfirmDeleteConfig.config.modelId)
      );
      setShowConfirmDeleteConfig(null);
    }
  };

  const cancelDeleteConfig = () => {
    setShowConfirmDeleteConfig(null);
  };

  const handleCreateConfirm = async () => {
    if (!newModelName.trim()) {
      setNameError("Model name can not be null!");
      return;
    }
    if (modelConfigs.some((config) => config.modelName === newModelName)) {
      setNameError("Model name already exist!");
      return;
    }

    if (!currentModelConfig) return;

    const newModel: ModelConfig = {
      ...currentModelConfig,
      modelName: newModelName,
    };

    const created = await onCreateConfig(newModel);
    if (created) {
      setModelConfigs((prev) => [...prev, created]);
      onModelChange(created.modelId);
      setShowAddLLM(false);
      setNewModelName("");
      setNameError(null);
    }
  };

  if (!visible || !currentModelConfig) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-3xl px-10 py-6 w-[40%]">
        <ModalHeader
          title={translations.title}
          addKnowledgeBaseLabel={translations.addKnowledgeBase}
          tutorialsLabel={translations.tutorials}
        />

        <div className="flex-1 overflow-y-auto px-2 max-h-[50vh]">
          <div className="pt-2">
            <LlmSettingsSection
              modelConfig={currentModelConfig}
              modelConfigs={modelConfigs}
              showDropdown={showDropdown}
              setShowDropdown={setShowDropdown}
              onModelChange={onModelChange}
              onDeleteConfig={handleDeleteConfig}
              onConfigChange={onConfigChange}
              onAddNewConfig={() => setShowAddLLM(true)}
            />
          </div>

          <div className="pt-2">
            <details className="group" open>
              <summary className="flex items-center cursor-pointer text-sm font-medium">
                {translations.chooseDB}
                <svg
                  className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
              </summary>
              <KnowledgeBaseSelector
                knowledgeBases={knowledgeBases}
                onBaseToggle={handleBaseToggle}
              />
            </details>
          </div>

          {showSystemPrompt && translations.systemPrompt && (
            <div className="pt-2">
              <details className="group">
                <summary className="flex items-center cursor-pointer text-sm font-medium">
                  {translations.systemPrompt}
                  <svg
                    className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
                </summary>
                <div className="mt-2 space-y-4">
                  <textarea
                    className="mt-1 w-full px-4 py-2 border border-gray-200 rounded-3xl min-h-[10vh] max-h-[20vh] resize-none overflow-y-auto focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    placeholder={currentModelConfig.systemPrompt}
                    rows={1}
                    value={currentModelConfig.systemPrompt}
                    onChange={(e) => {
                      e.target.style.height = "auto";
                      e.target.style.height = e.target.scrollHeight + "px";
                      onConfigChange({ systemPrompt: e.target.value });
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && e.shiftKey) {
                        e.preventDefault();
                      }
                    }}
                  />
                </div>
              </details>
            </div>
          )}

          <div className="pt-2">
            <AdvancedSettings
              modelConfig={currentModelConfig}
              onConfigChange={onConfigChange}
            />
          </div>
        </div>

        <ModalActions
          onCancel={onClose}
          onSave={handleSubmit}
          cancelLabel={translations.cancel}
          saveLabel={translations.save}
        />
      </div>

      {showAddLLM && (
        <AddLLMEngine
          setShowAddLLM={setShowAddLLM}
          nameError={nameError}
          setNameError={setNameError}
          newModelName={newModelName}
          setNewModelName={setNewModelName}
          onCreateConfirm={handleCreateConfirm}
        />
      )}

      {showConfirmDeleteConfig && (
        <ConfirmDialog
          message={`${translations.deleteModelConfigConfirmation}"${showConfirmDeleteConfig.config.modelName.slice(0, 30)}"`}
          onConfirm={confirmDeleteConfig}
          onCancel={cancelDeleteConfig}
        />
      )}
    </div>
  );
};

export default KnowledgeConfigModalBase;

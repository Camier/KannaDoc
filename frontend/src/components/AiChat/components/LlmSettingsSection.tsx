/**
 * LlmSettingsSection Component
 *
 * Collapsible section for LLM configuration:
 * - Model selection dropdown
 * - Model URL input
 * - API Key input
 *
 * @param modelConfig - Current model configuration
 * @param modelConfigs - List of available model configurations
 * @param showDropdown - Dropdown visibility state
 * @param setShowDropdown - Toggle dropdown
 * @param onModelChange - Callback when model changes
 * @param onDeleteConfig - Callback when model deletion requested
 * @param onConfigChange - Callback when config value changes
 * @param onAddNewConfig - Callback to add new configuration
 */
import React from "react";
import { ModelConfig } from "@/types/types";
import { useTranslations } from "next-intl";
import { ModelSelector } from "./ModelSelector";

interface LlmSettingsSectionProps {
  modelConfig: ModelConfig;
  modelConfigs: ModelConfig[];
  showDropdown: boolean;
  setShowDropdown: (show: boolean) => void;
  onModelChange: (modelId: string) => void;
  onDeleteConfig: (config: ModelConfig) => void;
  onConfigChange: (updates: Partial<ModelConfig>) => void;
  onAddNewConfig: () => void;
}

export const LlmSettingsSection: React.FC<LlmSettingsSectionProps> = ({
  modelConfig,
  modelConfigs,
  showDropdown,
  setShowDropdown,
  onModelChange,
  onDeleteConfig,
  onConfigChange,
  onAddNewConfig,
}) => {
  const t = useTranslations("ChatKnowledgeConfigModal");

  return (
    <details className="group" open>
      <summary className="flex items-center cursor-pointer text-sm font-medium">
        {t("llmSettings")}
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

      <div className="mt-2 space-y-4 pb-2">
        <div>
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium mb-2">
              {t("llmEngine")}
            </label>
            <div
              onClick={onAddNewConfig}
              className="px-3 py-2 text-indigo-500 hover:text-indigo-700 text-sm flex items-center cursor-pointer"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4 mr-1"
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
              {t("addNewConfiguration")}
            </div>
          </div>
          <div className="flex gap-2">
            <ModelSelector
              modelName={modelConfig.modelName}
              modelConfigs={modelConfigs}
              currentModelId={modelConfig.modelId}
              onModelChange={onModelChange}
              onDeleteConfig={onDeleteConfig}
              showDropdown={showDropdown}
              setShowDropdown={setShowDropdown}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium">{t("llmUrl")}</label>
          <input
            type="url"
            value={modelConfig.modelURL || ""}
            onChange={(e) => onConfigChange({ modelURL: e.target.value })}
            className={`mt-1 w-full px-4 py-2 border border-gray-200 rounded-3xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
              modelConfig.modelId.startsWith("system_")
                ? "bg-gray-100 dark:bg-gray-700 cursor-not-allowed text-gray-500"
                : ""
            }`}
            placeholder="https://api.example.com/v1"
            disabled={modelConfig.modelId.startsWith("system_")}
          />
        </div>

        <div>
          <label className="block text-sm font-medium">{t("apiKey")}</label>
          <input
            type="password"
            value={modelConfig.apiKey || ""}
            onChange={(e) => onConfigChange({ apiKey: e.target.value })}
            className={`mt-1 w-full px-4 py-2 border border-gray-200 rounded-3xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
              modelConfig.modelId.startsWith("system_")
                ? "bg-gray-100 dark:bg-gray-700 cursor-not-allowed text-gray-500"
                : ""
            }`}
            placeholder="sk-xxxxxxxx"
            disabled={modelConfig.modelId.startsWith("system_")}
          />
        </div>
      </div>
    </details>
  );
};

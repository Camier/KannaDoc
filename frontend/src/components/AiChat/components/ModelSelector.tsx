/**
 * ModelSelector Component
 *
 * Custom dropdown for selecting LLM engine configurations.
 * Supports selection, deletion, and displays current selection.
 *
 * @param modelName - Currently selected model name
 * @param modelConfigs - List of available model configurations
 * @param onModelChange - Callback when model selection changes
 * @param onDeleteConfig - Callback when model deletion is requested
 * @param showDropdown - Whether dropdown is currently open
 * @param setShowDropdown - Toggle dropdown visibility
 * @param dropdownRef - Reference for click-away detection
 */
import React, { useRef } from "react";
import { ModelConfig } from "@/types/types";
import { useClickAway } from "react-use";
import { useTranslations } from "next-intl";

interface ModelSelectorProps {
  modelName: string;
  modelConfigs: ModelConfig[];
  currentModelId?: string;
  onModelChange: (modelId: string) => void;
  onDeleteConfig: (config: ModelConfig) => void;
  showDropdown: boolean;
  setShowDropdown: (show: boolean) => void;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  modelName,
  modelConfigs,
  currentModelId,
  onModelChange,
  onDeleteConfig,
  showDropdown,
  setShowDropdown,
}) => {
  const t = useTranslations("ChatKnowledgeConfigModal");
  const ref = useRef(null);
  useClickAway(ref, () => {
    setShowDropdown(false);
  });

  return (
    <div className="relative w-full" ref={ref}>
      <div
        onClick={() => setShowDropdown(!showDropdown)}
        className="mt-1 w-full px-4 py-2 border border-gray-700 rounded-3xl cursor-pointer bg-gray-800 text-gray-100 flex items-center justify-between hover:border-indigo-500 transition-colors"
      >
        <span className="text-gray-700">{modelName}</span>
        <svg
          className={`w-5 h-5 text-gray-400 transform transition-transform ${
            showDropdown ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </div>

      {showDropdown && (
        <div className="p-1 absolute w-full mt-1 bg-gray-900 border border-gray-700 rounded-3xl shadow-lg z-50 overflow-hidden">
          <div className="max-h-60 overflow-y-auto">
            {modelConfigs.map((model) => (
              <div
                key={model.modelId}
                onClick={() => {
                  onModelChange(model.modelId);
                  setShowDropdown(false);
                }}
                className="px-4 py-2 cursor-pointer rounded-3xl transition-colors hover:bg-gray-200"
              >
                <div className="w-full flex gap-1 items-center justify-between">
                  {model.modelName}
                  {model.modelId === currentModelId ? (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="size-4"
                    >
                      <path
                        fillRule="evenodd"
                        d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : !model.modelId.startsWith("system_") ? (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className="size-4 text-indigo-500 hover:text-indigo-700"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConfig(model);
                      }}
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.5 4.478v.227a48.816 48.816 0 0 1 3.878.512.75.75 0 1 1-.256 1.478l-.209-.035-1.005 13.07a3 3 0 0 1-2.991 2.77H8.084a3 3 0 0 1-2.991-2.77L4.087 6.66l-.209.035a.75.75 0 0 1-.256-1.478A48.567 48.567 0 0 1 7.5 4.705v-.227c0-1.564 1.213-2.9 2.816-2.951a52.662 52.662 0 0 1 3.369 0c1.603.051 2.815 1.387 2.815 2.951Zm-6.136-1.452a51.196 51.196 0 0 1 3.273 0C14.39 3.05 15 3.684 15 4.478v.113a49.488 49.488 0 0 0-6 0v-.113c0-.794.609-1.428 1.364-1.452Zm-.355 5.945a.75.75 0 1 0-1.5.058l.347 9a.75.75 0 1 0 1.499-.058l-.346-9Zm5.48.058a.75.75 0 1 0-1.498-.058l-.347 9a.75.75 0 0 0 1.5.058l.345-9Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * AdvancedSettings Component
 *
 * Collapsible section for LLM advanced parameters:
 * - Temperature
 * - Max Token (maxLength)
 * - Top-P
 * - Top-K
 * - Score Threshold
 *
 * @param modelConfig - Current model configuration
 * @param onConfigChange - Callback when config value changes
 */
import React from "react";
import { ModelConfig } from "@/types/types";
import { useTranslations } from "next-intl";

interface AdvancedSettingsProps {
  modelConfig: ModelConfig;
  onConfigChange: (updates: Partial<ModelConfig>) => void;
}

export const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({
  modelConfig,
  onConfigChange,
}) => {
  const t = useTranslations("ChatKnowledgeConfigModal");

  return (
    <details className="group">
      <summary className="flex items-center cursor-pointer text-sm font-medium">
        {t("advancedSettings")}
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
        <AdvancedParameter
          label={t("temperature")}
          rangeLabel={t("range_0_1")}
          type="number"
          min="0"
          max="1"
          step="0.1"
          value={modelConfig.temperature}
          useDefault={modelConfig.useTemperatureDefault}
          onChange={(value) => onConfigChange({ temperature: value })}
          onToggleDefault={(checked) =>
            onConfigChange({ useTemperatureDefault: checked })
          }
        />

        <AdvancedParameter
          label={t("maxToken")}
          rangeLabel={t("range_1024_1048576")}
          type="number"
          min="1024"
          max="1048576"
          value={modelConfig.maxLength}
          useDefault={modelConfig.useMaxLengthDefault}
          onChange={(value) => onConfigChange({ maxLength: value })}
          onToggleDefault={(checked) =>
            onConfigChange({ useMaxLengthDefault: checked })
          }
        />

        <AdvancedParameter
          label={t("topP")}
          rangeLabel={t("range_0_1")}
          type="number"
          min="0"
          max="1"
          step="0.1"
          value={modelConfig.topP}
          useDefault={modelConfig.useTopPDefault}
          onChange={(value) => onConfigChange({ topP: value })}
          onToggleDefault={(checked) =>
            onConfigChange({ useTopPDefault: checked })
          }
        />

        <AdvancedParameter
          label={t("knowledgeBaseTopK")}
          rangeLabel={t("range_1_30")}
          type="number"
          min="1"
          max="30"
          step="1"
          value={modelConfig.topK}
          useDefault={modelConfig.useTopKDefault}
          onChange={(value) => onConfigChange({ topK: value })}
          onToggleDefault={(checked) =>
            onConfigChange({ useTopKDefault: checked })
          }
        />

        <AdvancedParameter
          label={t("retrievalScoreThreshold")}
          rangeLabel={t("range_0_20")}
          type="number"
          min="0"
          max="20"
          step="1"
          value={modelConfig.scoreThreshold}
          useDefault={modelConfig.useScoreThresholdDefault}
          onChange={(value) => onConfigChange({ scoreThreshold: value })}
          onToggleDefault={(checked) =>
            onConfigChange({ useScoreThresholdDefault: checked })
          }
          hint={t("suggestedRetrievalScoreThreshold")}
        />
      </div>
    </details>
  );
};

interface AdvancedParameterProps {
  label: string;
  rangeLabel: string;
  type: "number";
  min?: string;
  max?: string;
  step?: string;
  value: number;
  useDefault: boolean;
  onChange: (value: number) => void;
  onToggleDefault: (checked: boolean) => void;
  hint?: string;
}

const AdvancedParameter: React.FC<AdvancedParameterProps> = ({
  label,
  rangeLabel,
  type,
  min,
  max,
  step,
  value,
  useDefault,
  onChange,
  onToggleDefault,
  hint,
}) => {
  const t = useTranslations("ChatKnowledgeConfigModal");

  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium">
          {label}
          <span className="text-xs text-gray-500 ml-1">{rangeLabel}</span>
        </label>
        <label className="relative inline-flex items-center group p-2 rounded-3xl hover:bg-gray-50 cursor-pointer">
          <input
            type="checkbox"
            checked={useDefault}
            onChange={(e) => onToggleDefault(e.target.checked)}
            className="appearance-none h-5 w-5 border-2 border-gray-300 rounded-3xl transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
          />
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="absolute size-4 text-white"
          >
            <path
              fillRule="evenodd"
              d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
              clipRule="evenodd"
              transform="translate(2.8, 1)"
            />
          </svg>
          <span className="text-sm text-gray-600 ml-2">
            {t("useModelDefault")}
          </span>
        </label>
      </div>
      {hint && (
        <p className="block text-[13px] px-1 text-gray-600">{hint}</p>
      )}
      <input
        type={type}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => {
          const parsed =
            type === "number"
              ? step?.includes(".")
                ? parseFloat(e.target.value) || 0
                : parseInt(e.target.value) || 0
              : e.target.value;
          onChange(parsed as number);
        }}
        disabled={useDefault}
        className="mt-1 w-full px-4 py-2 border border-gray-200 rounded-3xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
      />
    </div>
  );
};

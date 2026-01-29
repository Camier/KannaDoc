import { ModelConfig } from "@/types/types";
import { create } from "zustand";

interface ModelConfigStore {
  modelConfig: ModelConfig;
  setModelConfig: (
    updater: ModelConfig | ((prev: ModelConfig) => ModelConfig)
  ) => void;
}

const useModelConfigStore = create<ModelConfigStore>((set) => ({
  modelConfig: {
    baseUsed: [],
    modelId: "",
    modelName: "",
    modelURL: null,
    apiKey: null,
    systemPrompt:
      "All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).",
    temperature: 0.1,
    maxLength: 8096,
    topP: 0.01,
    topK: 3,
    scoreThreshold: 10,
    useTemperatureDefault: true,
    useMaxLengthDefault: true,
    useTopPDefault: true,
    useTopKDefault: true,
    useScoreThresholdDefault: true,
  },
  setModelConfig: (updater) =>
    set((state) => ({
      modelConfig:
        typeof updater === "function" ? updater(state.modelConfig) : updater,
    })),
}));

export default useModelConfigStore;

"use client";
import { ModelConfig } from "@/types/types";
import { apiClient as api } from "./apiClient";

export const getAllModelConfig = async (_username?: string) => {
  return api.get("/config/all");
};

export const updateModelConfig = async (
  _username: string,
  modelConfig: ModelConfig
) => {
  return api.patch(`/config/${modelConfig.modelId}`, {
    model_name: modelConfig.modelName,
    model_url: modelConfig.modelURL,
    api_key: modelConfig.apiKey,
    base_used: modelConfig.baseUsed,
    system_prompt: modelConfig.systemPrompt,
    temperature: modelConfig.useTemperatureDefault
      ? -1
      : modelConfig.temperature,
    max_length: modelConfig.useMaxLengthDefault ? -1 : modelConfig.maxLength,
    top_P: modelConfig.useTopPDefault ? -1 : modelConfig.topP,
    top_K: modelConfig.useTopKDefault ? -1 : modelConfig.topK,
    score_threshold: modelConfig.useScoreThresholdDefault ? -1 : modelConfig.scoreThreshold,
  });
};

export const addModelConfig = async (
  _username: string,
  modelConfig: ModelConfig
) => {
  return api.post("/config/", {
    model_name: modelConfig.modelName,
    model_url: modelConfig.modelURL,
    api_key: modelConfig.apiKey,
    base_used: modelConfig.baseUsed,
    system_prompt: modelConfig.systemPrompt,
    temperature: modelConfig.useTemperatureDefault
      ? -1
      : modelConfig.temperature,
    max_length: modelConfig.useMaxLengthDefault ? -1 : modelConfig.maxLength,
    top_P: modelConfig.useTopPDefault ? -1 : modelConfig.topP,
    top_K: modelConfig.useTopKDefault ? -1 : modelConfig.topK,
    score_threshold: modelConfig.useScoreThresholdDefault ? -1 : modelConfig.scoreThreshold,
  });
};

export const deleteModelConfig = async (_username: string, modelId: string) => {
  return api.delete(`/config/${modelId}`);
};

export const selectModel = async (_username: string, modelId: string) => {
  return api.put(`/config/select-model`, {
    model_id: modelId,
  });
};

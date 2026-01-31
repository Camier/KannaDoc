import { ModelConfig } from "@/types/types";

/**
 * Backend Model Configuration Format
 * 
 * This is the format expected by the backend API endpoints.
 */
export interface BackendModelConfig {
  model_name: string;
  model_url: string | null;
  api_key: string | null;
  base_used: { name: string; baseId: string }[];
  system_prompt: string;
  temperature: number;
  max_length: number;
  top_P: number;
  top_K: number;
  score_threshold: number;
}

/**
 * Map frontend ModelConfig to backend format
 * 
 * Converts camelCase frontend model config to snake_case backend format.
 * Handles default value mapping (-1 means "use default" in backend).
 * 
 * @param config - Frontend ModelConfig
 * @returns BackendModelConfig for API requests
 */
export function mapModelConfigToBackend(config: ModelConfig): BackendModelConfig {
  return {
    model_name: config.modelName,
    model_url: config.modelURL,
    api_key: config.apiKey,
    base_used: config.baseUsed,
    system_prompt: config.systemPrompt,
    temperature: config.useTemperatureDefault ? -1 : config.temperature,
    max_length: config.useMaxLengthDefault ? -1 : config.maxLength,
    top_P: config.useTopPDefault ? -1 : config.topP,
    top_K: config.useTopKDefault ? -1 : config.topK,
    score_threshold: config.useScoreThresholdDefault ? -1 : config.scoreThreshold,
  };
}

/**
 * Map backend response to frontend ModelConfig
 * 
 * Converts snake_case backend response to camelCase frontend format.
 * 
 * @param backendConfig - Backend model config response
 * @returns ModelConfig for frontend state
 */
export function mapBackendToModelConfig(backendConfig: any): ModelConfig {
  return {
    modelId: backendConfig.model_id,
    modelName: backendConfig.model_name,
    modelURL: backendConfig.model_url,
    apiKey: backendConfig.api_key,
    baseUsed: backendConfig.base_used || [],
    systemPrompt: backendConfig.system_prompt || "",
    temperature: backendConfig.temperature === -1 ? 0.1 : backendConfig.temperature,
    maxLength: backendConfig.max_length === -1 ? 8192 : backendConfig.max_length,
    topP: backendConfig.top_P === -1 ? 0.01 : backendConfig.top_P,
    topK: backendConfig.top_K === -1 ? 3 : backendConfig.top_K,
    scoreThreshold: backendConfig.score_threshold === -1 ? 10 : backendConfig.score_threshold,
    useTemperatureDefault: backendConfig.temperature === -1,
    useMaxLengthDefault: backendConfig.max_length === -1,
    useTopPDefault: backendConfig.top_P === -1,
    useTopKDefault: backendConfig.top_K === -1,
    useScoreThresholdDefault: backendConfig.score_threshold === -1,
  };
}

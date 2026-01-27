/**
 * useKnowledgeConfigData Hook
 *
 * Manages data fetching for knowledge bases and model configurations.
 * Shared between Chat and Workflow KnowledgeConfigModal components.
 *
 * @param username - Current user's username
 * @param selectedModelId - ID of the currently selected model (optional)
 * @returns Object containing knowledge bases, model configs, setters, and refresh function
 */
import { useState, useCallback } from "react";
import { KnowledgeBase, ModelConfig } from "@/types/types";
import { getAllKnowledgeBase } from "@/lib/api/knowledgeBaseApi";
import { getAllModelConfig } from "@/lib/api/configApi";

interface UseKnowledgeConfigDataParams {
  username?: string;
  selectedModelId?: string;
}

interface UseKnowledgeConfigDataResult {
  knowledgeBases: KnowledgeBase[];
  setKnowledgeBases: React.Dispatch<React.SetStateAction<KnowledgeBase[]>>;
  modelConfigs: ModelConfig[];
  setModelConfigs: React.Dispatch<React.SetStateAction<ModelConfig[]>>;
  refreshData: () => Promise<void>;
}

export const useKnowledgeConfigData = ({
  username,
  selectedModelId,
}: UseKnowledgeConfigDataParams): UseKnowledgeConfigDataResult => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [modelConfigs, setModelConfigs] = useState<ModelConfig[]>([]);

  const fetchData = useCallback(async () => {
    if (!username) return;

    try {
      const responseBase = await getAllKnowledgeBase(username);
      const bases: KnowledgeBase[] = responseBase.data.map((item: any) => ({
        name: item.knowledge_base_name,
        id: item.knowledge_base_id,
        selected: false,
      }));

      const response = await getAllModelConfig(username);
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
          useTemperatureDefault: item.temperature === -1,
          useMaxLengthDefault: item.max_length === -1,
          useTopPDefault: item.top_P === -1,
          useTopKDefault: item.top_K === -1,
          useScoreThresholdDefault: item.score_threshold === -1,
        })
      );

      const selected = modelConfigsResponse.find(
        (m) => m.modelId === selectedModelId
      );

      if (selected) {
        const updatedKnowledgeBases = bases.map((kb) => ({
          ...kb,
          selected: selected.baseUsed.some((bu) => bu.baseId === kb.id),
        }));
        setKnowledgeBases(updatedKnowledgeBases);
      } else {
        setKnowledgeBases(bases);
      }

      setModelConfigs(modelConfigsResponse);
    } catch (error) {
      console.error("Error fetching knowledge base and model configs:", error);
    }
  }, [username, selectedModelId]);

  return {
    knowledgeBases,
    setKnowledgeBases,
    modelConfigs,
    setModelConfigs,
    refreshData: fetchData,
  };
};

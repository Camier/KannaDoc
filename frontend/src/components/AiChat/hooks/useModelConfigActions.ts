/**
 * useModelConfigActions Hook
 *
 * Handles model configuration CRUD operations.
 * Shared between Chat and Workflow KnowledgeConfigModal components.
 *
 * @param username - Current user's username
 * @returns Object containing action functions for model config management
 */
import { useCallback } from "react";
import { ModelConfig } from "@/types/types";
import {
  addModelConfig,
  deleteModelConfig,
} from "@/lib/api/configApi";

interface UseModelConfigActionsParams {
  username?: string;
}

interface UseModelConfigActionsResult {
  createModelConfig: (
    modelConfig: ModelConfig,
    modelConfigs: ModelConfig[]
  ) => Promise<ModelConfig | null>;
  deleteModelConfigById: (modelId: string) => Promise<void>;
}

export const useModelConfigActions = ({
  username,
}: UseModelConfigActionsParams): UseModelConfigActionsResult => {
  const createModelConfig = useCallback(
    async (
      modelConfig: ModelConfig,
      modelConfigs: ModelConfig[]
    ): Promise<ModelConfig | null> => {
      if (!username) return null;

      try {
        const response = await addModelConfig(username, modelConfig);
        return {
          ...modelConfig,
          modelId: response.data.model_id,
        };
      } catch (error) {
        console.error("Error creating model config:", error);
        return null;
      }
    },
    [username]
  );

  const deleteModelConfigById = useCallback(
    async (modelId: string) => {
      if (!username) return;

      try {
        await deleteModelConfig(username, modelId);
      } catch (error) {
        console.error("Error deleting model config:", error);
      }
    },
    [username]
  );

  return {
    createModelConfig,
    deleteModelConfigById,
  };
};

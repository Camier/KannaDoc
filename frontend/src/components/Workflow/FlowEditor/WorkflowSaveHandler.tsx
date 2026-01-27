/**
 * WorkflowSaveHandler
 *
 * Handles workflow saving operations including manual save, auto-save, and validation.
 * Manages save status notifications and error handling.
 *
 * Responsibilities:
 * - Manual workflow save
 * - Periodic auto-save
 * - Validation before save
 * - Save status notifications
 */

import { useEffect, useCallback } from "react";
import { CustomNode, CustomEdge } from "@/types/types";
import { createWorkflow } from "@/lib/api/workflowApi";
import { useTranslations } from "next-intl";

interface WorkflowSaveHandlerProps {
  workflowId: string;
  workflowName: string;
  startNode: string;
  userName: string | undefined;
  dockerImageUse: string;
  globalVariables: { [key: string]: string };
  nodes: CustomNode[];
  edges: CustomEdge[];
  onSaveStatusChange: (status: { visible: boolean; message: string; type: "success" | "error" }) => void;
  enabled?: boolean;
}

export const useWorkflowSaveHandler = ({
  workflowId,
  workflowName,
  startNode,
  userName,
  dockerImageUse,
  globalVariables,
  nodes,
  edges,
  onSaveStatusChange,
  enabled = true,
}: WorkflowSaveHandlerProps) => {
  const t = useTranslations("FlowEditor");

  const showTemporaryAlert = useCallback(
    (message: string, type: "success" | "error") => {
      onSaveStatusChange({ visible: true, message, type });
      setTimeout(() => {
        onSaveStatusChange((prev) => ({ ...prev, visible: false }));
      }, 5000);
    },
    [onSaveStatusChange]
  );

  const handleSaveWorkFlow = useCallback(async () => {
    if (userName) {
      try {
        const response = await createWorkflow(
          workflowId,
          userName,
          workflowName,
          { docker_image_use: dockerImageUse },
          startNode,
          globalVariables,
          nodes,
          edges
        );
        if (response.status == 200) {
          showTemporaryAlert(t("saveSuccess"), "success");
        }
      } catch (error) {
        console.error("Save failed:", error);
        showTemporaryAlert(t("saveFailure"), "error");
      }
    }
  }, [
    userName,
    workflowId,
    workflowName,
    dockerImageUse,
    startNode,
    globalVariables,
    nodes,
    edges,
    showTemporaryAlert,
    t,
  ]);

  // Auto-save every 60 seconds
  useEffect(() => {
    if (!enabled) return;

    const intervalId = setInterval(async () => {
      if (userName) {
        try {
          const response = await createWorkflow(
            workflowId,
            userName,
            workflowName,
            { docker_image_use: dockerImageUse },
            startNode,
            globalVariables,
            nodes,
            edges
          );
          if (response.status == 200) {
            showTemporaryAlert(
              t("autoSaveSuccess", { workflowName }),
              "success"
            );
          }
        } catch (error) {
          console.error("Auto-save failed:", error);
          showTemporaryAlert(
            t("autoSaveFailure", { workflowName }),
            "error"
          );
        }
      }
    }, 60000);

    return () => clearInterval(intervalId);
  }, [
    enabled,
    userName,
    workflowId,
    workflowName,
    dockerImageUse,
    startNode,
    globalVariables,
    nodes,
    edges,
    showTemporaryAlert,
    t,
  ]);

  return {
    handleSaveWorkFlow,
    showTemporaryAlert,
  };
};

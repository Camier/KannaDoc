/**
 * useWorkflowImportExport
 *
 * Hook that handles workflow import and export functionality.
 * Validates file format and manages workflow state transfer.
 *
 * Responsibilities:
 * - Export workflow to JSON file
 * - Import workflow from JSON file
 * - Validate imported data format
 * - Strip sensitive data (API keys) on export
 *
 * Returns:
 * - fileInputRef: Ref for the hidden file input element
 * - handleExportWorkflow: Function to export current workflow
 * - handleImportWorkflow: Function to handle file input change
 * - triggerImport: Function to trigger the file input click
 */

import { useRef, useCallback } from "react";
import { logger } from "@/lib/logger";
import { CustomNode, CustomEdge } from "@/types/types";
import { useTranslations } from "next-intl";

interface UseWorkflowImportExportProps {
  workflowName: string;
  nodes: CustomNode[];
  edges: CustomEdge[];
  globalVariables: { [key: string]: string };
  onImport: (nodes: CustomNode[], edges: CustomEdge[], variables: { [key: string]: string }) => void;
  onError: (message: string) => void;
}

export const useWorkflowImportExport = ({
  workflowName,
  nodes,
  edges,
  globalVariables,
  onImport,
  onError,
}: UseWorkflowImportExportProps) => {
  const t = useTranslations("FlowEditor");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExportWorkflow = useCallback(() => {
    // Remove API keys from exported nodes
    const outputNodes = nodes.map((node) => {
      if (node.data.nodeType !== "vlm" || !node.data.modelConfig) {
        return node;
      }

      return {
        ...node,
        data: {
          ...node.data,
          modelConfig: {
            ...node.data.modelConfig,
            apiKey: "",
          },
        },
      };
    });

    const exportData = {
      nodes: outputNodes,
      edges,
      globalVariables,
      metadata: {
        exportedAt: new Date().toISOString(),
      },
    };

    const jsonString = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `${workflowName}_${Date.now()}_layra.json`;
    document.body.appendChild(a);
    a.click();

    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [workflowName, nodes, edges, globalVariables]);

  const handleImportWorkflow = useCallback((
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        const content = e.target?.result as string;
        const data = JSON.parse(content);

        // Validate data format
        if (!data.nodes || !data.edges || !data.globalVariables) {
          throw new Error("Invalid workflow file format");
        }

        // Confirm import
        const confirm = window.confirm(t("importWorkflowAlert"));
        if (!confirm) return;

        // Update parent state
        onImport(data.nodes, data.edges, data.globalVariables);
      } catch (error) {
        logger.error("Import failed:", error);
        onError(t("invalidWorkflowFile"));
      }
    };

    reader.readAsText(file);
    event.target.value = ""; // Reset input to allow re-selecting same file
  }, [onImport, onError, t]);

  const triggerImport = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return {
    fileInputRef,
    handleExportWorkflow,
    handleImportWorkflow,
    triggerImport,
  };
};

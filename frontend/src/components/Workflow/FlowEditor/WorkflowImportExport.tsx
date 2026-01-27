/**
 * WorkflowImportExport
 *
 * Handles workflow import and export functionality.
 * Validates file format and manages workflow state transfer.
 *
 * Responsibilities:
 * - Export workflow to JSON file
 * - Import workflow from JSON file
 * - Validate imported data format
 * - Strip sensitive data (API keys) on export
 */

import React, { useRef } from "react";
import { CustomNode, CustomEdge } from "@/types/types";
import { useTranslations } from "next-intl";

interface WorkflowImportExportProps {
  workflowName: string;
  nodes: CustomNode[];
  edges: CustomEdge[];
  globalVariables: { [key: string]: string };
  onImport: (nodes: CustomNode[], edges: CustomEdge[], variables: { [key: string]: string }) => void;
  onError: (message: string) => void;
}

export const WorkflowImportExport: React.FC<WorkflowImportExportProps> = ({
  workflowName,
  nodes,
  edges,
  globalVariables,
  onImport,
  onError,
}) => {
  const t = useTranslations("FlowEditor");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExportWorkflow = () => {
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
  };

  const handleImportWorkflow = async (
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
        console.error("Import failed:", error);
        onError(t("invalidWorkflowFile"));
      }
    };

    reader.readAsText(file);
    event.target.value = ""; // Reset input to allow re-selecting same file
  };

  const triggerImport = () => {
    fileInputRef.current?.click();
  };

  return {
    fileInputRef,
    handleExportWorkflow,
    handleImportWorkflow,
    triggerImport,
  };
};

/**
 * Hook version for easier integration
 */
export const useWorkflowImportExport = (props: WorkflowImportExportProps) => {
  return WorkflowImportExport(props);
};

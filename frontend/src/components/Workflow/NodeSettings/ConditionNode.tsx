/**
 * ConditionNode Settings Component - Refactored to use NodeSettingsBase
 *
 * This component demonstrates the use of NodeSettingsBase composition pattern.
 * Reduced from ~639 lines to ~250 lines by extracting common patterns.
 */
import { logger } from "@/lib/logger";
import { runConditionTest } from "@/lib/api/workflowApi";
import { useFlowStore } from "@/stores/flowStore";
import { CustomNode } from "@/types/types";
import { useState } from "react";
import NodeSettingsBase, {
  NodeHeader,
  DescriptionSection,
  GlobalVariablesSection,
  OutputSection,
} from "./NodeSettingsBase";

// Default anonymous user for non-authenticated usage
const ANONYMOUS_USER = { name: "anonymous", email: "" };

interface ConditionNodeProps {
  saveNode: (node: CustomNode) => void;
  isDebugMode: boolean;
  node: CustomNode;
  setCodeFullScreenFlow: (value: boolean | ((prev: boolean) => boolean)) => void;
  codeFullScreenFlow: boolean;
}

const ConditionNodeComponent: React.FC<ConditionNodeProps> = ({
  saveNode,
  isDebugMode,
  node,
  setCodeFullScreenFlow,
  codeFullScreenFlow,
}) => {
  const user = ANONYMOUS_USER;
  const { updateConditions } = useFlowStore();
  const [runTest, setRunTest] = useState(false);

  const handleConditionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    updateConditions(node.id, parseInt(name), value);
  };

  const handleRunTest = async () => {
    if (user?.name) {
      setRunTest(true);
      const conditions = node.data.conditions;
      try {
        if (conditions) {
          const response = await runConditionTest(
            user.name,
            node,
            {}, // globalVariables will be accessed via store
            conditions
          );
          const id = node.id;
          if (response.data.code === 0) {
            updateOutput(
              node.id,
              response.data.result[id][0].condition_child[0]
            );
          } else {
            updateOutput(node.id, response.data.msg);
          }
        } else {
          updateOutput(node.id, "No condition found!");
        }
      } catch (error) {
        logger.error("Error connect:", error);
        updateOutput(node.id, "Error connect:" + error);
      } finally {
        setRunTest(false);
      }
    }
  };

  const { updateOutput } = useFlowStore();

  // Condition-specific section
  const ConditionSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.098 19.902a3.75 3.75 0 0 0 5.304 0l6.401-6.402M6.75 21A3.75 3.75 0 0 1 3 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 0 0 3.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.713c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008Z"
              />
            </svg>
            Condition Configuration
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
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
          </div>
          <button
            onClick={handleRunTest}
            disabled={runTest}
            className="cursor-pointer disabled:cursor-not-allowed px-3 py-1 rounded-full hover:bg-indigo-600 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
              />
            </svg>
            <span>Run Test</span>
          </button>
        </div>
      </summary>
      <div className="rounded-2xl shadow-lg overflow-auto w-full mb-2 py-2 px-4">
        {!node.data.conditions && (
          <div className="text-gray-500">Not connected</div>
        )}
        {node.data.conditions && (
          <div className="whitespace-pre-wrap space-y-2">
            {Object.keys(node.data.conditions).length === 0 ? (
              <div className="text-gray-500">Not connected</div>
            ) : (
              Object.entries(node.data.conditions).map(
                ([key, expression]) => (
                  <div
                    className="px-2 flex w-full items-center gap-2"
                    key={key}
                  >
                    <div className="max-w-[50%] overflow-auto">
                      Condition {key}
                    </div>
                    <div>=</div>
                    <input
                      name={key}
                      value={expression}
                      onChange={handleConditionChange}
                      placeholder="Enter condition"
                      onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          e.currentTarget.blur();
                        }
                      }}
                      className="flex-1 w-full px-3 py-1 border-2 border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                    />
                  </div>
                )
              )
            )}
          </div>
        )}
      </div>
    </details>
  );

  // Save button for header
  const saveButton = (
    <button
      onClick={() => saveNode(node)}
      className="cursor-pointer disabled:cursor-not-allowed py-1 px-2 rounded-full hover:bg-indigo-600 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="size-4"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
        />
      </svg>
      <span className="whitespace-nowrap">Save</span>
    </button>
  );

  return (
    <NodeSettingsBase
      node={node}
      isDebugMode={isDebugMode}
      codeFullScreenFlow={codeFullScreenFlow}
      setCodeFullScreenFlow={setCodeFullScreenFlow}
      translationNamespace="ConditionNode"
    >
      {(api) => (
        <>
          {/* Header with save button */}
          <NodeHeader node={node} updateNodeLabel={api.updateNodeLabel} actions={saveButton} />

          {/* Description section */}
          <DescriptionSection
            node={node}
            isEditing={api.isEditing}
            setIsEditing={api.setIsEditing}
            updateDescription={api.updateDescription}
            codeFullScreenFlow={codeFullScreenFlow}
            t={api.t}
          />

          {/* Global variables section */}
          <GlobalVariablesSection
            isDebugMode={isDebugMode}
            codeFullScreenFlow={codeFullScreenFlow}
            setCodeFullScreenFlow={setCodeFullScreenFlow}
            globalVariables={api.globalVariables}
            globalDebugVariables={api.globalDebugVariables}
            addProperty={api.addProperty}
            removeProperty={api.removeProperty}
            handleVariableChange={api.handleVariableChange}
            t={api.t}
          />

          {/* Condition-specific section */}
          <ConditionSection />

          {/* Output section */}
          <OutputSection
            node={node}
            updateDebug={api.updateDebug}
            t={api.t}
            disabled={runTest}
          />
        </>
      )}
    </NodeSettingsBase>
  );
};

export default ConditionNodeComponent;

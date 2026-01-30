/**
 * LoopNode Settings Component - Refactored to use NodeSettingsBase
 *
 * This component demonstrates the use of NodeSettingsBase composition pattern.
 * Reduced from ~617 lines to ~230 lines by extracting common patterns.
 */
import { useFlowStore } from "@/stores/flowStore";
import { CustomNode } from "@/types/types";
import { useState } from "react";
import NodeSettingsBase, {
  NodeHeader,
  DescriptionSection,
  GlobalVariablesSection,
  OutputSection,
} from "./NodeSettingsBase";

interface LoopNodeProps {
  saveNode: (node: CustomNode) => void;
  isDebugMode: boolean;
  node: CustomNode;
  setCodeFullScreenFlow: (value: boolean | ((prev: boolean) => boolean)) => void;
  codeFullScreenFlow: boolean;
}

const LoopNodeComponent: React.FC<LoopNodeProps> = ({
  saveNode,
  isDebugMode,
  node,
  setCodeFullScreenFlow,
  codeFullScreenFlow,
}) => {
  const { updateLoopType, updateMaxCount, updateCondition } = useFlowStore();

  const handleLoopChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const { value } = e.target;
    updateLoopType(node.id, value);
  };

  const handleMaxCountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    updateMaxCount(node.id, parseInt(value));
  };

  const handleConditionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    updateCondition(node.id, value);
  };

  // Loop-specific section
  const LoopSettingsSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-4"
            >
              <path
                fillRule="evenodd"
                d="M12 5.25c1.213 0 2.415.046 3.605.135a3.256 3.256 0 0 1 3.01 3.01c.044.583.077 1.17.1 1.759L17.03 8.47a.75.75 0 1 0-1.06 1.06l3 3a.75.75 0 0 0 1.06 0l3-3a.75.75 0 0 0-1.06-1.06l-1.752 1.751c-.023-.65-.06-1.296-.108-1.939a4.756 4.756 0 0 0-4.392-4.392 49.422 49.422 0 0 0-7.436 0A4.756 4.756 0 0 0 3.89 8.282c-.017.224-.033.447-.046.672a.75.75 0 1 0 1.497.092c.013-.217.028-.434.044-.651a3.256 3.256 0 0 1 3.01-3.01c1.19-.09 2.392-.135 3.605-.135Zm-6.97 6.22a.75.75 0 0 0-1.06 0l-3 3a.75.75 0 1 0 1.06 1.06l1.752-1.751c.023.65.06 1.296.108 1.939a4.756 4.756 0 0 0 4.392 4.392 49.413 49.413 0 0 0 7.436 0 4.756 4.756 0 0 0 4.392-4.392c.017-.223.032-.447.046-.672a.75.75 0 0 0-1.497-.092c-.013.217-.028.434-.044.651a3.256 3.256 0 0 1-3.01 3.01 47.953 47.953 0 0 1-7.21 0 3.256 3.256 0 0 1-3.01-3.01 47.759 47.759 0 0 1-.1-1.759L6.97 15.53a.75.75 0 0 0 1.06-1.06l-3-3Z"
                clipRule="evenodd"
              />
            </svg>
            Loop Settings
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
        </div>
      </summary>
      <div className="rounded-2xl shadow-lg overflow-auto w-full mb-2 py-2 px-4">
        <div className="whitespace-pre-wrap space-y-2">
          <div className="px-2 flex w-full items-center gap-2">
            <div className="max-w-[50%] overflow-auto">Loop Type</div>
            <div>=</div>
            <select
              name="LoopType"
              value={node.data.loopType}
              onChange={handleLoopChange}
              className="appearance-none flex-1 w-full px-3 py-1 border-2 border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              <option value="count">Count</option>
              <option value="condition">Condition</option>
            </select>
          </div>
          {node.data.loopType && (
            <div className="px-2 flex w-full items-center gap-2">
              <div className="max-w-[50%] overflow-auto">
                {node.data.loopType === "count" ? "Max Count" : "Break Condition"}
              </div>
              <div>=</div>
              {node.data.loopType === "count" ? (
                <input
                  name="LoopType"
                  value={node.data.maxCount ? node.data.maxCount : 1}
                  onChange={handleMaxCountChange}
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  placeholder="1"
                  onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      e.currentTarget.blur();
                    }
                  }}
                  className="flex-1 w-full px-3 py-1 border-2 border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
              ) : (
                <input
                  name="LoopType"
                  value={node.data.condition}
                  onChange={handleConditionChange}
                  placeholder="Enter break condition"
                  onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      e.currentTarget.blur();
                    }
                  }}
                  className="flex-1 w-full px-3 py-1 border-2 border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
              )}
            </div>
          )}
        </div>
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
      translationNamespace="LoopNode"
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

          {/* Loop-specific section */}
          <LoopSettingsSection />

          {/* Output section */}
          <OutputSection
            node={node}
            updateDebug={api.updateDebug}
            t={api.t}
          />
        </>
      )}
    </NodeSettingsBase>
  );
};

export default LoopNodeComponent;

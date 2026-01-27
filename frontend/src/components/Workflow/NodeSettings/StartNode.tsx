/**
 * StartNode Settings Component - Refactored to use NodeSettingsBase
 *
 * This component demonstrates the use of NodeSettingsBase composition pattern.
 * Reduced from ~437 lines to ~100 lines by extracting common patterns.
 */
import { useFlowStore } from "@/stores/flowStore";
import { useGlobalStore } from "@/stores/WorkflowVariableStore";
import { CustomNode } from "@/types/types";
import NodeSettingsBase, {
  NodeHeader,
  DescriptionSection,
  GlobalVariablesSection,
  OutputSection,
} from "./NodeSettingsBase";

interface StartNodeProps {
  isDebugMode: boolean;
  node: CustomNode;
  setCodeFullScreenFlow: (value: boolean | ((prev: boolean) => boolean)) => void;
  codeFullScreenFlow: boolean;
}

const StartNodeComponent: React.FC<StartNodeProps> = ({
  isDebugMode,
  node,
  setCodeFullScreenFlow,
  codeFullScreenFlow,
}) => {
  const { updateOutput } = useFlowStore();

  return (
    <NodeSettingsBase
      node={node}
      isDebugMode={isDebugMode}
      codeFullScreenFlow={codeFullScreenFlow}
      setCodeFullScreenFlow={setCodeFullScreenFlow}
      translationNamespace="StartNode"
    >
      {(api) => (
        <>
          {/* Header without save button */}
          <NodeHeader node={node} updateNodeLabel={api.updateNodeLabel} />

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

export default StartNodeComponent;

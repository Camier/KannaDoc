import { useFlowStore } from "@/stores/flowStore";
import { CustomNode, NodeTypeKey, nodeTypesInfo } from "@/types/types";
import { Dispatch, SetStateAction, useState } from "react";
import ConfirmDialog from "../ConfirmDialog";
import { parseToBeijingTime } from "@/utils/date";

interface NodeTypeSelectorProps {
  deleteCustomNode: (custom_node_name: string) => Promise<void>;
  workflowName: string;
  addNode: (key: NodeTypeKey) => void;
  addCustomNode: (name: string) => void;
  customNodes: {
    [key: string]: CustomNode;
  };
  setCustomNodes: Dispatch<
    SetStateAction<{
      [key: string]: CustomNode;
    }>
  >;
  lastModifyTime: string;
}

const NodeTypeSelector: React.FC<NodeTypeSelectorProps> = ({
  deleteCustomNode,
  addNode,
  addCustomNode,
  customNodes,
  setCustomNodes,
  workflowName,
  lastModifyTime,
}) => {
  const selectedType = useFlowStore((state) => state.selectedType);
  const setSelectedType = useFlowStore((state) => state.setSelectedType);
  const [searchTerm, setSearchTerm] = useState("")
  const [showConfirmDeleteNode, setShowConfirmDeleteNode] = useState<
    string | null
  >(null);

  const confirmDeleteNode = () => {
    if (showConfirmDeleteNode) {
      deleteCustomNode(showConfirmDeleteNode);
      setShowConfirmDeleteNode(null); // 关闭对话框
    }
  };

  const cancelDeleteNode = () => {
    if (showConfirmDeleteNode) {
      setShowConfirmDeleteNode(null); // 关闭对话框
    }
  };

  // 过滤知识库
  const filteredNodes = Object.entries(customNodes).filter(([name,node]) =>
    name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-2">
      <ul className="space-y-2">
        <div className="flex flex-col items-start justify-center px-2 gap-1">
          <div className="flex items-center justify-start px-2 gap-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-5 shrink-0"
            >
              <path
                fillRule="evenodd"
                d="M2.25 6a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3V6Zm3.97.97a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06l-2.25 2.25a.75.75 0 0 1-1.06-1.06l1.72-1.72-1.72-1.72a.75.75 0 0 1 0-1.06Zm4.28 4.28a.75.75 0 0 0 0 1.5h3a.75.75 0 0 0 0-1.5h-3Z"
                clipRule="evenodd"
              />
            </svg>

            <span className="whitespace-nowrap overflow-auto font-semibold">
              {workflowName}
            </span>
          </div>
          <span className="whitespace-nowrap overflow-auto text-xs font-semibold">
            {
              parseToBeijingTime(lastModifyTime + "Z")
                .toISOString()
                .split("T")[0]
            }{" "}
            {
              parseToBeijingTime(lastModifyTime + "Z")
                .toISOString()
                .split("T")[1]
                .split(".")[0]
            }
          </span>
        </div>
        <details className="group w-full space-y-1" open>
          <summary className="py-1 border-b-2 border-gray-200 text-center">
            Base Node
          </summary>
          {Object.entries(nodeTypesInfo).map(([key, type]) => (
            <li
              key={key}
              className={`cursor-pointer p-2 rounded-full text-center hover:bg-indigo-500 hover:text-white
              }`}
              onClick={() => {
                const typeKey = key as NodeTypeKey;
                if (selectedType === typeKey) {
                  addNode(typeKey);
                } else {
                  setSelectedType(typeKey);
                  addNode(typeKey);
                }
              }}
            >
              <div className="flex items-center justify-start gap-1">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-5"
                >
                  <path
                    fillRule="evenodd"
                    d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z"
                    clipRule="evenodd"
                  />
                </svg>
                {type.label}
              </div>
            </li>
          ))}
        </details>
        <details className="group w-full space-y-1" open>
          <summary className="py-1 border-b-2 border-gray-200 text-center">
            Custom Node
          </summary>
          <div className="py-1 relative w-[90%] mx-auto text-xs">
            <input
              type="text"
              placeholder="Search Nodes..."
              className="w-full pl-3 pr-6 py-1 rounded-full border border-gray-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-4 absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400"
            >
              <path
                fillRule="evenodd"
                d="M10.5 3.75a6.75 6.75 0 1 0 0 13.5 6.75 6.75 0 0 0 0-13.5ZM2.25 10.5a8.25 8.25 0 1 1 14.59 5.28l4.69 4.69a.75.75 0 1 1-1.06 1.06l-4.69-4.69A8.25 8.25 0 0 1 2.25 10.5Z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          {filteredNodes.map(([name, node]) => (
            <li
              key={name}
              className={`cursor-pointer p-2 rounded-full text-center hover:bg-indigo-500 hover:text-white
              }`}
              onClick={() => {
                addCustomNode(name);
              }}
            >
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center justify-start gap-1 overflow-auto w-full">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="size-5 shrink-0"
                  >
                    <path
                      fillRule="evenodd"
                      d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {name}
                </div>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-5 shrink-0 hover:text-indigo-700 text-indigo-500"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowConfirmDeleteNode(name);
                  }}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                  />
                </svg>
              </div>
            </li>
          ))}
        </details>
      </ul>
      {showConfirmDeleteNode && (
        <ConfirmDialog
          message={`Confirm the deletion of Custom Node "${showConfirmDeleteNode}"？`}
          onConfirm={confirmDeleteNode}
          onCancel={cancelDeleteNode}
        />
      )}
    </div>
  );
};

export default NodeTypeSelector;

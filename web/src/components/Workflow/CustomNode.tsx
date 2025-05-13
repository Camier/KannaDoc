import { useFlowStore } from "@/stores/flowStore";
import { CustomNodeProps, NodeTypeKey } from "@/types/types";
import { Handle, Position } from "@xyflow/react";

// 根据节点类型配置不同的连接点
const CustomNodeComponent = ({
  data,
  isConnectable,
  id,
  selected,
  ...props
}: CustomNodeProps) => {
  const deleteNode = useFlowStore((state) => state.deleteNode);
  const getHandles = (nodeType: NodeTypeKey) => {
    switch (nodeType) {
      case "start":
        return (
          <Handle
            type="source"
            position={Position.Right}
            isConnectable={isConnectable}
            className="!top-[calc(60%+8px)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
          />
        );
      // case "end":
      //   return (
      //     <Handle
      //       type="target"
      //       position={Position.Left}
      //       isConnectable={isConnectable}
      //       className="!top-[calc(60%+8px)] h-3 w-3 rounded-full !bg-indigo-500 relative
      //       after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2
      //       after:w-[10px] after:h-[2px] after:bg-white after:content-['']
      //       before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2
      //       before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
      //     />
      //   );
      case "loop":
        return (
          <>
            <Handle
              type="target"
              position={Position.Left}
              isConnectable={isConnectable}
              className="!top-[calc(60%+8px)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
            />
            <Handle
              type="source"
              position={Position.Right}
              isConnectable={isConnectable}
              className="!top-[calc(60%+8px)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
            />
            <Handle
              id="source"
              type="source"
              position={Position.Bottom}
              isConnectable={isConnectable}
              className="!left-[25%] h-3 w-3 rounded-full !bg-white relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-indigo-700 after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-indigo-700 before:content-['']"
            />
            <Handle
              id="target"
              type="target"
              position={Position.Bottom}
              isConnectable={isConnectable}
              className="!left-[75%] h-3 w-3 rounded-full !bg-white relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-indigo-700 after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-indigo-700 before:content-['']"
            />
          </>
        );
      default:
        return (
          <>
            <Handle
              type="target"
              position={Position.Left}
              isConnectable={isConnectable}
              className="!top-[calc(60%+8px)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
            />
            <Handle
              type="source"
              position={Position.Right}
              isConnectable={isConnectable}
              className="!top-[calc(60%+8px)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
            />
          </>
        );
    }
  };
  return (
    <div
      className={`w-32 h-32 overflow-auto p-2 shadow-lg rounded-3xl ${
        data.debug? selected ? "border-2 border-red-500" : "border-1 border-red-500" : selected ?  "border-2 border-indigo-700" : "border-1 border-indigo-500"
      } bg-white`}
    >
      {getHandles(data.nodeType)}
      <button
        onClick={(e) => {
          e.stopPropagation(); // 阻止事件冒泡
          deleteNode(id);
        }}
        className="cursor-pointer top-2 right-2 absolute"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 16 16"
          fill="currentColor"
          className="size-4 text-indigo-500"
        >
          <path d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z" />
        </svg>
      </button>
      <div
        // onBlur={(e) =>
        //   useFlowStore.getState().updateNodeLabel(id, e.currentTarget.innerText)
        // }
        className="h-[20%] flex items-center justify-center gap-1"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
          className="size-4 shrink-0"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
          />
        </svg>
        <span className="whitespace-nowrap text-sm">{data.label}</span>
      </div>
      <div
        // onBlur={(e) =>
        //   useFlowStore.getState().updateNodeLabel(id, e.currentTarget.innerText)
        // }
        className="h-[20%] flex items-center justify-center gap-1 text-sm text-gray-500"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="size-4"
        >
          <path
            fillRule="evenodd"
            d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z"
            clipRule="evenodd"
          />
        </svg>
        <span className="whitespace-nowrap text-sm">{data.nodeType}</span>
      </div>
      <div className="h-[calc(60%-8px)] mx-[calc(20%-8px)] mb-2 flex items-center justify-center rounded-3xl bg-gray-100">
        {data.status === "failed" ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className="size-6 text-red-500"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.25-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z"
            />
          </svg>
        ) : data.status === "pause" ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className="size-6 text-red-500"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 7.5V18M15 7.5V18M3 16.811V8.69c0-.864.933-1.406 1.683-.977l7.108 4.061a1.125 1.125 0 0 1 0 1.954l-7.108 4.061A1.125 1.125 0 0 1 3 16.811Z"
            />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className={`size-6 ${
              data.status === "ok" ? "text-indigo-500" : "opacity-30"
            }`}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
            />
          </svg>
        )}
      </div>
    </div>
  );
};

export default CustomNodeComponent;

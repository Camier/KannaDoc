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
        selected ? "border-2 border-indigo-700" : "border-1 border-indigo-500"
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
        className="h-[40%] flex items-center justify-center gap-1"
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
      <div className="h-[calc(60%-8px)] mx-[calc(20%-8px)] mb-2 flex items-center justify-center rounded-3xl bg-gray-100">
        {data.status === "failed"?
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
        </svg> : <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
          className={`size-6 ${data.status === "ok"? "text-indigo-500":"opacity-30"}`}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
          />
        </svg>}
      </div>
    </div>
  );
};

export default CustomNodeComponent;

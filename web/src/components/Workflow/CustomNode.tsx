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
            className="!top-[calc(50%)] h-3 w-3 rounded-full !bg-indigo-500 relative 
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
              className="!top-[calc(60%)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
            />
            <Handle
              type="source"
              position={Position.Right}
              isConnectable={isConnectable}
              className="!top-[calc(60%)] h-3 w-3 rounded-full !bg-indigo-500 relative 
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
              className="!top-[calc(50%)] h-3 w-3 rounded-full !bg-indigo-500 relative 
            after:absolute after:left-1/2 after:top-1/2 after:-translate-x-1/2 after:-translate-y-1/2 
            after:w-[10px] after:h-[2px] after:bg-white after:content-[''] 
            before:absolute before:left-1/2 before:top-1/2 before:-translate-x-1/2 before:-translate-y-1/2 
            before:h-[10px] before:w-[2px] before:bg-white before:content-['']"
            />
            <Handle
              type="source"
              position={Position.Right}
              isConnectable={isConnectable}
              className="!top-[calc(50%)] h-3 w-3 rounded-full !bg-indigo-500 relative 
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
      className={`${
        data.nodeType == "start"
          ? "w-24 h-24 rounded-l-[64px] rounded-r-2xl pl-[32px]"
          : data.nodeType == "loop"
          ? "w-28 h-36 rounded-t-[64px] rounded-b-3xl"
          : data.nodeType == "vlm"
          ? "w-42 h-32 rounded-4xl"
          : data.nodeType == "condition"
          ? "w-28 h-42 rounded-4xl"
          : "w-32 h-32 rounded-3xl"
      }   p-2 shadow-lg ${
        data.status === "failed"
          ? selected
            ? "border-3 border-red-600"
            : "border-2 border-red-500"
          : data.status === "pause"
          ? selected
            ? "border-2 border-red-600"
            : "border-1 border-red-500"
          : selected
          ? "border-2 border-indigo-500"
          : "border-1 border-white"
      } bg-white`}
    >
      {getHandles(data.nodeType)}
      <button
        onClick={(e) => {
          e.stopPropagation(); // 阻止事件冒泡
          deleteNode(id);
        }}
        className={`${
          data.nodeType == "start"
            ? "top-1 right-1"
            : data.nodeType == "loop"
            ? "top-5 right-5"
            : data.nodeType == "condition" || data.nodeType == "vlm"
            ? "top-3 right-3"
            : "top-2 right-2"
        } cursor-pointer absolute`}
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
        className={`${
          data.nodeType == "start"
            ? "h-[36%]  pr-2"
            : data.nodeType == "loop"
            ? "h-[36%] pt-[18%]"
            : "h-[36%] "
        } h-[40%] flex flex-col items-center justify-center gap-1`}
      >
        <div className="flex items-center justify-center gap-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="size-4 shrink-0"
          >
            <path
              fillRule="evenodd"
              d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z"
              clipRule="evenodd"
            />
          </svg>
          <span className="whitespace-nowrap">{data.nodeType}</span>
        </div>
        {data.debug && <div className="w-3 h-3 rounded-full bg-red-500"></div>}
        <div className="flex items-center justify-center gap-1">
          {data.isChatflowInput && (
            <div className="flex items-center justify-center w-full text-xs text-gray-500 gap-2">
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
                  d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                />
              </svg>
            </div>
          )}
          {data.isChatflowOutput && (
            <div className="flex items-center justify-center w-full text-xs text-gray-500 gap-2">
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
                  d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25"
                />
              </svg>
            </div>
          )}
          {data.useChatHistory && (
            <div className="flex items-center justify-center w-full text-xs text-gray-500 gap-2">
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
                  d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                />
              </svg>
            </div>
          )}
        </div>
      </div>
      <div
        className={`${
          data.nodeType == "loop"
            ? "h-[calc(64%-16px)] mt-1 mb-3"
            : data.nodeType == "condition"
            ? "h-[calc(60%-12px)] mt-1 mb-5"
            : "h-[calc(64%-12px)] mt-1 mb-3"
        } ${
          data.nodeType == "start"
            ? "mx-[calc(10%-8px)] mr-2"
            : "mx-[calc(20%-8px)]"
        } flex items-center justify-center rounded-3xl bg-gray-100`}
      >
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
        ) : data.status === "running" ? (
          <div className="animate-spin h-4 w-4 border-3 border-indigo-500 border-t-transparent rounded-full"></div>
        ) : data.status === "input" ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className="size-6 text-indigo-500"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
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
      <div
        // onBlur={(e) =>
        //   useFlowStore.getState().updateNodeLabel(id, e.currentTarget.innerText)
        // }
        className="absolute left-1/2 -translate-x-1/2 -top-1 -translate-y-[100%] flex items-center justify-center gap-1"
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
        <span className="whitespace-nowrap">{data.label}</span>
      </div>
      {data.nodeType === "vlm" && data.modelConfig && (
        <div className="mt-2 absolute left-1/2 -translate-x-1/2 flex items-center justify-center gap-1">
          <div className="flex flex-col mx-auto">
            <div className="rounded-xl flex flex-col item-center justify-center gap-1">
              <div className="w-full text-sm flex items-center justify-center gap-2 text-gray-500 pb-1">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-5"
                >
                  <path
                    fillRule="evenodd"
                    d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25Zm0 8.625a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25ZM15.375 12a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0ZM7.5 10.875a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25Z"
                    clipRule="evenodd"
                  />
                </svg>
                {data.modelConfig.modelName ? (
                  <div className="text-gray-500 whitespace-nowrap overflow-x-scroll scrollbar-hide ">
                    {data.modelConfig.modelName}
                  </div>
                ) : (
                  <div className="text-gray-500">No LLM engine was choosed</div>
                )}
              </div>
              {data.modelConfig.baseUsed?.length > 0 ? (
                <div className="flex flex-col items-center justify-center w-full text-sm text-gray-500 gap-2">
                  <div className="px-10 flex items-center justify-center gap-1">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      className="size-5"
                    >
                      <path d="M10.75 16.82A7.462 7.462 0 0 1 15 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0 0 18 15.06v-11a.75.75 0 0 0-.546-.721A9.006 9.006 0 0 0 15 3a8.963 8.963 0 0 0-4.25 1.065V16.82ZM9.25 4.065A8.963 8.963 0 0 0 5 3c-.85 0-1.673.118-2.454.339A.75.75 0 0 0 2 4.06v11a.75.75 0 0 0 .954.721A7.506 7.506 0 0 1 5 15.5c1.579 0 3.042.487 4.25 1.32V4.065Z" />
                    </svg>
                    <div className="whitespace-nowrap">
                      Knowledge-Base accessed:
                    </div>
                  </div>

                  <div className="flex gap-2 items-center justify-center flex-wrap">
                    {data.modelConfig.baseUsed.map((base, index) => (
                      <div
                        className="flex gap-1 items-center justify-center break-all"
                        key={index}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          className="size-4 shrink-0"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4Zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37ZM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 0 1 3 13.179Z"
                            clipRule="evenodd"
                            transform="translate(0, -0.5)"
                          />
                        </svg>
                        <span className="break-words">{base.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center w-full text-sm text-gray-500 gap-2">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="size-5"
                  >
                    <path d="M10.75 16.82A7.462 7.462 0 0 1 15 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0 0 18 15.06v-11a.75.75 0 0 0-.546-.721A9.006 9.006 0 0 0 15 3a8.963 8.963 0 0 0-4.25 1.065V16.82ZM9.25 4.065A8.963 8.963 0 0 0 5 3c-.85 0-1.673.118-2.454.339A.75.75 0 0 0 2 4.06v11a.75.75 0 0 0 .954.721A7.506 7.506 0 0 1 5 15.5c1.579 0 3.042.487 4.25 1.32V4.065Z" />
                  </svg>
                  <div className="whitespace-nowrap">
                    No Knowledge-Base was accessed‌
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomNodeComponent;

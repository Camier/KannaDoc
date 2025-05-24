import MarkdownDisplay from "@/components/AiChat/MarkdownDisplay";
import PythonEditor from "@/components/Workflow/PythonEditor";
import { runPythonTest } from "@/lib/api/workflowApi";
import { useAuthStore } from "@/stores/authStore";
import { useFlowStore } from "@/stores/flowStore";
import { useGlobalStore } from "@/stores/pythonVariableStore";
import { CustomNode } from "@/types/types";
import { Dispatch, SetStateAction, useState } from "react";

interface FunctionNodeProps {
  saveNode: (node: CustomNode) => void;
  isDebugMode: boolean;
  node: CustomNode;
  setCodeFullScreenFlow: Dispatch<SetStateAction<boolean>>;
  codeFullScreenFlow: boolean;
}

const FunctionNodeComponent: React.FC<FunctionNodeProps> = ({
  saveNode,
  isDebugMode,
  node,
  setCodeFullScreenFlow,
  codeFullScreenFlow,
}) => {
  const {
    globalVariables,
    globalDebugVariables,
    addProperty,
    removeProperty,
    updateProperty,
    updateDebugProperty,
  } = useGlobalStore();
  const [variable, setVariable] = useState("");
  const [packageName, setPackageName] = useState("");
  const { user } = useAuthStore();
  const {
    updateNodeLabel,
    updateOutput,
    updatePackageInfos,
    removePackageInfos,
    updateImageUrl,
    updateDebug,
    updateDescription,
  } = useFlowStore();
  const [runTest, setRunTest] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const handleVariableChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    isDebugMode: boolean
  ) => {
    const { name, value } = e.target;
    isDebugMode
      ? updateDebugProperty(name, value)
      : updateProperty(name, value);
  };

  const handleUpdatePackageInfos = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    updatePackageInfos(node.id, name, value);
  };
  const handleUpdateImageUrl = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    updateImageUrl(node.id, value);
  };
  const handleRunTest = async () => {
    if (user?.name) {
      setRunTest(true);
      updateOutput(node.id, "Code Running...");
      try {
        const response = await runPythonTest(user.name, node, globalVariables);
        const id = node.id;
        if (response.data.code === 0) {
          updateOutput(node.id, response.data.result[id][0].result);
        } else {
          updateOutput(node.id, response.data.msg);
        }
      } catch (error) {
        console.error("Error connect:", error);
        updateOutput(node.id, "Error connect:" + error);
      } finally {
        setRunTest(false);
      }
    }
  };

  return (
    <div
      className={`overflow-scroll h-full flex flex-col items-start justify-start gap-1`}
    >
      <div className="px-2 py-1 flex items-center justify-between w-full mt-1 font-medium">
        <div className="text-xl flex items-center justify-start max-w-[60%] gap-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className="size-6 shrink-0"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
            />
          </svg>
          <div
            contentEditable
            suppressContentEditableWarning // 避免React警告
            className="focus:outline-none cursor-text overflow-auto whitespace-nowrap" // 移除聚焦时的默认轮廓
            onBlur={(e) => {
              if (e.currentTarget.innerText.length > 1) {
                return updateNodeLabel(node.id, e.currentTarget.innerText);
              } else {
                e.currentTarget.innerText = node.data.label;
              }
            }}
            onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
              if (e.key === "Enter") {
                // 按下回车时保存并退出编辑模式
                e.preventDefault();
                e.currentTarget.blur();
              }
            }}
          >
            {node.data.label}
          </div>
        </div>
        <button
          onClick={() => saveNode(node)}
          className="cursor-pointer disabled:cursor-not-allowed py-2 px-3 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="size-5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
            />
          </svg>
          <span className="whitespace-nowrap">Save Node</span>
        </button>
      </div>
      <details className="group w-full" open>
        <summary className="flex items-center cursor-pointer font-medium w-full">
          <div className="py-1 px-2 flex mt-1 items-center justify-between w-full font-medium">
            <div className="flex items-center justify-start gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M2.25 5.25a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3V15a3 3 0 0 1-3 3h-3v.257c0 .597.237 1.17.659 1.591l.621.622a.75.75 0 0 1-.53 1.28h-9a.75.75 0 0 1-.53-1.28l.621-.622a2.25 2.25 0 0 0 .659-1.59V18h-3a3 3 0 0 1-3-3V5.25Zm1.5 0v7.5a1.5 1.5 0 0 0 1.5 1.5h13.5a1.5 1.5 0 0 0 1.5-1.5v-7.5a1.5 1.5 0 0 0-1.5-1.5H5.25a1.5 1.5 0 0 0-1.5 1.5Z"
                  clipRule="evenodd"
                />
              </svg>
              Description
              <svg
                className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
              onClick={(e) => {
                e.preventDefault();
                setIsEditing(!isEditing);
              }}
              className="hover:bg-indigo-500 hover:text-white cursor-pointer disabled:cursor-not-allowed py-2 px-3 rounded-full disabled:opacity-50"
            >
              {isEditing ? (
                <div className="flex items-center justify-center gap-1">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="1.5"
                    stroke="currentColor"
                    className="size-5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 0 1-2.25 2.25M16.5 7.5V18a2.25 2.25 0 0 0 2.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 0 0 2.25 2.25h13.5M6 7.5h3v3H6v-3Z"
                    />
                  </svg>
                  <span>Preview</span>
                </div>
              ) : (
                <div className="flex items-center justify-center gap-1">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="1.5"
                    stroke="currentColor"
                    className="size-5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                    />
                  </svg>
                  <span>Edit</span>
                </div>
              )}
            </button>
          </div>
        </summary>

        {isEditing ? (
          <div
            className={`rounded-2xl shadow-lg overflow-scroll w-full mb-2 p-4 bg-white`}
          >
            <textarea
              className={`mt-1 w-full px-2 py-2 border border-gray-200 rounded-xl min-h-[10vh] ${
                codeFullScreenFlow ? "max-h-[50vh]" : "max-h-[30vh]"
              } resize-none overflow-y-auto focus:outline-hidden focus:ring-2 focus:ring-indigo-500`}
              value={node.data.description || ""}
              onChange={(e) => updateDescription(node.id, e.target.value)}
              placeholder="Enter Markdown content here..."
            />
          </div>
        ) : (
          <div
            className={`rounded-2xl shadow-lg overflow-scroll w-full mb-2 p-4 bg-gray-100`}
          >
            <MarkdownDisplay
              md_text={node.data.description || "No decription found"}
              message={{
                type: "text",
                content: node.data.description || "",
                from: "ai",
              }}
              showTokenNumber={true}
              isThinking={false}
            />
          </div>
        )}
      </details>
      <details className="group w-full" open>
        <summary className="flex items-center cursor-pointer font-medium w-full">
          <div className="px-2 py-1 flex items-center justify-between w-full mt-1">
            <div className="flex items-center justify-center gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M19.253 2.292a.75.75 0 0 1 .955.461A28.123 28.123 0 0 1 21.75 12c0 3.266-.547 6.388-1.542 9.247a.75.75 0 1 1-1.416-.494c.94-2.7 1.458-5.654 1.458-8.753s-.519-6.054-1.458-8.754a.75.75 0 0 1 .461-.954Zm-14.227.013a.75.75 0 0 1 .414.976A23.183 23.183 0 0 0 3.75 12c0 3.085.6 6.027 1.69 8.718a.75.75 0 0 1-1.39.563c-1.161-2.867-1.8-6-1.8-9.281 0-3.28.639-6.414 1.8-9.281a.75.75 0 0 1 .976-.414Zm4.275 5.052a1.5 1.5 0 0 1 2.21.803l.716 2.148L13.6 8.246a2.438 2.438 0 0 1 2.978-.892l.213.09a.75.75 0 1 1-.584 1.381l-.214-.09a.937.937 0 0 0-1.145.343l-2.021 3.033 1.084 3.255 1.445-.89a.75.75 0 1 1 .786 1.278l-1.444.889a1.5 1.5 0 0 1-2.21-.803l-.716-2.148-1.374 2.062a2.437 2.437 0 0 1-2.978.892l-.213-.09a.75.75 0 0 1 .584-1.381l.214.09a.938.938 0 0 0 1.145-.344l2.021-3.032-1.084-3.255-1.445.89a.75.75 0 1 1-.786-1.278l1.444-.89Z"
                  clipRule="evenodd"
                />
              </svg>
              Global Variable
              <svg
                className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
              className="cursor-pointer disabled:cursor-not-allowed px-4 py-2 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
              onClick={() => setCodeFullScreenFlow((prev: boolean) => !prev)}
            >
              {codeFullScreenFlow ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-6"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 9V4.5M9 9H4.5M9 9 3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5 5.25 5.25"
                  />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-6"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                  />
                </svg>
              )}
            </button>
          </div>
        </summary>
        <div
          className={`space-y-2 p-4 rounded-2xl shadow-lg ${
            codeFullScreenFlow ? "w-full" : "w-full"
          }`}
        >
          <div className="flex items-center w-full px-2 gap-6 border-gray-200">
            <input
              name={"addVariable"}
              value={variable}
              placeholder="Variable Name"
              onChange={(e) => setVariable(e.target.value)}
              className="w-full px-3 py-1 border-2 border-gray-200 rounded-xl
              focus:outline-none focus:ring-2 focus:ring-indigo-500
              disabled:opacity-50"
              onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
                if (e.key === "Enter") {
                  // 按下回车时保存并退出编辑模式
                  e.preventDefault();
                  if (variable === "") {
                    return;
                  } else {
                    addProperty(variable, "");
                    setVariable("");
                  }
                }
              }}
            />
            <div
              onClick={() => {
                if (variable === "") {
                  return;
                } else {
                  addProperty(variable, "");
                  setVariable("");
                }
              }}
              className="whitespace-nowrap cursor-pointer hover:text-indigo-700 pr-2 flex items-center gap-1 text-indigo-500"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M12 3.75a.75.75 0 0 1 .75.75v6.75h6.75a.75.75 0 0 1 0 1.5h-6.75v6.75a.75.75 0 0 1-1.5 0v-6.75H4.5a.75.75 0 0 1 0-1.5h6.75V4.5a.75.75 0 0 1 .75-.75Z"
                  clipRule="evenodd"
                />
              </svg>
              <span>Click to Add</span>
            </div>
          </div>
          {Object.keys(
            isDebugMode ? globalDebugVariables : globalVariables
          ).map((key) => {
            // 获取当前值和初始值
            const currentValue = isDebugMode
              ? globalDebugVariables[key]
              : globalVariables[key];
            const initialValue = globalVariables[key];

            // 判断是否是未修改状态
            const isUnchanged = isDebugMode && currentValue === initialValue;
            return (
              <div className="px-2 flex w-full items-center gap-2" key={key}>
                <div className="max-w-[50%] whitespace-nowrap overflow-scroll">
                  {key}
                </div>
                <div>=</div>
                {/* 输入框容器添加相对定位 */}
                <div className="flex-1 relative">
                  <input
                    name={key}
                    value={currentValue}
                    onChange={(e) => handleVariableChange(e, isDebugMode)}
                    className={`w-full px-3 py-1 border-2 rounded-xl border-gray-200
            focus:outline-none focus:ring-2 focus:ring-indigo-500
            disabled:opacity-50 ${
              isUnchanged ? "text-gray-400" : "text-black"
            }`}
                    onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                      if (e.key === "Enter") e.currentTarget.blur();
                    }}
                  />
                  {/* 初始值提示（仅在调试模式且未修改时显示） */}
                  {isDebugMode && (
                    <div className="absolute right-1 top-0 px-3 py-1 pointer-events-none text-gray-400">
                      Init: {initialValue}
                    </div>
                  )}
                </div>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-5 text-indigo-500 cursor-pointer shrink-0"
                  onClick={() => removeProperty(key)}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                  />
                </svg>
              </div>
            );
          })}
        </div>
      </details>
      <details className="group w-full" open>
        <summary className="flex items-center cursor-pointer font-medium w-full">
          <div className="px-2 py-1 flex items-center justify-between w-full mt-1">
            <div className="flex items-center justify-center gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M7.5 5.25a3 3 0 0 1 3-3h3a3 3 0 0 1 3 3v.205c.933.085 1.857.197 2.774.334 1.454.218 2.476 1.483 2.476 2.917v3.033c0 1.211-.734 2.352-1.936 2.752A24.726 24.726 0 0 1 12 15.75c-2.73 0-5.357-.442-7.814-1.259-1.202-.4-1.936-1.541-1.936-2.752V8.706c0-1.434 1.022-2.7 2.476-2.917A48.814 48.814 0 0 1 7.5 5.455V5.25Zm7.5 0v.09a49.488 49.488 0 0 0-6 0v-.09a1.5 1.5 0 0 1 1.5-1.5h3a1.5 1.5 0 0 1 1.5 1.5Zm-3 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
                  clipRule="evenodd"
                />
                <path d="M3 18.4v-2.796a4.3 4.3 0 0 0 .713.31A26.226 26.226 0 0 0 12 17.25c2.892 0 5.68-.468 8.287-1.335.252-.084.49-.189.713-.311V18.4c0 1.452-1.047 2.728-2.523 2.923-2.12.282-4.282.427-6.477.427a49.19 49.19 0 0 1-6.477-.427C4.047 21.128 3 19.852 3 18.4Z" />
              </svg>
              Pip Dependencies
              <svg
                className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
        <div
          className={`space-y-2 p-4 rounded-2xl shadow-lg ${
            codeFullScreenFlow ? "w-full" : "w-full"
          }`}
        >
          <div className="flex items-center w-full px-2 pb-2 gap-6 text-gray-500">
            Install dependencies once per workflow on a single node – no
            redundant installations across other nodes needed.
          </div>
          <div className="flex items-center w-full px-2 gap-6 border-gray-200">
            <input
              name={"addPackage"}
              value={packageName}
              placeholder="Package Name"
              onChange={(e) => setPackageName(e.target.value)}
              className="w-full px-3 py-1 border-2 border-gray-200 rounded-xl
              focus:outline-none focus:ring-2 focus:ring-indigo-500
              disabled:opacity-50"
              onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
                if (e.key === "Enter") {
                  // 按下回车时保存并退出编辑模式
                  e.preventDefault();
                  if (packageName === "") {
                    return;
                  } else {
                    if (node?.data.pip?.hasOwnProperty(packageName)) {
                      alert(`Package ${packageName} already exists`);
                      return;
                    }
                    updatePackageInfos(node.id, packageName, "");
                    setPackageName("");
                  }
                }
              }}
            />
            <div
              onClick={() => {
                if (packageName === "") {
                  return;
                } else {
                  if (node?.data.pip?.hasOwnProperty(packageName)) {
                    alert(`Package ${packageName} already exists`);
                    return;
                  }
                  updatePackageInfos(node.id, packageName, "");
                  setVariable("");
                }
              }}
              className="whitespace-nowrap cursor-pointer hover:text-indigo-700 pr-2 flex items-center gap-1 text-indigo-500"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M12 3.75a.75.75 0 0 1 .75.75v6.75h6.75a.75.75 0 0 1 0 1.5h-6.75v6.75a.75.75 0 0 1-1.5 0v-6.75H4.5a.75.75 0 0 1 0-1.5h6.75V4.5a.75.75 0 0 1 .75-.75Z"
                  clipRule="evenodd"
                />
              </svg>
              <span>Click to Add</span>
            </div>
          </div>
          <div className="px-2 flex w-full items-center gap-2">
            <div className="max-w-[50%] whitespace-nowrap overflow-scroll">
              Mirror Url
            </div>
            <div>=</div>
            <input
              name={"imageUrl"}
              value={node.data.imageUrl ? node.data.imageUrl : ""}
              onChange={handleUpdateImageUrl}
              placeholder="Optional"
              onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
                if (e.key === "Enter") {
                  // 按下回车时保存并退出编辑模式
                  e.preventDefault();
                  e.currentTarget.blur();
                }
              }}
              className="flex-1 w-full px-3 py-1 border-2 border-gray-200 rounded-xl
              focus:outline-none focus:ring-2 focus:ring-indigo-500
              disabled:opacity-50"
            />
          </div>
          {node.data.pip && (
            <div className="space-y-2">
              {Object.keys(node.data.pip).map((key) => (
                <div className="px-2 flex w-full items-center gap-2" key={key}>
                  <div className="max-w-[50%] whitespace-nowrap overflow-scroll">
                    {key}
                  </div>
                  <div>==</div>
                  <input
                    name={key}
                    value={node.data.pip ? node.data.pip[key] : ""}
                    onChange={handleUpdatePackageInfos}
                    placeholder="Default Package Version"
                    onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
                      if (e.key === "Enter") {
                        // 按下回车时保存并退出编辑模式
                        e.preventDefault();
                        e.currentTarget.blur();
                      }
                    }}
                    className="flex-1 w-full px-3 py-1 border-2 border-gray-200 rounded-xl
              focus:outline-none focus:ring-2 focus:ring-indigo-500
              disabled:opacity-50"
                  />
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="1.5"
                    stroke="currentColor"
                    className="size-5 text-indigo-500 cursor-pointer shrink-0"
                    onClick={() => removePackageInfos(node.id, key)}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                    />
                  </svg>
                </div>
              ))}
            </div>
          )}
        </div>
      </details>
      <details className="group w-full" open>
        <summary className="flex items-center cursor-pointer font-medium w-full">
          <div className="py-1 px-2 flex mt-1 items-center justify-between w-full font-medium">
            <div className="flex items-center justify-start gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M2.25 6a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3V6Zm3.97.97a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06l-2.25 2.25a.75.75 0 0 1-1.06-1.06l1.72-1.72-1.72-1.72a.75.75 0 0 1 0-1.06Zm4.28 4.28a.75.75 0 0 0 0 1.5h3a.75.75 0 0 0 0-1.5h-3Z"
                  clipRule="evenodd"
                />
              </svg>
              Code Editor{" "}
              <svg
                className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
              className="cursor-pointer disabled:cursor-not-allowed py-2 px-3 rounded-full hover:bg-indigo-500 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-5"
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
        <div className={`rounded-2xl shadow-lg overflow-scroll w-full mb-2`}>
          <PythonEditor node={node} />
        </div>
      </details>
      <details className="group w-full" open>
        <summary className="flex items-center cursor-pointer font-medium w-full">
          <div className="py-1 px-2 flex mt-1 items-center justify-between w-full font-medium">
            <div className="flex items-center justify-start gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-5"
              >
                <path
                  fillRule="evenodd"
                  d="M2.25 5.25a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3V15a3 3 0 0 1-3 3h-3v.257c0 .597.237 1.17.659 1.591l.621.622a.75.75 0 0 1-.53 1.28h-9a.75.75 0 0 1-.53-1.28l.621-.622a2.25 2.25 0 0 0 .659-1.59V18h-3a3 3 0 0 1-3-3V5.25Zm1.5 0v7.5a1.5 1.5 0 0 0 1.5 1.5h13.5a1.5 1.5 0 0 0 1.5-1.5v-7.5a1.5 1.5 0 0 0-1.5-1.5H5.25a1.5 1.5 0 0 0-1.5 1.5Z"
                  clipRule="evenodd"
                />
              </svg>
              Output
              <svg
                className="ml-1 w-4 h-4 transition-transform group-open:rotate-180"
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
              onClick={() => {
                updateDebug(node.id, node.data.debug ? !node.data.debug : true);
              }}
              disabled={runTest}
              className={`${
                node.data.debug
                  ? "bg-red-500 text-white hover:bg-red-700"
                  : "hover:bg-indigo-500 hover:text-white"
              } cursor-pointer disabled:cursor-not-allowed py-2 px-3 rounded-full disabled:opacity-50 flex items-center justify-center gap-1`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="size-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 12.75c1.148 0 2.278.08 3.383.237 1.037.146 1.866.966 1.866 2.013 0 3.728-2.35 6.75-5.25 6.75S6.75 18.728 6.75 15c0-1.046.83-1.867 1.866-2.013A24.204 24.204 0 0 1 12 12.75Zm0 0c2.883 0 5.647.508 8.207 1.44a23.91 23.91 0 0 1-1.152 6.06M12 12.75c-2.883 0-5.647.508-8.208 1.44.125 2.104.52 4.136 1.153 6.06M12 12.75a2.25 2.25 0 0 0 2.248-2.354M12 12.75a2.25 2.25 0 0 1-2.248-2.354M12 8.25c.995 0 1.971-.08 2.922-.236.403-.066.74-.358.795-.762a3.778 3.778 0 0 0-.399-2.25M12 8.25c-.995 0-1.97-.08-2.922-.236-.402-.066-.74-.358-.795-.762a3.734 3.734 0 0 1 .4-2.253M12 8.25a2.25 2.25 0 0 0-2.248 2.146M12 8.25a2.25 2.25 0 0 1 2.248 2.146M8.683 5a6.032 6.032 0 0 1-1.155-1.002c.07-.63.27-1.222.574-1.747m.581 2.749A3.75 3.75 0 0 1 15.318 5m0 0c.427-.283.815-.62 1.155-.999a4.471 4.471 0 0 0-.575-1.752M4.921 6a24.048 24.048 0 0 0-.392 3.314c1.668.546 3.416.914 5.223 1.082M19.08 6c.205 1.08.337 2.187.392 3.314a23.882 23.882 0 0 1-5.223 1.082"
                />
              </svg>

              <span>Debug</span>
            </button>
          </div>
        </summary>
        <div
          className={`rounded-2xl shadow-lg overflow-scroll w-full mb-2 p-4 bg-gray-100`}
        >
          <MarkdownDisplay
            md_text={node.data.output || ""}
            message={{
              type: "text",
              content: node.data.output || "",
              from: "ai", // 消息的来源
            }}
            showTokenNumber={true}
            isThinking={false}
          />
        </div>
      </details>
    </div>
  );
};

export default FunctionNodeComponent;

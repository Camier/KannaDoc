import { Flow } from "@/types/types";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import ConfirmDialog from "../ConfirmDialog";

interface LeftSideBarProps {
  flows: Flow[];
  searchTerm: string;
  setShowCreateModal: Dispatch<SetStateAction<boolean>>;
  selectedFlow: string | null;
  setSelectedFlow: Dispatch<SetStateAction<string | null>>;
  ondeleteFlow: (flow: Flow) => void;
  onRenameWorkflow: (flow: Flow, WorkflowName: string) => void;
}

const LeftSideBar: React.FC<LeftSideBarProps> = ({
  flows,
  searchTerm,
  setShowCreateModal,
  selectedFlow,
  setSelectedFlow,
  ondeleteFlow,
  onRenameWorkflow,
}) => {
  useEffect(() => {
    setSettingsOpen(new Array(flows.length).fill(false));
    setIsEditOpen(new Array(flows.length).fill(false));
    setInputValues(flows.map((flow) => flow.name));
  }, [flows]);

  const [isSettingsOpen, setSettingsOpen] = useState<boolean[]>([]);
  const [inputValues, setInputValues] = useState<string[]>([]);
  const [isEditOpen, setIsEditOpen] = useState<boolean[]>([]);
  const [showConfirmDeleteFlow, setShowConfirmDeleteFlow] = useState<{
    index: number;
    flow: Flow;
  } | null>(null);

  // 过滤知识库
  const filteredFlows = flows.filter((flow) =>
    flow.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDeleteFlow = (flow: Flow, index: number) => {
    setShowConfirmDeleteFlow({ index, flow }); // 显示单个对话框
  };

  const confirmDeleteFlow = () => {
    if (showConfirmDeleteFlow) {
      ondeleteFlow(showConfirmDeleteFlow.flow);
      toggleSettings(showConfirmDeleteFlow.index); // 关闭设置面板
      setShowConfirmDeleteFlow(null); // 关闭对话框
    }
  };

  const cancelDeleteFlow = () => {
    if (showConfirmDeleteFlow) {
      toggleSettings(showConfirmDeleteFlow.index); // 关闭设置面板
      setShowConfirmDeleteFlow(null); // 关闭对话框
    }
  };

  const toggleSettings = (index: number) => {
    setSettingsOpen(
      (prev) => prev.map((item, idx) => (idx === index ? !item : false)) // 只切换当前项
    );
  };

  const handleEditFlow = (index: number) => {
    toggleSettings(index);
    setIsEditOpen(
      (prev) => prev.map((item, idx) => (idx === index ? !item : false)) // 只切换当前项
    );
  };

  const handleBlur = (flow: Flow, index: number) => {
    if (
      inputValues[index].trim() !== "" &&
      inputValues[index].trim() !== flow.name
    ) {
      onRenameWorkflow(flow, inputValues[index]);
    } else {
      inputValues[index] = flow.name;
    }
    setIsEditOpen(
      (prev) => prev.map((item, idx) => (idx === index ? !item : false)) // 只切换当前项
    );
  };

  const handleChange = (
    index: number,
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newInputValues = [...inputValues];
    newInputValues[index] = e.target.value; // 更新输入框的值
    setInputValues(newInputValues); // 设置新的输入值
  };

  return (
    <div className="w-[15%] flex-none flex flex-col gap-4 h-full">
      <div className="px-4 flex items-center justify-center h-[10%]">
        <button
          onClick={() => setShowCreateModal(true)}
          className="w-full py-2 px-4 bg-indigo-500 text-white hover:bg-indigo-700 transition-colors rounded-full"
        >
          <div className="flex items-center justify-center gap-1 cursor-pointer">
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
            <span>Add Work-Flow</span>
          </div>
        </button>
      </div>

      <div className="w-full bg-white rounded-2xl overflow-scroll min-h-[90%] max-h-[90%] scrollbar-hide p-2">
        {filteredFlows.map((flow, index) => (
          <div
            key={index}
            className={`py-2 my-2 hover:bg-indigo-600 group cursor-pointer rounded-3xl flex justify-between items-start ${
              selectedFlow === flow.flowId ? "bg-indigo-500" : ""
            }`}
          >
            <div
              className={`flex-1 gap-2 hover:text-white w-full ${
                flow.flowId === "1" ? "cursor-not-allowed" : ""
              }`}
              onClick={() => {
                if (flow.flowId === "1") {
                  return;
                }
                return setSelectedFlow(flow.flowId);
              }}
            >
              <div className="flex relative">
                <div
                  className={`px-3 flex items-center gap-2 text-gray-900 w-[80%] ${
                    selectedFlow === flow.flowId
                      ? "text-white text-lg"
                      : "text-base group-hover:text-white"
                  }`}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className={`${
                      selectedFlow === flow.flowId ? "size-6" : "size-5"
                    }  shrink-0`}
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.161 2.58a1.875 1.875 0 0 1 1.678 0l4.993 2.498c.106.052.23.052.336 0l3.869-1.935A1.875 1.875 0 0 1 21.75 4.82v12.485c0 .71-.401 1.36-1.037 1.677l-4.875 2.437a1.875 1.875 0 0 1-1.676 0l-4.994-2.497a.375.375 0 0 0-.336 0l-3.868 1.935A1.875 1.875 0 0 1 2.25 19.18V6.695c0-.71.401-1.36 1.036-1.677l4.875-2.437ZM9 6a.75.75 0 0 1 .75.75V15a.75.75 0 0 1-1.5 0V6.75A.75.75 0 0 1 9 6Zm6.75 3a.75.75 0 0 0-1.5 0v8.25a.75.75 0 0 0 1.5 0V9Z"
                      clipRule="evenodd"
                    />
                  </svg>

                  <div
                    className={`${
                      selectedFlow === flow.flowId ? "text-lg" : "text-base"
                    } whitespace-nowrap overflow-hidden`}
                  >
                    {isEditOpen[index] ? (
                      <input
                        type="text"
                        value={inputValues[index]} // 使用状态中的输入值
                        onChange={(e) => handleChange(index, e)} // 更新输入值
                        onBlur={() => handleBlur(flow, index)}
                        className="bg-transparent outline-hidden border-none p-0 m-0 w-full"
                        autoFocus
                      />
                    ) : (
                      flow.name
                    )}
                  </div>
                </div>
                {/* 重命名和删除 */}
                <div
                  className="w-[20%] flex items-center justify-center font-semibold cursor-pointer text-white"
                  onClick={() => toggleSettings(index)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className={`${
                      selectedFlow === flow.flowId ? "size-6" : "size-5"
                    }`}
                  >
                    <path d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" />
                  </svg>
                </div>
                {isSettingsOpen[index] && ( // 根据数组状态显示悬浮框
                  <div className="absolute right-0 top-full mt-1 bg-white text-black rounded-2xl border-2 py-2 px-1 border-slate-200 shadow-lg z-10">
                    <div
                      className="flex gap-2 cursor-pointer hover:bg-indigo-600 hover:text-white px-2 py-1 rounded-xl"
                      onClick={() => handleEditFlow(index)}
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
                          d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
                        />
                      </svg>

                      <div className="text-sm">Rename</div>
                    </div>
                    <div
                      className="flex gap-2 cursor-pointer hover:bg-indigo-600 hover:text-white px-2 py-1 rounded-xl"
                      onClick={() => handleDeleteFlow(flow, index)}
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
                          d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                        />
                      </svg>
                      <div className="text-sm">Delete</div>
                    </div>
                  </div>
                )}
              </div>
              <p
                className={`px-4 text-sm text-gray-500 ${
                  selectedFlow === flow.flowId ? "text-white" : "group-hover:text-white"
                }`}
              >
                {flow.lastModifyTime}
              </p>
            </div>
          </div>
        ))}
      </div>
      {showConfirmDeleteFlow && (
        <ConfirmDialog
          message={`Confirm the deletion of work-flow "${showConfirmDeleteFlow.flow.name}"？`}
          onConfirm={confirmDeleteFlow}
          onCancel={cancelDeleteFlow}
        />
      )}
    </div>
  );
};

export default LeftSideBar;

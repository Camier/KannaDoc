"use client";

import Navbar from "@/components/NavbarComponents/Navbar";
import AddWorkFlow from "@/components/WorkFlow/AddWorkFlow";
import FlowEditor from "@/components/WorkFlow/FlowEditor";
import LeftSideBar from "@/components/WorkFlow/LeftSideBar";
import TopBar from "@/components/WorkFlow/TopBar";
import withAuth from "@/middlewares/withAuth";

// import FlowWorkDetails from "@/components/FlowWork/FlowWorkDetails";
// import LeftSideBar from "@/components/WorkFlow/LeftSideBar";
// import TopBar from "@/components/WorkFlow/TopBar";
// import Navbar from "@/components/NavbarComponents/Navbar";
// import {
//   createFlowWork,
//   deleteFlowWork,
//   getAllFlowWork,
//   renameFlowWork,
//   uploadFiles,
// } from "@/lib/api/workFlowApi";
// import withAuth from "@/middlewares/withAuth";
import { useAuthStore } from "@/stores/authStore";
import { Flow, UploadFile } from "@/types/types";
// import { getFileExtension } from "@/utils/file";
import { useState, useEffect, useCallback } from "react";
// import Cookies from "js-cookie";
// import { EventSourceParserStream } from "eventsource-parser/stream";
// import AddWorkFlow from "@/components/WorkFlow/AddWorkFlow";

const FlowWork = () => {
  const [selectedFlow, setSelectedFlow] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [flows, setFlows] = useState<Flow[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFlowName, setNewFlowName] = useState("");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const { user } = useAuthStore();
  const [refresh, setRefresh] = useState<boolean>(false);
  const [fullScreenFlow, setFullScreenFlow] = useState<boolean>(false);
  // const [uploadProgress, setUploadProgress] = useState<number | null>(0);
  // const [taskStatus, setTaskStatus] = useState<
  //   "processing" | "completed" | "failed" | null
  // >(null);
  // const [taskProgress, setTaskProgress] = useState<number>(0);
  // const [uploadFile, setUploadFile] = useState<boolean>(false);
  // const [load, setLoad] = useState(true);

  // // 修改发送按钮逻辑
  // const isUploadComplete = uploadProgress === 100;
  // const isTaskComplete = taskStatus === "completed";
  // const isSendDisabled = (!isUploadComplete || !isTaskComplete) && uploadFile;

  // let buttonText;
  // if (!uploadFile) {
  //   buttonText = "Upload Files";
  // } else if (!isUploadComplete) {
  //   buttonText = `Upload:${uploadProgress}%`;
  // } else if (!isTaskComplete) {
  //   buttonText =
  //     taskStatus === "failed" ? "Upload Failed" : `Processing:${taskProgress}%`;
  // } else {
  //   buttonText = "Upload Files";
  // }

  // 成功消息自动消失
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // // 支持的文件类型
  // const supportedExtensions = ["doc","docx","pdf","ppt","pptx"];

  // // Wrap fetchAllFlowWork with useCallback
  // const fetchAllFlowWork = useCallback(async () => {
  //   if (user?.name) {
  //     try {
  //       const response = await getAllFlowWork(user.name);
  //       const Flows: Flow[] = response.data.map((item: any) => ({
  //         name: item.work_flow_name,
  //         flowId: item.work_flow_id,
  //         lastModityTime: item.last_modify_at.split("T")[0],
  //         createTime: item.created_at.split("T")[0],
  //         fileNumber: item.file_number,
  //       }));
  //       setFlows(flows);
  //     } catch (error) {
  //       console.error("Error fetching chat history:", error);
  //     }
  //   }
  // }, [user?.name]); // Add dependencies

  // useEffect(() => {
  //   fetchAllFlowWork();
  // }, [user?.name, refresh, fetchAllFlowWork]); // Add fetchAllFlowWork

  // 创建工作流校验
  const handleCreateConfirm = async () => {
    if (!newFlowName.trim()) {
      setNameError("Work-Flow name can not be null!");
      return;
    }
    if (flows.some((flow) => flow.name === newFlowName)) {
      setNameError("Work-Flow name already exist!");
      return;
    }

    if (user?.name) {
      try {
        setFlows((prevFlow: Flow[]) => {
          return [
            {
              name: "加载中...",
              flowId: "1",
              lastModityTime: "加载中...",
              createTime: "加载中...",
              fileNumber: 0,
            },
            ...prevFlow,
          ];
        });
        setShowCreateModal(false);
        setNewFlowName("");
        setNameError(null);
        //const response = await createFlowWork(user.name, newFlowName);
        setSelectedFlow(null);
      } catch (error) {
        console.error("Error fetching chat history:", error);
      }
    }
    setRefresh((pre) => !pre);
  };

  // 删除工作流
  const handledeleteFlow = async (flow: Flow) => {
    if (user?.name) {
      try {
        setFlows((prevFlow: Flow[]) =>
          prevFlow.filter((c: { flowId: string }) => c.flowId !== flow.flowId)
        );
        //const response = await deleteFlowWork(flow.flowId);
      } catch (error) {
        console.error("Error delete Knowledge Flow:", error);
      }
      setSelectedFlow(null);
      setRefresh((pre) => !pre);
    }
  };

  const handleRenameWorkFlow = (flow: Flow, inputValue: string) => {
    const fetchRenameChat = async () => {
      if (user?.name) {
        try {
          setFlows((prevFlow: Flow[]) =>
            prevFlow.map((c) =>
              c.flowId === flow.flowId ? { ...c, name: inputValue } : c
            )
          );
          //await renameFlowWork(flow.flowId, inputValue);
          setRefresh((prev) => !prev);
        } catch (error) {
          console.error("Error fetching rename chat:", error);
        }
      }
    };
    fetchRenameChat(); // 调用获取聊天记录的函数
  };

  // const handleFileUpload = (filelist: FileList) => {
  //   const files = Array.from(filelist);
  //   const validFiles = files.filter((file) => {
  //     const ext = getFileExtension(file.name);
  //     return supportedExtensions.includes(ext);
  //   });

  //   const invalidFiles = files.filter((file) => {
  //     const ext = getFileExtension(file.name);
  //     return !supportedExtensions.includes(ext);
  //   });

  //   if (invalidFiles.length > 0) {
  //     alert(
  //       `Unsupport file type: \n${invalidFiles.map((f) => f.name).join("\n")}`
  //     );
  //   }

  //   if (validFiles.length > 0 && user?.name) {
  //     setUploadProgress(0); // 重置上传进度
  //     setTaskStatus(null); // 重置任务状态
  //     setUploadFile(true);

  //     if (user?.name && selectedFlow) {
  //       uploadFiles(files, selectedFlow, (percent) => {
  //         setUploadProgress(percent); // 更新上传进度
  //       })
  //         .then(async (response) => {
  //           // 使用fetch代替EventSource
  //           const token = Cookies.get("token"); // 确保已引入cookie库
  //           const taskId = response?.data.task_id;

  //           try {
  //             const response = await fetch(
  //               `${process.env.NEXT_PUBLIC_API_BASE_URL}/sse/task/${user.name}/${taskId}`,
  //               {
  //                 headers: {
  //                   Authorization: `Bearer ${token}`,
  //                 },
  //               }
  //             );

  //             if (!response.ok) throw new Error("Request failed");
  //             if (!response.body) return;

  //             // 使用EventSourceParserStream处理流
  //             const eventStream = response.body
  //               ?.pipeThrough(new TextDecoderStream())
  //               .pipeThrough(new EventSourceParserStream());

  //             const eventReader = eventStream.getReader();
  //             while (true) {
  //               const { done, value } = (await eventReader?.read()) || {};
  //               if (done) break;

  //               const payload = JSON.parse(value.data);
  //               // 处理事件数据
  //               if (payload.event === "progress") {
  //                 const progress = payload.total > 0 ? payload.progress : 0;

  //                 setTaskProgress(progress);
  //                 setTaskStatus(payload.status);

  //                 if (["completed", "failed"].includes(payload.status)) {
  //                   eventReader.cancel();
  //                   break;
  //                 }
  //               }
  //             }
  //             setFlows((prevFlows) =>
  //               prevFlows.map((flow) =>
  //                 flow.flowId === selectedFlow
  //                   ? {
  //                       ...flow,
  //                       fileNumber: flow.fileNumber + validFiles.length,
  //                     }
  //                   : flow
  //               )
  //             );
  //             setLoad((prev) => !prev);
  //           } catch (error) {
  //             console.error("SSE错误:", error);
  //             setTaskStatus("failed");
  //           }finally {
  //             setSelectedFlow(null);
  //           }
  //         })
  //         .catch((error) => {
  //           alert("Upload error");
  //         });
  //     }
  //   }
  // };

  return (
    <div className="overflow-hidden flex flex-col">
      <Navbar />
      <div className="absolute w-[96%] h-[91%] top-[7%] bg-white/10 left-[2%] rounded-3xl flex items-center justify-between shadow-2xl">
        <div className="w-full top-0 absolute px-6 pb-6 pt-2 h-full">
          {/* 新建工作流弹窗 */}
          {showCreateModal && (
            <AddWorkFlow
              setShowCreateModal={setShowCreateModal}
              nameError={nameError}
              setNameError={setNameError}
              newWorkFlowName={newFlowName}
              setNewWorkFlowName={setNewFlowName}
              onCreateConfirm={handleCreateConfirm}
            />
          )}

          {/* 成功提示 */}
          {successMessage && (
            <div className="w-[20%] text-center fixed top-[40%] left-[40%] bg-indigo-500 text-white px-4 py-2 rounded-lg shadow-lg animate-bounce">
              {successMessage}
            </div>
          )}

          {/* 顶部导航 */}
          {!fullScreenFlow && <TopBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />}

          <div className={`mx-auto px-4 pt-4 flex gap-6 ${fullScreenFlow? "h-full":"h-[88%]"}`}>
            {/* 左侧边栏 */}
            {!fullScreenFlow && <LeftSideBar
              flows={flows}
              searchTerm={searchTerm}
              setShowCreateModal={setShowCreateModal}
              selectedFlow={selectedFlow}
              setSelectedFlow={setSelectedFlow}
              ondeleteFlow={handledeleteFlow}
              onRenameWorkFlow={handleRenameWorkFlow}
            />}

            {/* 右侧内容区 */}
            <FlowEditor setFullScreenFlow={setFullScreenFlow} fullScreenFlow={fullScreenFlow}/>
            {/* <FlowWorkDetails
              flows={flows}
              setFlows={setFlows}
              selectedFlow={selectedFlow}
              setSelectedFlow={setSelectedFlow}
              onFileUpload={handleFileUpload}
              buttonText={buttonText}
              isSendDisabled={isSendDisabled}
              load={load}
              setLoad={setLoad}
            /> */}
          </div>
        </div>
      </div>
    </div>
  );
};

export default withAuth(FlowWork);

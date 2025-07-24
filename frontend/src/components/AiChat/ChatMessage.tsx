// components/ChatMessage.tsx
"use client";
import React, { Dispatch, useMemo, useState } from "react";
import { FileRespose, Message, ModelConfig } from "@/types/types";
import Image from "next/image";
import LoadingCircle from "./LoadingCircle";
import { getFileIcon } from "@/utils/file";
import MarkdownDisplay from "./MarkdownDisplay";
import { createPortal } from "react-dom";

interface ChatMessageProps {
  modelConfig: ModelConfig | undefined;
  message: Message;
  showRefFile: string[];
  setShowRefFile: Dispatch<React.SetStateAction<string[]>>;
  onSendEditingMessage?: (
    inputMessage: string,
    sendingFiles: FileRespose[],
    tempBaseId: string,
    parentMessageId: string
  ) => void;
  lastUserMessage?: () => string; // 最后一条用户消息
  sendDisabled?: boolean; // 是否禁用发送按钮
  enableOperation?: boolean; // 是否启用操作栏
  handleBranchChange?: (parentId: string, newIndex: number) => void;
  branchIndex?: number; // 当前分支
  branchCount?: number; // 分支数量
  parentId?: string; // 父消息ID，用于分支切换
  isLastMessage?: boolean // 判断是否为最后一条消息
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  modelConfig,
  message,
  showRefFile,
  setShowRefFile,
  lastUserMessage = () => "",
  sendDisabled = false,
  onSendEditingMessage = () => {},
  enableOperation = false,
  handleBranchChange = () => {},
  branchIndex = 1, // 当前分支索引
  branchCount = 5, // 分支总数
  parentId = "root", // 父消息ID，用于分支切换
  isLastMessage = false
}) => {
  const isUser = message.from === "user"; // 判断是否是用户消息
  const [isOpen, setIsOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState("");
  const [copiedAll, setCopiedAll] = useState(false);
  const [messageEditing, setMessageEditing] = useState<boolean>(false);
  const [inputMessage, setInputMessage] = useState<string>(
    message.content || ""
  );

  // 提取thinking内容和剩余内容
  const { thinkingContent, displayContent } = useMemo(() => {
    let thinkingContent = "";
    let displayContent = message.content || "";

    // 仅处理文本类型的消息
    if (message.type === "text" && displayContent) {
      // 检查是否有<think>开头
      if (displayContent.startsWith("<think>")) {
        const endTagIndex = displayContent.indexOf("</think>");

        if (endTagIndex !== -1) {
          // 有闭合标签：提取思考内容
          thinkingContent = displayContent.substring(
            7, // "<think>" 长度
            endTagIndex
          );
          displayContent = displayContent.substring(endTagIndex + 8).trim(); // "</think>" 长度
        } else {
          // 没有闭合标签：整个内容作为思考内容
          thinkingContent = displayContent.substring(7);
          displayContent = "";
        }
      }
    }

    return { thinkingContent, displayContent };
  }, [message.content, message.type]);

  const handleImageClick = (selctImage: string) => {
    setSelectedImage(selctImage);
    setIsOpen(true);
  };

  const handleCloseModal = () => {
    setIsOpen(false);
  };

  const handleDownload = async (url: string) => {
    try {
      window.open(url, "_blank");
    } catch (error) {
      console.error("Download failed:", error);
      alert("Download failed!");
    }
  };

  // 复制全部内容的处理函数
  const handleCopyAll = async (md_text: string) => {
    // 直接使用原始的md_text（base64编码之前的内容）
    try {
      await navigator.clipboard.writeText(md_text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch (err) {
      // 降级方案：使用textarea
      const textArea = document.createElement("textarea");
      textArea.value = md_text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    }
  };

  return (
    <div className="w-full group">
      <div
        className={`m-1 rounded-3xl w-fit break-words flex flex-col 
        ${isUser ? "ml-auto max-w-[90%]" : "mr-auto max-w-[98%]"} ${
          isUser && message.type === "text"
            ? "" //"bg-indigo-300 shadow-lg"
            : message.type === "image"
            ? "bg-white mb-3 shadow-lg"
            : "bg-white mb-0.5"
        } ${
          message.type === "text"
            ? "px-4 py-2 mb-2 text-gray-800"
            : "overflow-hidden"
        }`}
      >
        {/* user message */}
        {message.type === "text" &&
          message.from === "user" &&
          message.content &&
          (messageEditing ? (
            <div className="flex flex-col gap-2">
              <div className="flex justify-center items-center h-full">
                <textarea
                  className="px-4 py-2 w-[50vw] min-h-[10vh] max-h-[20vh] border-indigo-500 border-2 rounded-3xl text-base focus:outline-hidden focus:border-indigo-600 focus:border-[2.5px] resize-none overflow-y-auto"
                  placeholder=""
                  value={inputMessage}
                  rows={1}
                  onChange={(e) => {
                    setInputMessage(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = e.target.scrollHeight + "px";
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.shiftKey) {
                      e.preventDefault();
                      if (!sendDisabled) {
                        onSendEditingMessage(
                          inputMessage,
                          [],
                          "",
                          message.parentMessageId || ""
                        );
                        setMessageEditing(false);
                      }
                    }
                  }}
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setMessageEditing(false);
                    setInputMessage(message.content || "");
                  }}
                  className="border border-gray-200 hover:bg-gray-100 cursor-pointer px-4 py-2 rounded-3xl"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (!sendDisabled) {
                      onSendEditingMessage(
                        inputMessage,
                        [],
                        "",
                        message.parentMessageId || ""
                      );
                      setMessageEditing(false);
                    }
                  }}
                  disabled={sendDisabled || inputMessage.trim() === ""}
                  className="bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 px-4 py-2 hover:bg-indigo-700 cursor-pointer text-white rounded-3xl"
                >
                  Send
                </button>
              </div>
            </div>
          ) : (
            <MarkdownDisplay
              md_text={message.content}
              message={message}
              showTokenNumber={false}
              isThinking={false}
            />
          ))}
        {/* AI thinking 1 */}
        {message.type === "text" && message.thinking && (
          <MarkdownDisplay
            md_text={message.thinking}
            message={message}
            showTokenNumber={false}
            isThinking={true}
          />
        )}
        {/* AI thinking 2 */}
        {message.type === "text" &&
          message.from === "ai" &&
          thinkingContent && (
            <MarkdownDisplay
              md_text={thinkingContent}
              message={message}
              showTokenNumber={false}
              isThinking={true}
            />
          )}
        {/* AI message */}
        {message.type === "text" && message.from === "ai" && displayContent && (
          <MarkdownDisplay
            md_text={displayContent}
            message={message}
            showTokenNumber={true}
            isThinking={false}
          />
        )}

        {/* 消息操作栏--复制、重试、切换等 */}
        {message.type === "text" && (
          <div
            className={`flex gap-2 items-center mt-3 text-sm text-gray-600 ${
              message.from === "user" ? "pr-2 justify-end" : "justify-start"
            }`}
          >
            {message.from === "ai" &&
              enableOperation &&
              !messageEditing &&
              branchCount > 1 && (
                <div className="flex gap-0.5 font-medium">
                  <button
                    className="cursor-pointer hover:text-gray-800 transition-colors disabled:cursor-not-allowed disabled:hover:text-gray-600  disabled:opacity-50"
                    onClick={() =>
                      handleBranchChange(parentId ?? "root", branchIndex - 1)
                    }
                    disabled={branchIndex === 0}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth="2"
                      stroke="currentColor"
                      className="size-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15.75 19.5 8.25 12l7.5-7.5"
                      />
                    </svg>
                  </button>
                  <span>{branchIndex + 1}</span>/<span>{branchCount}</span>
                  <button
                    className="cursor-pointer hover:text-gray-800 transition-colors disabled:cursor-not-allowed disabled:hover:text-gray-600  disabled:opacity-50"
                    onClick={() =>
                      handleBranchChange(parentId ?? "root", branchIndex + 1)
                    }
                    disabled={branchIndex === branchCount - 1}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth="2"
                      stroke="currentColor"
                      className="size-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="m8.25 4.5 7.5 7.5-7.5 7.5"
                      />
                    </svg>
                  </button>
                </div>
              )}
            {/* 复制全部按钮 - 只在非思考状态下显示 */}
            {(message.from === "ai" ||
              (message.from === "user" && !messageEditing)) && (
              <button
                onClick={() => handleCopyAll(displayContent)}
                className={`${isLastMessage? "":"group-hover:opacity-100 opacity-0"} cursor-pointer flex items-center gap-0.5 hover:text-gray-800 transition-colors`}
                aria-label="Copy all content"
              >
                {copiedAll ? (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="1.5"
                    stroke="currentColor"
                    className="w-5 h-5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75"
                    />
                  </svg>
                ) : (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="1.5"
                    stroke="currentColor"
                    className="w-5 h-5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
                    />
                  </svg>
                )}
                <span>{copiedAll ? "Copied!" : "Copy"}</span>
              </button>
            )}
            {message.from === "ai" && enableOperation && (
              <div
                onClick={() => {
                  if (!sendDisabled) {
                    onSendEditingMessage(
                      lastUserMessage(),
                      [],
                      "",
                      message.parentMessageId || ""
                    );
                    setMessageEditing(false);
                  }
                }}
                className={`${
                  sendDisabled
                    ? isLastMessage? "cursor-not-allowed opacity-50" : "cursor-not-allowed group-hover:opacity-50 opacity-0"
                    : isLastMessage? "cursor-pointer" : "cursor-pointer group-hover:opacity-100 opacity-0"
                } flex items-center gap-0.5 hover:text-gray-800 transition-colors`}
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
                    d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
                  />
                </svg>
                <span>Regenerate</span>
              </div>
            )}
            {message.from === "user" && enableOperation && !messageEditing && (
              <div
                onClick={() => setMessageEditing(true)}
                className={`${isLastMessage? "":"group-hover:opacity-100 opacity-0"} cursor-pointer flex items-center gap-0.5 hover:text-gray-800 transition-colors`}
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
                    d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                  />
                </svg>
                <span>Edit</span>
              </div>
            )}
            {/* 分支选择器 */}
            {message.from === "user" &&
              enableOperation &&
              !messageEditing &&
              branchCount > 1 && (
                <div className="flex gap-0.5 font-medium">
                  <button
                    className="cursor-pointer hover:text-gray-800 transition-colors disabled:cursor-not-allowed disabled:hover:text-gray-600  disabled:opacity-50"
                    onClick={() =>
                      handleBranchChange(parentId ?? "root", branchIndex - 1)
                    }
                    disabled={branchIndex === 0}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth="2"
                      stroke="currentColor"
                      className="size-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15.75 19.5 8.25 12l7.5-7.5"
                      />
                    </svg>
                  </button>
                  <span>{branchIndex + 1}</span>/<span>{branchCount}</span>
                  <button
                    className="cursor-pointer hover:text-gray-800 transition-colors disabled:cursor-not-allowed disabled:hover:text-gray-600  disabled:opacity-50"
                    onClick={() =>
                      handleBranchChange(parentId ?? "root", branchIndex + 1)
                    }
                    disabled={branchIndex === branchCount - 1}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth="2"
                      stroke="currentColor"
                      className="size-5"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="m8.25 4.5 7.5 7.5-7.5 7.5"
                      />
                    </svg>
                  </button>
                </div>
              )}
          </div>
        )}

        {message.type === "file" && (
          <div className="flex items-center gap-0.5">
            <span className="text-sm">{getFileIcon(message.fileType)}</span>
            <div className="flex">
              <span
                onClick={() =>
                  handleDownload(message.minioUrl ? message.minioUrl : "")
                }
                className="pr-2 text-xs font-medium hover:text-indigo-500 hover:cursor-pointer"
              >
                {message.fileName}
              </span>
            </div>
          </div>
        )}

        {message.type === "image" && (
          <div className="flex items-center justify-center">
            {message.content === "loading" ? (
              <LoadingCircle />
            ) : (
              <div>
                <Image
                  src={message.minioUrl || ""}
                  alt={`image`}
                  width={200}
                  height={200}
                  onClick={() => handleImageClick(message.minioUrl || "")}
                  className="cursor-pointer"
                />
              </div>
            )}
          </div>
        )}
        {message.type === "baseFile" &&
          message.content === "image_0" &&
          message.messageId && (
            <div
              className={`pl-2 flex gap-1 items-center text-sm text-indigo-500 hover:text-indigo-700 cursor-pointer ${
                showRefFile.includes(message.messageId) ? "pb-2" : "pb-6"
              }`}
              onClick={() => {
                setShowRefFile((prev) => {
                  // 使用函数式更新确保获取最新状态 ()
                  if (message.messageId) {
                    if (prev.includes(message.messageId)) {
                      // 如果存在：创建新数组（过滤掉目标元素）
                      return prev.filter((item) => item !== message.messageId);
                    } else {
                      // 如果不存在：创建新数组（添加新元素）
                      return [...prev, message.messageId];
                    }
                  } else {
                    return [...prev];
                  }
                });
              }}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="size-4"
              >
                <path d="M19.5 21a3 3 0 0 0 3-3v-4.5a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3V18a3 3 0 0 0 3 3h15ZM1.5 10.146V6a3 3 0 0 1 3-3h5.379a2.25 2.25 0 0 1 1.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 0 1 3 3v1.146A4.483 4.483 0 0 0 19.5 9h-15a4.483 4.483 0 0 0-3 1.146Z" />
              </svg>

              <div>
                {showRefFile.includes(message.messageId)
                  ? "Close References"
                  : "View References"}
              </div>
              {showRefFile.includes(message.messageId) ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M11.47 7.72a.75.75 0 0 1 1.06 0l7.5 7.5a.75.75 0 1 1-1.06 1.06L12 9.31l-6.97 6.97a.75.75 0 0 1-1.06-1.06l7.5-7.5Z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-5"
                >
                  <path
                    fillRule="evenodd"
                    d="M12.53 16.28a.75.75 0 0 1-1.06 0l-7.5-7.5a.75.75 0 0 1 1.06-1.06L12 14.69l6.97-6.97a.75.75 0 1 1 1.06 1.06l-7.5 7.5Z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          )}
        {message.type === "baseFile" &&
          message.messageId &&
          showRefFile.includes(message.messageId) && (
            <div className="pl-2 flex flex-col gap-2 items-start justify-center mb-3">
              <div className="flex items-center justify-center gap-1">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="text-gray-600 text-sm">
                  Score: {message.score}
                </div>
              </div>
              <div>
                <Image
                  src={message.imageMinioUrl || ""}
                  alt={`image`}
                  width={100}
                  height={100}
                  onClick={() => handleImageClick(message.imageMinioUrl || "")}
                  className="cursor-pointer"
                />
              </div>
              <div
                onClick={() => {
                  return handleDownload(
                    message.minioUrl ? message.minioUrl : ""
                  );
                }}
                className="text-gray-600 text-sm hover:text-indigo-700 cursor-pointer"
              >
                {message.fileName}
              </div>
              <div className="flex items-center justify-start gap-1 text-gray-600 pb-2 border-b-2 border-gray-200 w-full">
                <div className="text-sm font-semibold">From: </div>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="size-4"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4Zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37ZM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 0 1 3 13.179Z"
                    clipRule="evenodd"
                    transform="translate(0, 1)"
                  />
                </svg>
                <div className="text-sm font-semibold">
                  {modelConfig?.baseUsed.find(
                    (item) => item.baseId === message.baseId
                  )?.name || "User Upload"}
                </div>
              </div>
            </div>
          )}
        {/* 大图弹窗 */}
        {isOpen &&
          createPortal(
            <div
              className="overflow-visible top-0 left-0 w-[100vw] h-[100vh] flex items-center justify-center fixed !z-[50000] bg-black/80"
              onClick={handleCloseModal}
            >
              <Image
                src={selectedImage}
                alt="Selected large"
                fill // 使用 fill 布局
                style={{ objectFit: "contain" }} // 使用 style 来设置 objectFitobjectFit="contain" // 保持图像比例
                className="max-h-[90%] m-auto"
              />
            </div>,
            document.body
          )}
      </div>
    </div>
  );
};

export default ChatMessage;

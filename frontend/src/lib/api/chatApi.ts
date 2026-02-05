"use client";
import { BaseUsed, ModelConfig } from "@/types/types";
import { AxiosProgressEvent } from "axios";
import { apiClient as api } from "./apiClient";
import { mapModelConfigToBackend } from "./modelConfigMapper";

export const getChatHistory = async (username: string) => {
  return api.get("/chat/users/" + username + "/conversations");
};

export const renameChat = async (conversationId: string, chatName: string) => {
  return api.post("/chat/conversations/rename", {
    conversation_id: conversationId,
    conversation_new_name: chatName,
  });
};

export const getChatContent = async (conversationId: string) => {
  return api.get("/chat/conversations/" + conversationId);
};

export const deleteConversations = async (conversationId: string) => {
  return api.delete("/chat/conversations/" + conversationId);
};

export const deleteAllConversations = async (username: string) => {
  return api.delete("/chat/users/" + username + "/conversations");
};

export const uploadFiles = async (
  selectedFiles: File[],
  username: string,
  chatId: string,
  onProgress: (percent: number | null) => void
) => {
  if (!selectedFiles) return;

  const fileFormData = new FormData();

  selectedFiles.forEach((file) => {
    fileFormData.append("files", file); // 多个文件使用相同字段名
  });

  return api.post("/chat/upload/" + username + "/" + chatId, fileFormData, {
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (progressEvent.lengthComputable && progressEvent.total) {
        const percent = Math.round(
          (progressEvent.loaded / progressEvent.total) * 100
        );
        onProgress(percent); // 调用回调函数并传递进度百分比
      } else {
        // 处理无法计算进度的情况
        onProgress(null); // 或者传递一个特定的值表示进度不可计算
      }
    },
  });
};

export const createConversation = async (
  conversationId: string,
  username: string,
  conversationName: string,
  modelConfig: ModelConfig
) => {
  return api.post("/chat/conversations", {
    conversation_id: conversationId,
    username: username,
    conversation_name: conversationName,
    chat_model_config: mapModelConfigToBackend(modelConfig),
  });
};

export const updateChatModelConfig = async (
  conversationId: string,
  modelConfig: ModelConfig
) => {
  return api.post("/chat/conversations/config", {
    conversation_id: conversationId,
    chat_model_config: mapModelConfigToBackend(modelConfig),
  });
};

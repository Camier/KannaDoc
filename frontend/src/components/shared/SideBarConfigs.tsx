import { UnifiedSideBarConfig } from "./UnifiedSideBar";

// Preset configurations for different sidebar contexts
export const workflowSideBarConfig: UnifiedSideBarConfig = {
  translationNamespace: "WorkflowLeftSideBar",
  idField: "flowId",
  width: "w-[15%]",
  icon: "workflow",
  subtitleField: "lastModifyTime",
  disableFirstItem: true,
  emptyItemId: "1",
};

export const knowledgeBaseSideBarConfig: UnifiedSideBarConfig = {
  translationNamespace: "KnowledgeBaseLeftSideBar",
  idField: "baseId",
  width: "w-[20%]",
  containerPadding: "px-6",
  buttonPadding: "px-4",
  icon: "knowledge",
  subtitleField: "fileNumber",
  subtitleFormatFn: (item) => `${item.fileNumber} files`,
  disableFirstItem: true,
  emptyItemId: "1",
};

export const chatSideBarConfig: UnifiedSideBarConfig = {
  translationNamespace: "ChatLeftSidebar",
  idField: "conversationId",
  width: "w-[20%]",
  icon: "chat",
  subtitleField: "lastModifyTime",
  truncateName: 30,
};

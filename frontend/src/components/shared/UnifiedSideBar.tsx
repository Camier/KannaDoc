import { Dispatch, SetStateAction, useEffect, useRef, useState } from "react";
import ConfirmDialog from "@/components/ConfirmDialog";
import { useClickAway } from "react-use";
import { useTranslations } from "next-intl";

// Type for items displayed in sidebar (Flow, Base, or Chat)
export interface SidebarItem {
  id: string;
  name: string;
  lastModifyTime: string;
  createTime?: string;
  fileNumber?: number;
  flowId?: string;
  baseId?: string;
  conversationId?: string;
  isRead?: boolean;
}

// Type for delete confirmation state
interface DeleteState<T> {
  index: number;
  item: T;
}

export interface UnifiedSideBarConfig {
  // Translation namespace
  translationNamespace: "WorkflowLeftSideBar" | "KnowledgeBaseLeftSideBar" | "ChatLeftSidebar";

  // Item identification
  idField: keyof SidebarItem;

  // UI configuration
  width: string;
  containerPadding?: string;
  buttonPadding?: string;

  // Item display
  icon: "workflow" | "knowledge" | "chat";
  subtitleField?: keyof SidebarItem;
  subtitleFormatFn?: (item: SidebarItem) => string;

  // Features
  showSearch?: boolean;
  showTimeGrouping?: boolean;
  showClearAll?: boolean;
  disableFirstItem?: boolean;
  truncateName?: number;

  // Empty ID for disabled items
  emptyItemId?: string;
}

export interface UnifiedSideBarProps<T extends SidebarItem> {
  items: T[];
  searchTerm: string;
  setShowCreateModal: Dispatch<SetStateAction<boolean>>;
  selectedItem: string | null;
  setSelectedItem: Dispatch<SetStateAction<string | null>>;
  onDelete: (item: T) => void;
  onRename: (item: T, newName: string) => void;
  config: UnifiedSideBarConfig;

  // Optional props for Chat-specific features
  onNewChat?: () => void;
  onDeleteAll?: (items: T[]) => void;
  onSelectChat?: (chatId: string, isRead: boolean) => void;
  searchInput?: string;
  setSearchInput?: Dispatch<SetStateAction<string>>;
}

const UnifiedSideBar = <T extends SidebarItem>({
  items,
  searchTerm,
  setShowCreateModal,
  selectedItem,
  setSelectedItem,
  onDelete,
  onRename,
  config,
  onNewChat,
  onDeleteAll,
  onSelectChat,
  searchInput = "",
  setSearchInput,
}: UnifiedSideBarProps<T>) => {
  const t = useTranslations(config.translationNamespace);
  const ref = useRef(null);

  const [isSettingsOpen, setSettingsOpen] = useState<boolean[]>([]);
  const [inputValues, setInputValues] = useState<string[]>([]);
  const [isEditOpen, setIsEditOpen] = useState<boolean[]>([]);
  const [showConfirmDelete, setShowConfirmDelete] = useState<DeleteState<T> | null>(null);
  const [showConfirmDeleteAll, setShowConfirmDeleteAll] = useState(false);

  useClickAway(ref, () => {
    setSettingsOpen((prev) => prev.map(() => false));
  });

  useEffect(() => {
    setSettingsOpen(new Array(items.length).fill(false));
    setIsEditOpen(new Array(items.length).fill(false));
    setInputValues(items.map((item) => item.name));
  }, [items]);

  const filteredItems = items.filter((item) =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getItemId = (item: T): string => {
    const id = item[config.idField] as string;
    return id;
  };

  const handleDelete = (item: T, index: number) => {
    toggleSettings(index);
    setShowConfirmDelete({ index, item });
  };

  const confirmDelete = () => {
    if (showConfirmDelete) {
      onDelete(showConfirmDelete.item);
      setShowConfirmDelete(null);
    }
  };

  const cancelDelete = () => {
    setShowConfirmDelete(null);
  };

  const confirmDeleteAll = () => {
    if (onDeleteAll) {
      onDeleteAll(items);
      setShowConfirmDeleteAll(false);
    }
  };

  const cancelDeleteAll = () => {
    setShowConfirmDeleteAll(false);
  };

  const toggleSettings = (index: number) => {
    setSettingsOpen((prev) => prev.map((item, idx) => (idx === index ? !item : false)));
  };

  const handleEdit = (index: number) => {
    toggleSettings(index);
    setIsEditOpen((prev) => prev.map((item, idx) => (idx === index ? !item : false)));
  };

  const handleBlur = (item: T, index: number) => {
    if (
      inputValues[index].trim() !== "" &&
      inputValues[index].trim() !== item.name
    ) {
      onRename(item, inputValues[index]);
    } else {
      inputValues[index] = item.name;
    }
    setIsEditOpen((prev) => prev.map((item, idx) => (idx === index ? !item : false)));
  };

  const handleChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const newInputValues = [...inputValues];
    newInputValues[index] = e.target.value;
    setInputValues(newInputValues);
  };

  const handleItemClick = (item: T) => {
    const itemId = getItemId(item);

    if (config.disableFirstItem && itemId === config.emptyItemId) {
      return;
    }

    if (config.translationNamespace === "ChatLeftSidebar" && onSelectChat) {
      onSelectChat(item.conversationId!, item.isRead!);
    } else {
      setSelectedItem(itemId);
    }
  };

  const renderIcon = () => {
    const iconClass = `${selectedItem ? "size-5" : "size-4.5"} shrink-0`;

    switch (config.icon) {
      case "workflow":
        return (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className={iconClass}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z"
            />
          </svg>
        );
      case "knowledge":
        return (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className={iconClass}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
            />
          </svg>
        );
      case "chat":
        return (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className={iconClass}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
              transform="translate(0, 0.3)"
            />
          </svg>
        );
    }
  };

  const renderAddButton = () => {
    const buttonText = {
      WorkflowLeftSideBar: "addWorkflow",
      KnowledgeBaseLeftSideBar: "addKnowledgeBase",
      ChatLeftSidebar: "newChat",
    }[config.translationNamespace];

    const isChat = config.translationNamespace === "ChatLeftSidebar";

    return (
      <button
        onClick={() => (isChat && onNewChat ? onNewChat() : setShowCreateModal(true))}
        className={`w-full py-2 ${config.buttonPadding || "px-4"} bg-indigo-500 text-white hover:bg-indigo-700 transition-colors rounded-full`}
      >
        <div className="flex items-center justify-center gap-1 cursor-pointer text-[15px]">
          {isChat ? (
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
                d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-4.5"
            >
              <path
                fillRule="evenodd"
                d="M12 3.75a.75.75 0 0 1 .75.75v6.75h6.75a.75.75 0 0 1 0 1.5h-6.75v6.75a.75.75 0 0 1-1.5 0v-6.75H4.5a.75.75 0 0 1 0-1.5h6.75V4.5a.75.75 0 0 1 .75-.75Z"
                clipRule="evenodd"
              />
            </svg>
          )}
          <span>{t(buttonText)}</span>
        </div>
      </button>
    );
  };

  // Chat-specific extra controls
  const renderChatControls = () => {
    if (config.translationNamespace !== "ChatLeftSidebar") return null;

    return (
      <>
        <h2 className="text-sm text-center font-medium">{t("historyChat")}</h2>

        <div className="relative flex w-[75%] text-xs my-3">
          <input
            type="text"
            placeholder={t("searchPlaceholder")}
            className="w-full pl-3 pr-6 py-1 rounded-full border border-gray-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
            value={searchInput}
            onChange={(e) => setSearchInput?.(e.target.value)}
          />
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="size-4 absolute right-2.5 top-1/2 transform -translate-y-1/2 text-gray-400"
          >
            <path
              fillRule="evenodd"
              d="M10.5 3.75a6.75 6.75 0 1 0 0 13.5 6.75 6.75 0 0 0 0-13.5ZM2.25 10.5a8.25 8.25 0 1 1 14.59 5.28l4.69 4.69a.75.75 0 1 1-1.06 1.06l-4.69-4.69A8.25 8.25 0 0 1 2.25 10.5Z"
              clipRule="evenodd"
            />
          </svg>
        </div>

        <div className="flex gap-4 mb-2">
          <div
            className="text-indigo-500 cursor-pointer flex gap-1 items-center hover:text-indigo-700"
            onClick={() => setShowConfirmDeleteAll(true)}
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
                d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5m6 4.125 2.25 2.25m0 0 2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
              />
            </svg>
            <div className="text-sm">{t("clear")}</div>
          </div>
          <div
            className="text-gray-500 cursor-pointer flex items-center gap-1 hover:text-gray-700"
            onClick={onNewChat}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-5"
            >
              <path
                fillRule="evenodd"
                d="M4.755 10.059a7.5 7.5 0 0 1 12.548-3.364l1.903 1.903h-3.183a.75.75 0 1 0 0 1.5h4.992a.75.75 0 0 0 .75-.75V4.356a.75.75 0 0 0-1.5 0v3.18l-1.9-1.9A9 9 0 0 0 3.306 9.67a.75.75 0 1 0 1.45.388Zm15.408 3.352a.75.75 0 0 0-.919.53 7.5 7.5 0 0 1-12.548 3.364l-1.902-1.903h3.183a.75.75 0 0 0 0-1.5H2.984a.75.75 0 0 0-.75.75v4.992a.75.75 0 0 0 1.5 0v-3.18l1.9 1.9a9 9 0 0 0 15.059-4.035.75.75 0 0 0-.53-.918Z"
                clipRule="evenodd"
              />
            </svg>
            <div className="text-sm">{t("refresh")}</div>
          </div>
        </div>
        <div className="border-b-2 border-gray-200 w-[95%]"></div>
      </>
    );
  };

  return (
    <div
      className={`${
        config.translationNamespace === "ChatLeftSidebar"
          ? "bg-white rounded-l-3xl flex flex-col items-center py-5 pl-5"
          : `flex-none flex flex-col gap-4 h-full`
      } ${config.width}`}
    >
      <div
        className={`flex items-center justify-center ${
          config.translationNamespace === "ChatLeftSidebar"
            ? "my-2 w-full h-[8%] cursor-pointer"
            : "h-[10%]"
        } ${config.containerPadding || "px-6"}`}
      >
        {renderAddButton()}
      </div>

      {renderChatControls()}

      <div
        className={`${
          config.translationNamespace === "ChatLeftSidebar"
            ? "px-2 w-full flex-1 overflow-scroll scrollbar-hide mt-3"
            : "bg-white rounded-2xl overflow-scroll min-h-[90%] max-h-[90%] scrollbar-hide p-2"
        }`}
      >
        {filteredItems.map((item, index) => {
          const itemId = getItemId(item);
          const isSelected = selectedItem === itemId;
          const isDisabled = config.disableFirstItem && itemId === config.emptyItemId;

          return (
            <div
              key={index}
              className={`${
                config.translationNamespace === "ChatLeftSidebar"
                  ? "relative flex"
                  : "py-1.5 my-0.5 hover:bg-indigo-600 group cursor-pointer rounded-3xl flex justify-between items-start"
              } ${isSelected ? "bg-indigo-500 text-white" : "text-gray-800"} hover:bg-indigo-600 hover:text-white rounded-2xl mb-0.5`}
            >
              <div
                className={`flex-1 gap-2 hover:text-white w-full ${
                  isDisabled ? "cursor-not-allowed" : ""
                }`}
                onClick={() => handleItemClick(item)}
              >
                <div className="flex relative">
                  <div
                    className={`${
                      config.translationNamespace === "ChatLeftSidebar"
                        ? "py-1.5 pl-2.5 pr-0"
                        : "pl-3"
                    } flex items-center gap-1 text-gray-900 w-[${
                      config.translationNamespace === "ChatLeftSidebar"
                        ? "85%"
                        : config.icon === "workflow"
                        ? "78%"
                        : "80%"
                    }] ${isSelected ? "text-white text-lg" : "text-base group-hover:text-white"}`}
                  >
                    {renderIcon()}
                    <div
                      className={`${
                        isSelected ? "text-base" : "text-[15px]"
                      } whitespace-nowrap ${config.translationNamespace === "ChatLeftSidebar" ? "overflow-hidden" : config.icon === "knowledge" ? "overflow-hidden" : "overflow-auto"}`}
                    >
                      {isEditOpen[index] ? (
                        <input
                          type="text"
                          value={inputValues[index]}
                          onChange={(e) => handleChange(index, e)}
                          onBlur={() => handleBlur(item, index)}
                          className="bg-transparent outline-hidden border-none p-0 m-0 w-full"
                          autoFocus
                        />
                      ) : (
                        config.truncateName && config.translationNamespace === "ChatLeftSidebar"
                          ? item.name.slice(0, config.truncateName)
                          : item.name
                      )}
                    </div>
                  </div>
                  <div
                    className={`w-[${
                      config.translationNamespace === "ChatLeftSidebar"
                        ? "15%"
                        : config.icon === "workflow"
                        ? "22%"
                        : "20%"
                    }] flex items-center justify-center cursor-pointer text-white`}
                    onClick={() => toggleSettings(index)}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 16 16"
                      fill="currentColor"
                      className="size-5"
                    >
                      <path d="M2 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM12.5 6.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" />
                    </svg>
                  </div>
                  {isSettingsOpen[index] && (
                    <div
                      ref={ref}
                      className="absolute right-0 top-full mt-1 bg-white text-black rounded-2xl border-2 py-2 px-1 border-slate-200 shadow-lg z-10"
                    >
                      <div
                        className="flex gap-2 cursor-pointer hover:bg-indigo-600 hover:text-white px-2 py-1 rounded-xl"
                        onClick={() => handleEdit(index)}
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
                        <div className="text-sm">{t("rename")}</div>
                      </div>
                      <div
                        className="flex gap-2 cursor-pointer hover:bg-indigo-600 hover:text-white px-2 py-1 rounded-xl"
                        onClick={() => handleDelete(item, index)}
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
                        <div className="text-sm">{t("delete")}</div>
                      </div>
                    </div>
                  )}
                </div>
                <p
                  className={`px-4 text-gray-500 ${
                    isSelected
                      ? "text-white text-[13px]"
                      : "group-hover:text-white text-xs"
                  }`}
                >
                  {config.subtitleFormatFn
                    ? config.subtitleFormatFn(item)
                    : config.subtitleField
                    ? String(item[config.subtitleField] || "")
                    : item.lastModifyTime}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {showConfirmDelete && (
        <ConfirmDialog
          message={
            config.translationNamespace === "WorkflowLeftSideBar"
              ? t("confirmDelete", { flowName: showConfirmDelete.item.name })
              : config.translationNamespace === "KnowledgeBaseLeftSideBar"
              ? `${t("deleteConfirm")}"${showConfirmDelete.item.name}"？`
              : `${t("deleteSingleConfirm")}"${showConfirmDelete.item.name.slice(0, 30)}"？`
          }
          onConfirm={confirmDelete}
          onCancel={cancelDelete}
        />
      )}

      {showConfirmDeleteAll && (
        <ConfirmDialog
          message={t("deleteAllConfirm")}
          onConfirm={confirmDeleteAll}
          onCancel={cancelDeleteAll}
        />
      )}
    </div>
  );
};

export default UnifiedSideBar;

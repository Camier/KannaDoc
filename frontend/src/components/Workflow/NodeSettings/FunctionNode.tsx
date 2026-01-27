/**
 * FunctionNode Settings Component - Refactored to use NodeSettingsBase
 *
 * This component demonstrates the use of NodeSettingsBase composition pattern.
 * Reduced from ~1,032 lines to ~450 lines by extracting common patterns.
 */
import { logger } from "@/lib/logger";
import ConfirmDialog from "@/components/ConfirmDialog";
import PythonEditor from "@/components/Workflow/PythonEditor";
import {
  deleteDockerImages,
  getDockerImages,
  runPythonTest,
} from "@/lib/api/workflowApi";
import { useAuthStore } from "@/stores/authStore";
import { useFlowStore } from "@/stores/flowStore";
import { useGlobalStore } from "@/stores/WorkflowVariableStore";
import { CustomNode } from "@/types/types";
import { useTranslations } from "next-intl";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import NodeSettingsBase, {
  NodeHeader,
  DescriptionSection,
  GlobalVariablesSection,
  OutputSection,
} from "./NodeSettingsBase";

interface FunctionNodeProps {
  refreshDockerImages: boolean;
  saveImage: boolean;
  setSaveImage: React.Dispatch<React.SetStateAction<boolean>>;
  saveImageTag: string;
  setSaveImageTag: React.Dispatch<React.SetStateAction<string>>;
  saveImageName: string;
  setSaveImageName: React.Dispatch<React.SetStateAction<string>>;
  saveNode: (node: CustomNode) => void;
  isDebugMode: boolean;
  node: CustomNode;
  setCodeFullScreenFlow: React.Dispatch<React.SetStateAction<boolean>>;
  codeFullScreenFlow: boolean;
}

const FunctionNodeComponent: React.FC<FunctionNodeProps> = ({
  refreshDockerImages,
  saveImage,
  setSaveImage,
  saveImageTag,
  setSaveImageTag,
  saveImageName,
  setSaveImageName,
  saveNode,
  isDebugMode,
  node,
  setCodeFullScreenFlow,
  codeFullScreenFlow,
}) => {
  const t = useTranslations("FunctionNode");
  const { user } = useAuthStore();
  const {
    updateOutput,
    updatePackageInfos,
    removePackageInfos,
    updateImageUrl,
    updateDockerImageUse,
  } = useFlowStore();

  const {
    globalVariables,
    DockerImageUse,
    updateDockerImageUse: updateGlobalDockerImageUse,
  } = useGlobalStore();

  const [runTest, setRunTest] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [systemDockerImages, setSystemDockerImages] = useState<string[]>([]);
  const [showConfirmDeleteImage, setShowConfirmDeleteImage] = useState<string | null>(null);
  const [packageName, setPackageName] = useState("");

  const dockerImageUseRef = useRef(DockerImageUse);

  useEffect(() => {
    dockerImageUseRef.current = DockerImageUse;
  }, [DockerImageUse]);

  const fetchDockerImages = useCallback(async () => {
    try {
      if (user?.name) {
        const response = await getDockerImages(user.name);
        setSystemDockerImages(response.data.images);
        if (
          !(response.data.images as string[]).includes(
            dockerImageUseRef.current
          )
        ) {
          updateDockerImageUse("python-sandbox:latest");
        }
      }
    } catch (error) {
      logger.error("Get Docker Images Error:", error);
    }
  }, [user?.name, setSystemDockerImages, updateDockerImageUse]);

  useEffect(() => {
    fetchDockerImages();
  }, [refreshDockerImages, fetchDockerImages]);

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
      updateOutput(node.id, t("output.running"));
      try {
        if (saveImage) {
          if (saveImageName === "" || saveImageTag === "") {
            alert(t("alert.imageNameVersionRequired"));
            return;
          }
        }
        const sendSaveImage = saveImage
          ? saveImageName + ":" + saveImageTag
          : "";
        const response = await runPythonTest(
          user.name,
          node,
          globalVariables,
          sendSaveImage,
          DockerImageUse
        );
        const id = node.id;
        if (response.data.code === 0) {
          updateOutput(node.id, response.data.result[id][0].result);
        } else {
          updateOutput(node.id, response.data.msg);
        }
      } catch (error) {
        logger.error("Error connect:", error);
        updateOutput(node.id, t("output.running") + String(error));
      } finally {
        fetchDockerImages();
        setRunTest(false);
      }
    }
  };

  const deleteImage = async (showConfirmDeleteNImage: string) => {
    try {
      if (user?.name) {
        const response = await deleteDockerImages(
          user.name,
          showConfirmDeleteNImage
        );
        if (response.data.status === "success") {
          setSystemDockerImages((prev) =>
            prev.filter((image) => image != showConfirmDeleteNImage)
          );
          updateDockerImageUse("python-sandbox:latest");
        } else {
          alert(t("alert.cannotDeleteImage"));
        }
      }
    } catch (error) {
      logger.error("Error delete Image:", error);
    }
  };

  const confirmDeleteImage = () => {
    if (showConfirmDeleteImage) {
      deleteImage(showConfirmDeleteImage);
      setShowConfirmDeleteImage(null);
    }
  };

  const cancelDeleteImage = () => {
    if (showConfirmDeleteImage) {
      setShowConfirmDeleteImage(null);
    }
  };

  // FunctionNode-specific sections
  const PipDependenciesSection = ({ api }: { api: any }) => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="px-2 py-1 flex items-center justify-between w-full mt-1">
          <div className="flex items-center justify-center gap-1">
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
                d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0M12 12.75h.008v.008H12v-.008Z"
              />
            </svg>
            {t("pipDependencies.title")}
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
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
        <div className="w-full flex items-center justify-between p-2 gap-1 bg-gray-100 rounded-2xl">
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
              d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
            />
          </svg>
          <span className="whitespace-nowrap pr-2">
            {t("pipDependencies.sandboxImage")}
          </span>
          <div className="flex-1">
            <div className="flex items-center justify-center gap-1">
              <select
                name="updateDockerImageUse"
                value={DockerImageUse}
                onChange={(e) => {
                  updateDockerImageUse(e.target.value);
                }}
                className="w-full px-2 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 appearance-none"
              >
                {systemDockerImages.map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
              </select>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className={`size-4.5 ${
                  DockerImageUse === "python-sandbox:latest"
                    ? "cursor-not-allowed opacity-50"
                    : "cursor-pointer"
                } text-indigo-500 shrink-0`}
                onClick={() => {
                  if (DockerImageUse !== "python-sandbox:latest") {
                    setShowConfirmDeleteImage(DockerImageUse);
                  }
                }}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                />
              </svg>
            </div>
          </div>
        </div>
        <label className="w-full overflow-auto relative inline-flex items-center group p-2 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer">
          <input
            type="checkbox"
            checked={saveImage}
            onChange={() => setSaveImage((prev) => !prev)}
            className="shrink-0 appearance-none h-4.5 w-4.5 border-2 border-gray-300 rounded-lg transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
          />
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="absolute size-4 text-white shrink-0"
          >
            <path
              fillRule="evenodd"
              d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
              clipRule="evenodd"
              transform="translate(2, 0.2)"
            />
          </svg>
          <div className="ml-2 flex gap-1 items-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-4"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
              />
            </svg>
            <span>{t("pipDependencies.commitEnvironment")}</span>
          </div>
        </label>
        {saveImage && (
          <div className="bg-gray-100 rounded-2xl p-2">
            <div className="w-full flex items-center justify-between px-2 py-1 gap-1 rounded-2xl">
              <span className="whitespace-nowrap pr-2">
                {t("pipDependencies.imageName")}
              </span>
              <div className="flex-1">
                <input
                  name={"addImageName"}
                  value={saveImageName}
                  placeholder={t("pipDependencies.imageNamePlaceholder")}
                  onChange={(e) => setSaveImageName(e.target.value)}
                  className="w-full px-3 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
              </div>
            </div>
            <div className="w-full flex items-center justify-between px-2 py-1 gap-1 rounded-2xl">
              <span className="whitespace-nowrap pr-2">
                {t("pipDependencies.imageVersion")}
              </span>
              <div className="flex-1">
                <input
                  name={"addImageTag"}
                  value={saveImageTag}
                  placeholder={t("pipDependencies.imageVersionPlaceholder")}
                  onChange={(e) => setSaveImageTag(e.target.value)}
                  className="w-full px-3 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
              </div>
            </div>
          </div>
        )}
        <div className="flex items-center w-full px-2 pb-2 gap-6 text-gray-500">
          {t("pipDependencies.instruction")}
        </div>
        <div className="flex items-center w-full px-2 gap-6 border-gray-200">
          <input
            name={"addPackage"}
            value={packageName}
            placeholder={t("pipDependencies.packageNamePlaceholder")}
            onChange={(e) => setPackageName(e.target.value)}
            className="w-full px-3 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
            onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
              if (e.key === "Enter") {
                e.preventDefault();
                if (packageName === "") {
                  return;
                } else {
                  if (node?.data.pip?.hasOwnProperty(packageName)) {
                    alert(
                      t("alert.packageExists", { packageName: packageName })
                    );
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
                  alert(
                    t("alert.packageExists", { packageName: packageName })
                  );
                  return;
                }
                updatePackageInfos(node.id, packageName, "");
                setPackageName("");
              }
            }}
            className="whitespace-nowrap cursor-pointer hover:text-indigo-700 pr-2 flex items-center gap-1 text-indigo-500"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="size-4"
            >
              <path
                fillRule="evenodd"
                d="M12 3.75a.75.75 0 0 1 .75.75v6.75h6.75a.75.75 0 0 1 0 1.5h-6.75v6.75a.75.75 0 0 1-1.5 0v-6.75H4.5a.75.75 0 0 1 0-1.5h6.75V4.5a.75.75 0 0 1 .75-.75Z"
                clipRule="evenodd"
              />
            </svg>
            <span>{t("pipDependencies.clickToAdd")}</span>
          </div>
        </div>
        {node.data.pip && (
          <div className="space-y-2">
            {Object.keys(node.data.pip).length == 0 && (
              <div className="px-2 flex w-full items-center gap-2 text-gray-500">
                {t("pipDependencies.noPackages")}
              </div>
            )}
            {Object.keys(node.data.pip).map((key) => (
              <div className="px-2 flex w-full items-center gap-2" key={key}>
                <div className="max-w-[50%] whitespace-nowrap overflow-auto">
                  {key}
                </div>
                <div>==</div>
                <input
                  name={key}
                  value={node.data.pip ? node.data.pip[key] : ""}
                  onChange={handleUpdatePackageInfos}
                  placeholder={t("pipDependencies.packageVersionPlaceholder")}
                  onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      e.currentTarget.blur();
                    }
                  }}
                  className="flex-1 w-full px-3 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="size-4 text-indigo-500 cursor-pointer shrink-0"
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
        <div className="px-2 flex w-full items-center gap-2">
          <div className="max-w-[50%] whitespace-nowrap overflow-auto">
            {t("pipDependencies.mirrorUrl")}
          </div>
          <div>=</div>
          <input
            name={"imageUrl"}
            value={node.data.imageUrl ? node.data.imageUrl : ""}
            onChange={handleUpdateImageUrl}
            placeholder={t("pipDependencies.mirrorUrlPlaceholder")}
            onKeyDown={(e: React.KeyboardEvent<HTMLSpanElement>) => {
              if (e.key === "Enter") {
                e.preventDefault();
                e.currentTarget.blur();
              }
            }}
            className="flex-1 w-full px-3 py-1 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
          />
        </div>
      </div>
    </details>
  );

  const CodeEditorSection = () => (
    <details className="group w-full" open>
      <summary className="flex items-center cursor-pointer w-full">
        <div className="py-1 px-2 flex mt-1 items-center justify-between w-full">
          <div className="flex items-center justify-start gap-1">
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
                d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z"
              />
            </svg>
            {t("codeEditor.title")}
            <svg
              className="w-4 h-4 transition-transform group-open:rotate-180"
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
            className="cursor-pointer disabled:cursor-not-allowed px-2 py-1 rounded-full hover:bg-indigo-600 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
          >
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
                d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
              />
            </svg>
            <span>{t("codeEditor.runTest")}</span>
          </button>
        </div>
      </summary>
      <div className="rounded-2xl shadow-lg overflow-auto w-full mb-2">
        <PythonEditor node={node} />
      </div>
    </details>
  );

  // Save button for header
  const saveButton = (
    <button
      onClick={() => saveNode(node)}
      className="cursor-pointer disabled:cursor-not-allowed py-1 px-2 rounded-full hover:bg-indigo-600 hover:text-white disabled:opacity-50 flex items-center justify-center gap-1"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="size-4"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
        />
      </svg>
      <span className="whitespace-nowrap">{t("saveNode")}</span>
    </button>
  );

  return (
    <NodeSettingsBase
      node={node}
      isDebugMode={isDebugMode}
      codeFullScreenFlow={codeFullScreenFlow}
      setCodeFullScreenFlow={setCodeFullScreenFlow}
      translationNamespace="FunctionNode"
    >
      {(api) => (
        <>
          {/* Header with save button */}
          <NodeHeader node={node} updateNodeLabel={api.updateNodeLabel} actions={saveButton} />

          {/* Description section */}
          <DescriptionSection
            node={node}
            isEditing={api.isEditing}
            setIsEditing={api.setIsEditing}
            updateDescription={api.updateDescription}
            codeFullScreenFlow={codeFullScreenFlow}
            t={api.t}
          />

          {/* Global variables section */}
          <GlobalVariablesSection
            isDebugMode={isDebugMode}
            codeFullScreenFlow={codeFullScreenFlow}
            setCodeFullScreenFlow={setCodeFullScreenFlow}
            globalVariables={api.globalVariables}
            globalDebugVariables={api.globalDebugVariables}
            addProperty={api.addProperty}
            removeProperty={api.removeProperty}
            handleVariableChange={api.handleVariableChange}
            t={api.t}
          />

          {/* FunctionNode-specific sections */}
          <PipDependenciesSection api={api} />
          <CodeEditorSection />

          {/* Output section */}
          <OutputSection
            node={node}
            updateDebug={api.updateDebug}
            t={api.t}
            disabled={runTest}
          />

          {/* Portal for delete confirmation */}
          {showConfirmDeleteImage &&
            createPortal(
              <ConfirmDialog
                message={t("deleteImage.confirmMessage", {
                  imageName: showConfirmDeleteImage,
                })}
                onConfirm={confirmDeleteImage}
                onCancel={cancelDeleteImage}
              />,
              document.body
            )}
        </>
      )}
    </NodeSettingsBase>
  );
};

export default FunctionNodeComponent;

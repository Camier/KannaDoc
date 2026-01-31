import { Dispatch, SetStateAction, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useClickAway } from "react-use";
import { getCliproxyapiModels, CliproxyapiModel } from "@/lib/api/configApi";

interface AddLLMEngineProps {
  setShowAddLLM: Dispatch<SetStateAction<boolean>>;
  nameError: string | null;
  setNameError: Dispatch<SetStateAction<string | null>>;
  newModelName: string;
  setNewModelName: Dispatch<SetStateAction<string>>;
  onCreateConfirm: () => void;
  setNewModelUrl?: Dispatch<SetStateAction<string>>;
}

const AddLLMEngine: React.FC<AddLLMEngineProps> = ({
  setShowAddLLM,
  nameError,
  setNameError,
  newModelName,
  setNewModelName,
  onCreateConfirm,
  setNewModelUrl,
}) => {
  const t = useTranslations("AddLLMEngine");
  const [availableModels, setAvailableModels] = useState<CliproxyapiModel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  const dropdownRef = useRef(null);

  useClickAway(dropdownRef, () => {
    setShowDropdown(false);
  });

  useEffect(() => {
    const fetchModels = async () => {
      setIsLoading(true);
      try {
        const models = await getCliproxyapiModels();
        setAvailableModels(models);
      } catch (error) {
        console.error("Failed to fetch models", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchModels();
  }, []);

  const filteredModels = availableModels.filter((model) =>
    model.name.toLowerCase().includes(newModelName.toLowerCase())
  );

  const groupedModels = filteredModels.reduce((acc, model) => {
    (acc[model.group] = acc[model.group] || []).push(model);
    return acc;
  }, {} as Record<string, CliproxyapiModel[]>);

  const handleModelSelect = (model: CliproxyapiModel) => {
    setNewModelName(model.name);
    if (setNewModelUrl) {
      setNewModelUrl(model.base_url);
    }
    setNameError(null);
    setShowDropdown(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900 rounded-3xl p-6 w-[35%]">
        <div className="flex items-center gap-2 mb-6 px-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="2"
            stroke="currentColor"
            className="size-6"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
            />
          </svg>

          <h3 className="text-lg font-medium text-gray-100">{t("title")}</h3>
        </div>
        <div className="px-4 w-full">
          <div className="relative w-full" ref={dropdownRef}>
            <input
              type="text"
              placeholder={t("placeholder")}
              className={`w-full px-4 py-2 mb-2 border bg-gray-800 text-gray-100 rounded-3xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500 ${
                nameError ? "border-red-500" : "border-gray-700"
              }`}
              value={newModelName}
              onChange={(e) => {
                setNewModelName(e.target.value);
                setNameError(null);
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onCreateConfirm();
                }
              }}
              autoFocus
            />

            {showDropdown && (availableModels.length > 0 || isLoading) && (
              <div className="absolute w-full mt-1 bg-gray-900 border border-gray-700 rounded-3xl shadow-lg z-50 overflow-hidden">
                <div className="max-h-60 overflow-y-auto">
                  {isLoading ? (
                    <div className="px-4 py-2 text-gray-400 text-sm">
                      Loading models...
                    </div>
                  ) : Object.keys(groupedModels).length > 0 ? (
                    Object.entries(groupedModels).map(([group, models]) => (
                      <div key={group}>
                        <div className="text-gray-500 text-xs px-4 py-1 font-semibold bg-gray-800/90 uppercase tracking-wider sticky top-0 backdrop-blur-sm">
                          {group}
                        </div>
                        {models.map((model) => (
                          <div
                            key={model.name}
                            onClick={() => handleModelSelect(model)}
                            className="px-4 py-2 cursor-pointer transition-colors hover:bg-gray-800 text-gray-200 flex justify-between items-center"
                          >
                            <span>{model.name}</span>
                          </div>
                        ))}
                      </div>
                    ))
                  ) : (
                    <div className="px-4 py-2 text-gray-500 text-sm">
                      No matching models found
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {nameError && (
            <p className="text-red-500 text-sm mb-2 px-2">{nameError}</p>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={() => setShowAddLLM(false)}
            className="px-4 py-2 text-gray-300 border border-gray-700 rounded-full hover:bg-gray-800 cursor-pointer"
          >
            {t("cancel")}
          </button>
          <button
            onClick={onCreateConfirm}
            className="px-4 py-2 text-white bg-indigo-500 rounded-full hover:bg-indigo-700 cursor-pointer"
          >
            {t("confirm")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddLLMEngine;

/**
 * KnowledgeBaseSelector Component
 *
 * Grid of selectable knowledge base checkboxes.
 * Displays available knowledge bases with selection state.
 *
 * @param knowledgeBases - List of knowledge bases with selection state
 * @param onBaseToggle - Callback when knowledge base selection changes
 */
import React from "react";
import { KnowledgeBase } from "@/types/types";

interface KnowledgeBaseSelectorProps {
  knowledgeBases: KnowledgeBase[];
  onBaseToggle: (id: string) => void;
}

export const KnowledgeBaseSelector: React.FC<KnowledgeBaseSelectorProps> = ({
  knowledgeBases,
  onBaseToggle,
}) => {
  return (
    <div className="py-2 grid grid-cols-2 gap-3 mt-2">
      {knowledgeBases.map((base) => (
        <label
          key={base.id}
          className="overflow-auto relative inline-flex items-center group px-3 py-2 border border-gray-200 rounded-3xl hover:bg-gray-50 cursor-pointer"
        >
          <input
            type="checkbox"
            checked={base.selected}
            onChange={() => onBaseToggle(base.id)}
            className="shrink-0 appearance-none h-5 w-5 border-2 border-gray-300 rounded-3xl transition-colors checked:bg-indigo-500 checked:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-200"
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
              transform="translate(2.8, 1)"
            />
          </svg>
          <div className="ml-2 flex gap-1 items-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-5 shrink-0"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
              />
            </svg>
            <span>{base.name}</span>
          </div>
        </label>
      ))}
    </div>
  );
};

import { useState } from "react";
import { useTranslations } from "next-intl";
import { searchPreview } from "@/lib/api/knowledgeBaseApi";
import type { SearchPreviewResult } from "@/lib/api/knowledgeBaseApi";

interface SearchPreviewPanelProps {
  kbId: string;
  onClose: () => void;
}

const SearchPreviewPanel: React.FC<SearchPreviewPanelProps> = ({
  kbId,
  onClose,
}) => {
  const t = useTranslations("SearchPreview");
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchPreviewResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError("Please enter a search query");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await searchPreview(kbId, query, topK);
      setResults(response.results);
    } catch (err: any) {
      setError(err.message || "Failed to search");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 rounded-3xl p-6 w-[80%] max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
              className="size-6 text-indigo-500"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
              />
            </svg>
            <h3 className="text-lg font-medium text-gray-100">
              Search Preview
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
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
                d="M6 18 18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Search Input */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="Enter search query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 px-4 py-2 border border-gray-600 rounded-3xl bg-gray-700 text-gray-100 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="px-4 py-2 border border-gray-600 rounded-3xl bg-gray-700 text-gray-100 focus:outline-hidden"
          >
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
          </select>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2 bg-indigo-500 text-white rounded-full hover:bg-indigo-600 disabled:bg-gray-600 transition-colors"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-xl text-red-400">
            {error}
          </div>
        )}

        {/* Results Table */}
        <div className="flex-1 overflow-auto">
          {results.length > 0 ? (
            <table className="w-full">
              <thead className="sticky top-0 bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-300">Rank</th>
                  <th className="px-4 py-2 text-left text-gray-300">Score</th>
                  <th className="px-4 py-2 text-left text-gray-300">File</th>
                  <th className="px-4 py-2 text-left text-gray-300">Page</th>
                  <th className="px-4 py-2 text-left text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result, index) => (
                  <tr
                    key={index}
                    className="border-b border-gray-700 hover:bg-gray-700/50 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-300">#{index + 1}</td>
                    <td className="px-4 py-3 text-gray-300">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          result.score > 0.8
                            ? "bg-green-500/20 text-green-400"
                            : result.score > 0.6
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-red-500/20 text-red-400"
                        }`}
                      >
                        {result.score.toFixed(3)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-300 max-w-xs truncate">
                      {result.file_name || "Unknown"}
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {result.page_number}
                    </td>
                    <td className="px-4 py-3">
                      {result.minio_url ? (
                        <button
                          onClick={() => setSelectedImage(result.minio_url!)}
                          className="px-3 py-1 bg-indigo-500 text-white rounded-full hover:bg-indigo-600 text-sm transition-colors"
                        >
                          View Image
                        </button>
                      ) : (
                        <span className="text-gray-500 text-sm">No image</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              {loading
                ? "Searching..."
                : "Enter a query and click Search to see results"}
            </div>
          )}
        </div>
      </div>

      {/* Image Viewer Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[60]"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] overflow-auto">
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute top-2 right-2 bg-gray-800 text-white p-2 rounded-full hover:bg-gray-700 transition-colors"
            >
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
                  d="M6 18 18 6M6 6l12 12"
                />
              </svg>
            </button>
            <img
              src={selectedImage}
              alt="Preview"
              className="rounded-xl"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPreviewPanel;

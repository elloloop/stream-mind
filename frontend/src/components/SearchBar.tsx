"use client";

import { useState, useEffect, FormEvent } from "react";
import type { EmbeddingModel } from "@/lib/types";
import { getModels } from "@/lib/api";

interface SearchBarProps {
  onSearch: (query: string, model?: string) => void;
  isLoading: boolean;
}

export default function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [models, setModels] = useState<EmbeddingModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");

  useEffect(() => {
    getModels()
      .then((data) => {
        setModels(data.models);
        setSelectedModel(data.default);
      })
      .catch(() => {});
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      onSearch(trimmed, selectedModel || undefined);
      setQuery("");
    }
  };

  return (
    <div className="px-8 md:px-16 py-6">
      <form onSubmit={handleSubmit} className="flex gap-3 max-w-2xl">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe what you want to watch... (e.g. 'cyberpunk anime', '90s romcoms')"
            className="w-full rounded-md bg-gray-800/80 border border-gray-600 px-4 py-3 text-white placeholder-gray-400 outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
            disabled={isLoading}
          />
          {isLoading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-white" />
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="rounded-md bg-red-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? "Searching..." : "Discover"}
        </button>
      </form>
      <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
        <span>Powered by AI semantic search</span>
        {models.length > 1 && (
          <>
            <span className="text-gray-700">·</span>
            <span className="text-gray-500">Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="rounded border border-gray-700 bg-gray-800/60 px-2 py-0.5 text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 outline-none cursor-pointer transition-colors"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id} className="bg-gray-900 text-gray-300">
                  {m.label}
                </option>
              ))}
            </select>
          </>
        )}
      </div>
    </div>
  );
}

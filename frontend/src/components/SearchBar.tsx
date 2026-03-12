"use client";

import { useState, FormEvent } from "react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export default function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      onSearch(trimmed);
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
      <p className="mt-2 text-xs text-gray-500">
        Powered by AI semantic search with Qwen embeddings
      </p>
    </div>
  );
}

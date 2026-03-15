"use client";

import { useState, useRef, FormEvent } from "react";

const SUGGESTIONS = [
  "christopher nolan sci-fi",
  "korean thriller",
  "feel good comedy",
  "90s action classics",
  "studio ghibli vibes",
  "movies like Interstellar",
  "underrated horror gems",
  "Leonardo DiCaprio drama",
];

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
  autoFocus?: boolean;
}

export default function SearchBar({ onSearch, isLoading, autoFocus }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      onSearch(trimmed);
      setQuery("");
      setShowSuggestions(false);
      inputRef.current?.blur();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    onSearch(suggestion);
    setQuery("");
    setShowSuggestions(false);
    inputRef.current?.blur();
  };

  return (
    <div className="px-6 md:px-16 py-4 md:py-6">
      <form onSubmit={handleSubmit} className="relative flex gap-3 max-w-2xl">
        <div className="relative flex-1">
          <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => !query && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Describe what you're in the mood for..."
            className="w-full rounded-lg bg-white/5 border border-white/10 pl-10 pr-4 py-3 text-white placeholder-gray-500 outline-none focus:border-yellow-400/50 focus:ring-1 focus:ring-yellow-400/50 transition-colors text-sm min-h-[44px]"
            disabled={isLoading}
            autoFocus={autoFocus}
          />
          {isLoading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-yellow-400/30 border-t-yellow-400" />
            </div>
          )}

          {/* Suggestions dropdown */}
          {showSuggestions && !query && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-2xl overflow-hidden z-20 animate-fadeIn">
              <p className="px-3 py-2 text-[10px] font-medium text-gray-600 uppercase tracking-wider">
                Try searching for
              </p>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onMouseDown={() => handleSuggestionClick(s)}
                  className="w-full text-left px-3 py-2.5 text-sm text-gray-300 hover:bg-white/5 transition-colors flex items-center gap-2"
                >
                  <svg className="h-3 w-3 text-gray-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                  </svg>
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="rounded-lg bg-yellow-400 px-5 py-3 font-medium text-black text-sm transition-all hover:bg-yellow-300 disabled:opacity-40 disabled:cursor-not-allowed min-h-[44px] press-scale"
        >
          {isLoading ? "Searching..." : "Discover"}
        </button>
      </form>
      <p className="mt-2 text-xs text-gray-600 ml-1">
        AI-powered semantic search across 300k+ movies
      </p>
    </div>
  );
}

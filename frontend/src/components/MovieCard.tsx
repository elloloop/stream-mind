"use client";

import { Movie } from "@/lib/types";
import { tmdbImageUrl } from "@/lib/api";
import { isWatched, toggleWatched } from "@/lib/storage";
import { useState } from "react";

interface MovieCardProps {
  movie: Movie;
  onInfo: (movie: Movie) => void;
  onWatchedChange?: () => void;
}

export default function MovieCard({ movie, onInfo, onWatchedChange }: MovieCardProps) {
  const [watched, setWatched] = useState(() => isWatched(movie.id));
  const posterUrl = tmdbImageUrl(movie.poster_path, "w300");

  const handleToggleWatched = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newState = toggleWatched(movie);
    setWatched(newState);
    onWatchedChange?.();
  };

  return (
    <div
      className="group relative flex-shrink-0 w-[160px] md:w-[200px] cursor-pointer transition-transform duration-200 hover:scale-105 hover:z-10"
      onClick={() => onInfo(movie)}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] overflow-hidden rounded-md bg-gray-800">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={movie.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-500 text-sm px-2 text-center">
            {movie.title}
          </div>
        )}

        {/* Hover overlay — pointer-events-none so clicks pass through to the card */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-200 pointer-events-none" />

        {/* Match score badge */}
        {movie.match_score > 0 && (
          <div className="absolute top-2 left-2 rounded bg-green-600/90 px-1.5 py-0.5 text-xs font-bold text-white">
            {Math.round(movie.match_score * 100)}%
          </div>
        )}

        {/* Watched indicator */}
        {watched && (
          <div className="absolute top-2 right-2 rounded-full bg-blue-500 p-1">
            <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
            </svg>
          </div>
        )}

        {/* Action buttons on hover */}
        <div className="absolute bottom-0 left-0 right-0 translate-y-full group-hover:translate-y-0 transition-transform duration-200 bg-gradient-to-t from-black/90 to-transparent p-2 pt-8 flex justify-between items-end">
          <button
            onClick={handleToggleWatched}
            className="rounded-full border border-gray-400 p-1.5 text-white hover:border-white transition-colors"
            title={watched ? "Unmark watched" : "Mark as watched"}
          >
            {watched ? (
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
            )}
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onInfo(movie);
            }}
            className="rounded-full border border-gray-400 p-1.5 text-white hover:border-white transition-colors"
            title="More info"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Title below poster */}
      <p className="mt-1.5 text-xs text-gray-400 line-clamp-1">{movie.title}</p>
    </div>
  );
}

"use client";

import { Movie } from "@/lib/types";
import { tmdbImageUrl } from "@/lib/api";
import { isWatched, toggleWatched } from "@/lib/storage";
import { useState, useEffect } from "react";

interface MovieDetailsProps {
  movie: Movie;
  onClose: () => void;
  onWatchedChange?: () => void;
}

const STREAMING_PLATFORMS = [
  { name: "Netflix", color: "bg-red-600" },
  { name: "Prime Video", color: "bg-blue-500" },
  { name: "Disney+", color: "bg-blue-700" },
  { name: "Hulu", color: "bg-green-500" },
];

export default function MovieDetails({ movie, onClose, onWatchedChange }: MovieDetailsProps) {
  const [watched, setWatched] = useState(() => isWatched(movie.id));
  const backdropUrl = tmdbImageUrl(movie.backdrop_path, "w780");

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleToggleWatched = () => {
    const newState = toggleWatched(movie);
    setWatched(newState);
    onWatchedChange?.();
  };

  // Pick 2-3 random platforms
  const platforms = STREAMING_PLATFORMS.slice(
    0,
    2 + Math.floor(Math.random() * 2)
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-lg bg-[#181818] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 z-10 rounded-full bg-[#181818] p-1.5 text-white hover:bg-gray-700 transition-colors"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Backdrop image */}
        {backdropUrl && (
          <div className="relative">
            <img
              src={backdropUrl}
              alt={movie.title}
              className="w-full rounded-t-lg object-cover"
              style={{ maxHeight: "350px" }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#181818] via-transparent to-transparent" />

            {/* Title overlay */}
            <div className="absolute bottom-4 left-6 right-6">
              <h2 className="text-3xl font-bold text-white drop-shadow-lg">
                {movie.title}
              </h2>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="px-6 pb-6">
          {!backdropUrl && (
            <h2 className="text-3xl font-bold text-white pt-6 mb-4">
              {movie.title}
            </h2>
          )}

          {/* Meta row */}
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            {movie.match_score > 0 && (
              <span className="text-green-400 font-bold text-base">
                {Math.round(movie.match_score * 100)}% Match
              </span>
            )}
            {movie.vote_average > 0 && (
              <span className="text-green-400 font-semibold">
                {movie.vote_average.toFixed(1)} / 10
              </span>
            )}
            {movie.release_date && (
              <span className="text-gray-400">{movie.release_date}</span>
            )}
            {movie.vote_count > 0 && (
              <span className="text-gray-500">
                {movie.vote_count.toLocaleString()} votes
              </span>
            )}
          </div>

          {/* Genres */}
          {movie.genres.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {movie.genres.map((genre) => (
                <span
                  key={genre}
                  className="rounded border border-gray-600 px-2 py-0.5 text-xs text-gray-300"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {/* Overview */}
          <p className="mt-4 text-gray-300 leading-relaxed">{movie.overview}</p>

          {/* Action buttons */}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={handleToggleWatched}
              className={`flex items-center gap-2 rounded px-5 py-2 font-semibold transition-colors ${
                watched
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
            >
              {watched ? (
                <>
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                  </svg>
                  Watched
                </>
              ) : (
                <>
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                  Mark as Watched
                </>
              )}
            </button>
          </div>

          {/* Streaming platforms */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-2">
              Available to Watch On
            </h3>
            <div className="flex flex-wrap gap-2">
              {platforms.map((platform) => (
                <button
                  key={platform.name}
                  className={`${platform.color} rounded px-4 py-1.5 text-sm font-medium text-white hover:opacity-80 transition-opacity`}
                >
                  {platform.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

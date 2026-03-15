"use client";

import { Movie } from "@/lib/types";
import { tmdbImageUrl } from "@/lib/api";

interface HeroProps {
  movie: Movie;
  onInfo: (movie: Movie) => void;
  onAddToWatchlist?: (movie: Movie) => void;
}

export default function Hero({ movie, onInfo, onAddToWatchlist }: HeroProps) {
  const bgUrl = tmdbImageUrl(movie.backdrop_path, "original");

  return (
    <div className="relative h-[55vh] md:h-[65vh] min-h-[380px] md:min-h-[460px] w-full overflow-hidden animate-fadeIn">
      {/* Background image */}
      {bgUrl && (
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${bgUrl})` }}
        />
      )}

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/50 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0c0c0c] via-transparent to-black/40" />

      {/* Content */}
      <div className="relative flex h-full flex-col justify-end px-6 pb-16 md:px-16 md:pb-20 lg:max-w-2xl">
        <h1 className="mb-3 text-2xl font-bold text-white md:text-4xl lg:text-5xl drop-shadow-lg">
          {movie.title}
        </h1>

        <div className="mb-4 flex items-center gap-3 text-sm text-gray-300">
          {movie.vote_average > 0 && (
            <span className="rounded-full bg-yellow-400/20 border border-yellow-400/40 px-2.5 py-0.5 text-yellow-300 font-medium text-xs">
              {movie.vote_average.toFixed(1)} / 10
            </span>
          )}
          {movie.release_date && (
            <span className="text-gray-400">{movie.release_date.slice(0, 4)}</span>
          )}
          {movie.genres.length > 0 && (
            <span className="text-gray-400 hidden sm:inline">{movie.genres.slice(0, 3).join(" · ")}</span>
          )}
        </div>

        <p className="mb-6 line-clamp-2 md:line-clamp-3 text-sm text-gray-300 md:text-base leading-relaxed">
          {movie.overview}
        </p>

        <div className="flex gap-3">
          <button
            onClick={() => onInfo(movie)}
            className="flex items-center gap-2 rounded-lg bg-yellow-400 px-5 py-2.5 font-semibold text-black text-sm transition hover:bg-yellow-300 min-h-[44px] press-scale"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Details
          </button>
          <button
            onClick={() => onAddToWatchlist?.(movie)}
            className="flex items-center gap-2 rounded-lg bg-white/10 border border-white/10 px-5 py-2.5 font-medium text-white text-sm transition hover:bg-white/20 min-h-[44px] press-scale"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
            Watchlist
          </button>
        </div>
      </div>

      {/* Mobile logo overlay (since navbar is hidden on mobile) */}
      <div className="absolute top-4 left-6 md:hidden safe-top">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-yellow-400 flex items-center justify-center">
            <svg className="h-3.5 w-3.5 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <span className="text-lg font-bold tracking-tight text-white drop-shadow-lg">
            stream<span className="text-yellow-400">mind</span>
          </span>
        </div>
      </div>
    </div>
  );
}

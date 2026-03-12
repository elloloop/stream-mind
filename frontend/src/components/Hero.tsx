"use client";

import { Movie } from "@/lib/types";
import { tmdbImageUrl } from "@/lib/api";

interface HeroProps {
  movie: Movie;
  onInfo: (movie: Movie) => void;
}

export default function Hero({ movie, onInfo }: HeroProps) {
  const bgUrl = tmdbImageUrl(movie.backdrop_path, "original");

  return (
    <div className="relative h-[70vh] min-h-[500px] w-full overflow-hidden">
      {/* Background image */}
      {bgUrl && (
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${bgUrl})` }}
        />
      )}

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#141414] via-transparent to-black/30" />

      {/* Content */}
      <div className="relative flex h-full flex-col justify-end px-8 pb-24 md:px-16 lg:max-w-2xl">
        <h1 className="mb-3 text-4xl font-bold text-white md:text-5xl lg:text-6xl drop-shadow-lg">
          {movie.title}
        </h1>

        <div className="mb-4 flex items-center gap-3 text-sm text-gray-300">
          {movie.vote_average > 0 && (
            <span className="text-green-400 font-semibold">
              {Math.round(movie.vote_average * 10)}% Match
            </span>
          )}
          {movie.release_date && (
            <span>{movie.release_date.slice(0, 4)}</span>
          )}
          {movie.genres.length > 0 && (
            <span>{movie.genres.slice(0, 3).join(" · ")}</span>
          )}
        </div>

        <p className="mb-6 line-clamp-3 text-base text-gray-200 md:text-lg">
          {movie.overview}
        </p>

        <div className="flex gap-3">
          <button
            onClick={() => onInfo(movie)}
            className="flex items-center gap-2 rounded bg-white/90 px-6 py-2.5 font-semibold text-black transition hover:bg-white"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
            Play
          </button>
          <button
            onClick={() => onInfo(movie)}
            className="flex items-center gap-2 rounded bg-gray-500/60 px-6 py-2.5 font-semibold text-white transition hover:bg-gray-500/80"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            More Info
          </button>
        </div>
      </div>
    </div>
  );
}

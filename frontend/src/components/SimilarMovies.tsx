"use client";

import { useState, useEffect } from "react";
import { Movie } from "@/lib/types";
import { getSimilarMovies, tmdbImageUrl } from "@/lib/api";

interface SimilarMoviesProps {
  movieId: number;
  onSelect: (movie: Movie) => void;
}

export default function SimilarMovies({ movieId, onSelect }: SimilarMoviesProps) {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getSimilarMovies(movieId)
      .then((data) => {
        if (!cancelled) setMovies(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [movieId]);

  if (loading) {
    return (
      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">More Like This</h3>
        <div className="flex gap-2 overflow-hidden">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex-shrink-0 w-[80px] aspect-[2/3] rounded-lg bg-white/5 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!movies.length) return null;

  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">More Like This</h3>
      <div className="flex gap-2 overflow-x-auto scrollbar-hide momentum-scroll pb-1">
        {movies.map((movie) => (
          <button
            key={movie.id}
            onClick={() => onSelect(movie)}
            className="flex-shrink-0 w-[80px] group/sim"
          >
            <div className="aspect-[2/3] rounded-lg overflow-hidden bg-gray-800/50">
              {movie.poster_path ? (
                <img
                  src={tmdbImageUrl(movie.poster_path, "w200")}
                  alt={movie.title}
                  className="h-full w-full object-cover group-hover/sim:scale-105 transition-transform"
                  loading="lazy"
                />
              ) : (
                <div className="h-full w-full flex items-center justify-center text-gray-600 text-[10px] px-1 text-center">
                  {movie.title}
                </div>
              )}
            </div>
            <p className="mt-1 text-[10px] text-gray-500 line-clamp-1">{movie.title}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

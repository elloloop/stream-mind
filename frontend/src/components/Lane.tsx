"use client";

import { useRef } from "react";
import { Movie } from "@/lib/types";
import MovieCard from "./MovieCard";

interface LaneProps {
  title: string;
  movies: Movie[];
  onInfo: (movie: Movie) => void;
  onWatchedChange?: () => void;
  onRemove?: () => void;
}

export default function Lane({ title, movies, onInfo, onWatchedChange, onRemove }: LaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: "left" | "right") => {
    if (!scrollRef.current) return;
    const amount = scrollRef.current.clientWidth * 0.8;
    scrollRef.current.scrollBy({
      left: direction === "left" ? -amount : amount,
      behavior: "smooth",
    });
  };

  if (!movies.length) return null;

  return (
    <div className="mb-8">
      {/* Lane header */}
      <div className="flex items-center gap-3 px-8 md:px-16 mb-2">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {onRemove && (
          <button
            onClick={onRemove}
            className="text-gray-500 hover:text-gray-300 transition-colors text-sm"
            title="Remove lane"
          >
            &times;
          </button>
        )}
      </div>

      {/* Scrollable row */}
      <div className="group/lane relative">
        {/* Left arrow */}
        <button
          onClick={() => scroll("left")}
          className="absolute left-0 top-0 bottom-6 z-10 w-12 bg-black/50 opacity-0 group-hover/lane:opacity-100 transition-opacity flex items-center justify-center text-white hover:bg-black/70"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <div
          ref={scrollRef}
          className="flex gap-3 overflow-x-auto px-8 md:px-16 scrollbar-hide scroll-smooth"
        >
          {movies.map((movie) => (
            <MovieCard
              key={movie.id}
              movie={movie}
              onInfo={onInfo}
              onWatchedChange={onWatchedChange}
            />
          ))}
        </div>

        {/* Right arrow */}
        <button
          onClick={() => scroll("right")}
          className="absolute right-0 top-0 bottom-6 z-10 w-12 bg-black/50 opacity-0 group-hover/lane:opacity-100 transition-opacity flex items-center justify-center text-white hover:bg-black/70"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}

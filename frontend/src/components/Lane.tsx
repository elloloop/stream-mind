"use client";

import { useRef } from "react";
import { Movie, SearchInsights } from "@/lib/types";
import MovieCard from "./MovieCard";

interface LaneProps {
  title: string;
  movies: Movie[];
  onInfo: (movie: Movie) => void;
  onWatchedChange?: () => void;
  onRemove?: () => void;
  onDismiss?: (movie: Movie) => void;
  insights?: SearchInsights;
  stagger?: boolean;
  icon?: React.ReactNode;
}

export default function Lane({
  title,
  movies,
  onInfo,
  onWatchedChange,
  onRemove,
  onDismiss,
  insights,
  stagger,
  icon,
}: LaneProps) {
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
    <div className="mb-6 md:mb-8 animate-fadeIn">
      {/* Lane header */}
      <div className="flex items-center gap-3 px-6 md:px-16 mb-2">
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <h2 className="text-base md:text-lg font-semibold text-white">{title}</h2>
        <span className="text-xs text-gray-600 font-medium">{movies.length}</span>
        {onRemove && (
          <button
            onClick={onRemove}
            className="text-gray-500 hover:text-gray-300 transition-colors text-sm ml-auto min-h-[44px] min-w-[44px] flex items-center justify-center"
            title="Remove lane"
          >
            &times;
          </button>
        )}
      </div>

      {/* Insights line */}
      {insights && (
        <div className="px-6 md:px-16 mb-2">
          <p className="text-xs text-gray-600">
            {insights.search_text && <span>{insights.search_text}</span>}
            {insights.filters_applied && <span> · {insights.filters_applied}</span>}
            {insights.total_time_ms > 0 && <span> · {Math.round(insights.total_time_ms)}ms</span>}
          </p>
        </div>
      )}

      {/* Divider */}
      <div className="mx-6 md:mx-16 mb-3 border-b border-white/5" />

      {/* Scrollable row */}
      <div className="group/lane relative">
        {/* Left arrow */}
        <button
          onClick={() => scroll("left")}
          className="absolute left-0 top-0 bottom-6 z-10 w-12 bg-black/50 opacity-0 group-hover/lane:opacity-100 transition-opacity hidden md:flex items-center justify-center text-white hover:bg-black/70"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <div
          ref={scrollRef}
          className={`flex gap-2.5 md:gap-3 overflow-x-auto px-6 md:px-16 scrollbar-hide scroll-smooth snap-lane momentum-scroll ${stagger ? "stagger-fade" : ""}`}
        >
          {movies.map((movie) => (
            <MovieCard
              key={movie.id}
              movie={movie}
              onInfo={onInfo}
              onWatchedChange={onWatchedChange}
              onDismiss={onDismiss ? () => onDismiss(movie) : undefined}
            />
          ))}
        </div>

        {/* Right arrow */}
        <button
          onClick={() => scroll("right")}
          className="absolute right-0 top-0 bottom-6 z-10 w-12 bg-black/50 opacity-0 group-hover/lane:opacity-100 transition-opacity hidden md:flex items-center justify-center text-white hover:bg-black/70"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}

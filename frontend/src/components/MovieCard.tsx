"use client";

import { Movie } from "@/lib/types";
import { tmdbImageUrl } from "@/lib/api";
import { isWatched, toggleWatched, isInWatchlist, toggleWatchlist, getRating } from "@/lib/storage";
import { haptic } from "@/lib/identity";
import { useToast } from "./Toast";
import { useState, useRef } from "react";

interface MovieCardProps {
  movie: Movie;
  onInfo: (movie: Movie) => void;
  onWatchedChange?: () => void;
  onDismiss?: () => void;
}

export default function MovieCard({ movie, onInfo, onWatchedChange, onDismiss }: MovieCardProps) {
  const [watched, setWatched] = useState(() => isWatched(movie.id));
  const [inWatchlist, setInWatchlist] = useState(() => isInWatchlist(movie.id));
  const [dismissed, setDismissed] = useState(false);
  const rating = getRating(movie.id);
  const { toast } = useToast();
  const posterUrl = tmdbImageUrl(movie.poster_path, "w300");

  // Swipe tracking
  const touchStartX = useRef(0);
  const touchDelta = useRef(0);
  const cardRef = useRef<HTMLDivElement>(null);

  const handleToggleWatched = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newState = toggleWatched(movie);
    setWatched(newState);
    haptic();
    toast(newState ? "Marked as watched" : "Removed from watched", newState ? "success" : "neutral");
    onWatchedChange?.();
  };

  const handleToggleWatchlist = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newState = toggleWatchlist(movie);
    setInWatchlist(newState);
    haptic();
    toast(newState ? "Added to watchlist" : "Removed from watchlist", newState ? "success" : "neutral");
  };

  // Touch gesture handlers for swipe-to-dismiss
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchDelta.current = 0;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const delta = e.touches[0].clientX - touchStartX.current;
    touchDelta.current = delta;
    if (cardRef.current && delta < 0) {
      cardRef.current.style.transform = `translateX(${delta * 0.5}px)`;
      cardRef.current.style.opacity = `${Math.max(0.3, 1 + delta / 300)}`;
    }
  };

  const handleTouchEnd = () => {
    if (cardRef.current) {
      if (touchDelta.current < -80 && onDismiss) {
        // Trigger dismiss
        cardRef.current.style.transform = "translateX(-100%)";
        cardRef.current.style.opacity = "0";
        cardRef.current.style.transition = "all 0.2s ease-out";
        haptic(15);
        setTimeout(() => {
          setDismissed(true);
          onDismiss();
        }, 200);
      } else {
        cardRef.current.style.transform = "";
        cardRef.current.style.opacity = "";
        cardRef.current.style.transition = "all 0.2s ease-out";
        setTimeout(() => {
          if (cardRef.current) cardRef.current.style.transition = "";
        }, 200);
      }
    }
  };

  if (dismissed) return null;

  const year = movie.release_date?.slice(0, 4);

  return (
    <div
      ref={cardRef}
      className={`group relative flex-shrink-0 w-[120px] sm:w-[140px] md:w-[180px] lg:w-[200px] cursor-pointer transition-transform duration-200 hover:scale-105 hover:z-10 select-none ${
        rating === "up" ? "ring-1 ring-green-500/30 rounded-lg" : ""
      }`}
      onClick={() => onInfo(movie)}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] overflow-hidden rounded-lg bg-gray-800/50">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={movie.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-500 text-xs px-2 text-center">
            {movie.title}
          </div>
        )}

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-200 pointer-events-none" />

        {/* Match score badge */}
        {movie.match_score > 0 && (
          <div className="absolute top-2 left-2 rounded-md bg-yellow-400 px-1.5 py-0.5 text-xs font-bold text-black">
            {Math.round(movie.match_score * 100)}%
          </div>
        )}

        {/* Watched indicator */}
        {watched && (
          <div className="absolute top-2 right-2 rounded-full bg-yellow-400 p-1">
            <svg className="h-3 w-3 text-black" fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
            </svg>
          </div>
        )}

        {/* Watchlist indicator (when not watched) */}
        {!watched && inWatchlist && (
          <div className="absolute top-2 right-2 rounded-full bg-white/20 p-1">
            <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
          </div>
        )}

        {/* Dismiss button (hover only on desktop) */}
        {onDismiss && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
            className="absolute top-1.5 right-1.5 rounded-full bg-black/60 p-1 text-gray-400 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
            title="Dismiss"
          >
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Action buttons on hover */}
        <div className="absolute bottom-0 left-0 right-0 translate-y-full group-hover:translate-y-0 transition-transform duration-200 bg-gradient-to-t from-black/90 to-transparent p-2 pt-8 hidden md:flex justify-between items-end">
          <button
            onClick={handleToggleWatched}
            className="rounded-full border border-gray-400 p-1.5 text-white hover:border-yellow-400 hover:text-yellow-400 transition-colors"
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
            onClick={handleToggleWatchlist}
            className="rounded-full border border-gray-400 p-1.5 text-white hover:border-yellow-400 hover:text-yellow-400 transition-colors"
            title={inWatchlist ? "Remove from watchlist" : "Add to watchlist"}
          >
            <svg className="h-4 w-4" fill={inWatchlist ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onInfo(movie);
            }}
            className="rounded-full border border-gray-400 p-1.5 text-white hover:border-yellow-400 hover:text-yellow-400 transition-colors"
            title="More info"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Title + year below poster */}
      <div className="mt-1.5">
        <p className="text-xs text-gray-400 line-clamp-1">{movie.title}</p>
        {year && (
          <p className="text-[10px] text-gray-600">{year}</p>
        )}
      </div>
    </div>
  );
}

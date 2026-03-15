"use client";

import { Movie } from "@/lib/types";
import { tmdbImageUrl } from "@/lib/api";
import { isWatched, toggleWatched, isInWatchlist, toggleWatchlist, getRating, setRating } from "@/lib/storage";
import { haptic } from "@/lib/identity";
import { useToast } from "./Toast";
import SimilarMovies from "./SimilarMovies";
import { useState, useEffect, useRef, useCallback } from "react";

interface MovieDetailsProps {
  movie: Movie;
  onClose: () => void;
  onWatchedChange?: () => void;
  onSearch?: (query: string) => void;
  onNavigate?: (direction: "prev" | "next") => void;
}

export default function MovieDetails({ movie, onClose, onWatchedChange, onSearch, onNavigate }: MovieDetailsProps) {
  const [watched, setWatched] = useState(() => isWatched(movie.id));
  const [inWatchlist, setInWatchlist] = useState(() => isInWatchlist(movie.id));
  const [currentRating, setCurrentRating] = useState<"up" | "down" | null>(() => getRating(movie.id));
  const [showRatingPrompt, setShowRatingPrompt] = useState(false);
  const { toast } = useToast();
  const backdropUrl = tmdbImageUrl(movie.backdrop_path, "w780");

  // Mobile drag-to-close
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef(0);
  const dragDelta = useRef(0);

  // Reset state when movie changes
  useEffect(() => {
    setWatched(isWatched(movie.id));
    setInWatchlist(isInWatchlist(movie.id));
    setCurrentRating(getRating(movie.id));
    setShowRatingPrompt(false);
  }, [movie.id]);

  // Keyboard handling
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") onNavigate?.("prev");
      if (e.key === "ArrowRight") onNavigate?.("next");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, onNavigate]);

  // Lock body scroll
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  const handleToggleWatched = () => {
    const newState = toggleWatched(movie);
    setWatched(newState);
    haptic();
    toast(newState ? "Marked as watched" : "Removed from watched", newState ? "success" : "neutral");
    onWatchedChange?.();
    if (newState && !currentRating) {
      setShowRatingPrompt(true);
    }
  };

  const handleToggleWatchlist = () => {
    const newState = toggleWatchlist(movie);
    setInWatchlist(newState);
    haptic();
    toast(newState ? "Added to watchlist" : "Removed from watchlist", newState ? "success" : "neutral");
  };

  const handleRate = (rating: "up" | "down") => {
    setRating(movie.id, rating);
    setCurrentRating(rating);
    setShowRatingPrompt(false);
    haptic();
    toast(rating === "up" ? "Liked!" : "Noted", "success");
  };

  const handleShare = async () => {
    const year = movie.release_date?.slice(0, 4);
    const text = `${movie.title}${year ? ` (${year})` : ""}\n${movie.vote_average?.toFixed(1)} · ${movie.genres?.slice(0, 3).join(", ")}\n"${movie.overview?.slice(0, 120)}..."\n\nFrom my StreamMind collection`;

    // Native share (requires secure context)
    if (window.isSecureContext && navigator.share) {
      try {
        await navigator.share({ title: movie.title, text });
        return;
      } catch {
        // User cancelled or not supported — fall through
      }
    }

    // Clipboard fallback (also needs secure context for async API)
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        toast("Copied to clipboard!", "success");
        return;
      } catch {
        // Fall through to textarea hack
      }
    }

    // Final fallback: execCommand (works without secure context)
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      toast("Copied to clipboard!", "success");
    } catch {
      toast("Couldn't share", "error");
    }
  };

  const handleSimilarSelect = useCallback((m: Movie) => {
    // Open details for the similar movie
    // This triggers a re-render with the new movie's data
    onClose();
    setTimeout(() => onSearch?.(`${m.title}`), 100);
  }, [onClose, onSearch]);

  // Mobile drag handlers
  const handleDragStart = (e: React.TouchEvent) => {
    dragStartY.current = e.touches[0].clientY;
    dragDelta.current = 0;
  };

  const handleDragMove = (e: React.TouchEvent) => {
    const delta = e.touches[0].clientY - dragStartY.current;
    dragDelta.current = delta;
    if (sheetRef.current && delta > 0) {
      sheetRef.current.style.transform = `translateY(${delta}px)`;
    }
  };

  const handleDragEnd = () => {
    if (dragDelta.current > 100) {
      onClose();
    } else if (sheetRef.current) {
      sheetRef.current.style.transform = "";
      sheetRef.current.style.transition = "transform 0.2s ease-out";
      setTimeout(() => {
        if (sheetRef.current) sheetRef.current.style.transition = "";
      }, 200);
    }
  };

  const year = movie.release_date?.slice(0, 4);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={sheetRef}
        className="relative w-full md:max-w-3xl max-h-[95vh] md:max-h-[90vh] overflow-y-auto bg-[#161616] shadow-2xl border-t md:border border-white/5 rounded-t-2xl md:rounded-xl animate-slideUp md:animate-fadeInScale"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Mobile drag handle */}
        <div
          className="md:hidden sticky top-0 z-10 bg-[#161616] rounded-t-2xl"
          onTouchStart={handleDragStart}
          onTouchMove={handleDragMove}
          onTouchEnd={handleDragEnd}
        >
          <div className="drag-handle" />
          <div className="h-2" />
        </div>

        {/* Close button (desktop) */}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 z-10 rounded-full bg-black/50 p-1.5 text-white hover:bg-black/70 transition-colors hidden md:block"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Share button */}
        <button
          onClick={(e) => { e.stopPropagation(); handleShare(); }}
          className="absolute right-3 md:right-12 top-3 z-10 rounded-full bg-black/50 p-1.5 text-white hover:bg-black/70 transition-colors"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" />
          </svg>
        </button>

        {/* Backdrop image */}
        {backdropUrl && (
          <div className="relative">
            <img
              src={backdropUrl}
              alt={movie.title}
              className="w-full md:rounded-t-xl object-cover"
              style={{ maxHeight: "300px" }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#161616] via-transparent to-transparent" />

            {/* Title overlay */}
            <div className="absolute bottom-4 left-6 right-6">
              <h2 className="text-2xl md:text-3xl font-bold text-white drop-shadow-lg">
                {movie.title}
              </h2>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="px-6 pb-8 md:pb-6">
          {!backdropUrl && (
            <h2 className="text-2xl md:text-3xl font-bold text-white pt-4 mb-4">
              {movie.title}
            </h2>
          )}

          {/* Meta row */}
          <div className="mt-3 flex flex-wrap items-center gap-2 md:gap-3 text-sm">
            {movie.match_score > 0 && (
              <span className="rounded-full bg-yellow-400/20 border border-yellow-400/40 px-2.5 py-0.5 text-yellow-300 font-semibold text-xs">
                {Math.round(movie.match_score * 100)}% match
              </span>
            )}
            {movie.vote_average > 0 && (
              <span className="text-yellow-400 font-semibold">
                {movie.vote_average.toFixed(1)} / 10
              </span>
            )}
            {movie.imdb_rating && movie.imdb_rating > 0 && (
              <span className="text-gray-400 text-xs">
                IMDb {movie.imdb_rating.toFixed(1)}
              </span>
            )}
            {year && (
              <span className="text-gray-400">{year}</span>
            )}
            {movie.vote_count > 0 && (
              <span className="text-gray-500 text-xs">
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
                  className="rounded-full bg-white/5 border border-white/10 px-3 py-1 text-xs text-gray-300"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}

          {/* Director */}
          {movie.director && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs text-gray-500">Directed by</span>
              <button
                onClick={() => onSearch?.(`${movie.director} movies`)}
                className="text-xs text-yellow-400/80 hover:text-yellow-400 transition-colors"
              >
                {movie.director}
              </button>
            </div>
          )}

          {/* Cast */}
          {movie.cast && movie.cast.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-1.5">Cast</p>
              <div className="flex flex-wrap gap-1.5">
                {movie.cast.slice(0, 8).map((actor) => (
                  <button
                    key={actor}
                    onClick={() => onSearch?.(`${actor} movies`)}
                    className="rounded-full bg-white/5 border border-white/10 px-2.5 py-1 text-xs text-gray-300 hover:border-yellow-400/30 hover:text-yellow-400 transition-colors"
                  >
                    {actor}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Overview */}
          <p className="mt-4 text-sm md:text-base text-gray-300 leading-relaxed">{movie.overview}</p>

          {/* Rating prompt */}
          {showRatingPrompt && (
            <div className="mt-4 flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/5 animate-fadeIn">
              <span className="text-sm text-gray-400">Did you enjoy it?</span>
              <div className="flex gap-2">
                <button
                  onClick={() => handleRate("up")}
                  className={`rounded-full p-2 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center ${
                    currentRating === "up" ? "bg-green-500/20 text-green-400" : "bg-white/5 text-gray-400 hover:text-green-400"
                  }`}
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 .75-.75 2.25 2.25 0 0 1 2.25 2.25c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282m0 0h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 0 1-2.649 7.521c-.388.482-.987.729-1.605.729H13.48c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 0 0-1.423-.23H5.904" />
                  </svg>
                </button>
                <button
                  onClick={() => handleRate("down")}
                  className={`rounded-full p-2 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center ${
                    currentRating === "down" ? "bg-red-500/20 text-red-400" : "bg-white/5 text-gray-400 hover:text-red-400"
                  }`}
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.498 15.25H4.372c-1.026 0-1.945-.694-2.054-1.715a12.137 12.137 0 0 1-.068-1.285c0-2.848.992-5.464 2.649-7.521C5.287 4.247 5.886 4 6.504 4h4.016a4.5 4.5 0 0 1 1.423.23l3.114 1.04a4.5 4.5 0 0 0 1.423.23h1.294M7.498 15.25c.618 0 .991.724.725 1.282A7.471 7.471 0 0 0 7.5 19.75 2.25 2.25 0 0 0 9.75 22a.75.75 0 0 0 .75-.75v-.633c0-.573.11-1.14.322-1.672.304-.76.93-1.33 1.653-1.715a9.04 9.04 0 0 0 2.86-2.4c.498-.634 1.226-1.08 2.032-1.08h.384" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {/* Persistent rating display (if already rated, no prompt) */}
          {currentRating && !showRatingPrompt && (
            <div className="mt-3 flex items-center gap-2">
              <span className={`text-xs ${currentRating === "up" ? "text-green-400" : "text-gray-500"}`}>
                {currentRating === "up" ? "You liked this" : "Not for you"}
              </span>
              <button
                onClick={() => handleRate(currentRating === "up" ? "down" : "up")}
                className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
              >
                Change
              </button>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={handleToggleWatched}
              className={`flex items-center gap-2 rounded-lg px-5 py-2.5 font-medium text-sm transition-colors min-h-[44px] press-scale ${
                watched
                  ? "bg-yellow-400 text-black hover:bg-yellow-300"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
            >
              {watched ? (
                <>
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                  </svg>
                  Watched
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Mark as Watched
                </>
              )}
            </button>

            <button
              onClick={handleToggleWatchlist}
              className={`flex items-center gap-2 rounded-lg px-5 py-2.5 font-medium text-sm transition-colors min-h-[44px] press-scale ${
                inWatchlist
                  ? "bg-white/20 text-white"
                  : "bg-white/10 text-white hover:bg-white/20"
              }`}
            >
              <svg className="h-4 w-4" fill={inWatchlist ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
              </svg>
              {inWatchlist ? "In Watchlist" : "Watchlist"}
            </button>
          </div>

          {/* Similar Movies */}
          <SimilarMovies movieId={movie.id} onSelect={handleSimilarSelect} />
        </div>
      </div>
    </div>
  );
}

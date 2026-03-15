"use client";

import { useState, useEffect, useCallback } from "react";
import { Movie, Lane as LaneType, CustomLane, SearchInsights } from "@/lib/types";
import { searchMovies, getStandardLanes, getHeroMovie, getForYouMovies } from "@/lib/api";
import {
  getWatchedIds,
  getCustomLanes,
  saveCustomLane,
  removeCustomLane,
  getDismissedIds,
  dismissMovie,
  getLikedMovieIds,
  getWatchHistory,
  toggleWatchlist,
} from "@/lib/storage";
import { getDeviceId } from "@/lib/identity";
import { ToastProvider, useToast } from "@/components/Toast";
import Navbar from "@/components/Navbar";
import BottomNav from "@/components/BottomNav";
import Hero from "@/components/Hero";
import SearchBar from "@/components/SearchBar";
import MoodChips from "@/components/MoodChips";
import Lane from "@/components/Lane";
import MovieDetails from "@/components/MovieDetails";
import DismissPopup from "@/components/DismissPopup";
import InstallPrompt from "@/components/InstallPrompt";
import { HeroSkeleton, LaneSkeleton } from "@/components/Skeleton";

function HomeContent() {
  const [heroMovie, setHeroMovie] = useState<Movie | null>(null);
  const [standardLanes, setStandardLanes] = useState<LaneType[]>([]);
  const [customLanes, setCustomLanes] = useState<CustomLane[]>([]);
  const [forYouMovies, setForYouMovies] = useState<Movie[]>([]);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [activeMoodQuery, setActiveMoodQuery] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [dismissingMovie, setDismissingMovie] = useState<Movie | null>(null);
  const { toast } = useToast();

  // Initialize device identity on first load
  useEffect(() => {
    getDeviceId();
  }, []);

  // Keyboard shortcut: "/" to focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "/" && !e.metaKey && !e.ctrlKey) {
        const active = document.activeElement;
        if (active?.tagName !== "INPUT" && active?.tagName !== "TEXTAREA") {
          e.preventDefault();
          const input = document.querySelector<HTMLInputElement>('input[type="text"]');
          input?.focus();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const loadData = useCallback(async () => {
    const watchedIds = getWatchedIds();
    const dismissedIds = getDismissedIds();
    try {
      const [hero, lanes] = await Promise.all([
        getHeroMovie(watchedIds, dismissedIds),
        getStandardLanes(watchedIds, dismissedIds),
      ]);
      setHeroMovie(hero);
      setStandardLanes(lanes);
      setBackendAvailable(true);
    } catch (err) {
      console.error("Failed to load data:", err);
      setBackendAvailable(false);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load For You lane
  const loadForYou = useCallback(async () => {
    const likedIds = getLikedMovieIds();
    if (likedIds.length < 3) {
      setForYouMovies([]);
      return;
    }
    try {
      const movies = await getForYouMovies(likedIds, getWatchedIds(), getDismissedIds());
      setForYouMovies(movies);
    } catch {
      // Silently fail — For You is optional
    }
  }, []);

  useEffect(() => {
    loadData();
    loadForYou();
    setCustomLanes(getCustomLanes());
  }, [loadData, loadForYou, refreshKey]);

  const handleSearch = async (query: string) => {
    setIsSearching(true);
    setActiveMoodQuery(query);
    try {
      const watchedIds = getWatchedIds();
      const dismissedIds = getDismissedIds();
      const result = await searchMovies(query, 10, watchedIds, dismissedIds);

      const insights: SearchInsights = {
        search_text: result.search_text,
        filters_applied: result.filters_applied,
        total_time_ms: result.total_time_ms,
      };

      const newLane: CustomLane = {
        id: `lane_${Date.now()}`,
        query,
        movies: result.movies,
        created_at: Date.now(),
        insights,
      };

      saveCustomLane(newLane);
      setCustomLanes(getCustomLanes());
    } catch (err) {
      console.error("Search failed:", err);
      toast("Search failed. Make sure the backend is running.", "error");
    } finally {
      setIsSearching(false);
    }
  };

  const handleRemoveLane = (laneId: string) => {
    removeCustomLane(laneId);
    setCustomLanes(getCustomLanes());
  };

  const handleWatchedChange = () => {
    setRefreshKey((k) => k + 1);
  };

  const handleDismiss = (movie: Movie) => {
    setDismissingMovie(movie);
  };

  const handleDismissReason = (reason: "seen" | "not_interested" | "not_in_mood" | "bad_suggestion") => {
    if (dismissingMovie) {
      dismissMovie(dismissingMovie.id, reason);
      toast(
        reason === "seen" ? "Marked as seen" : "Dismissed",
        reason === "seen" ? "success" : "neutral"
      );
      setDismissingMovie(null);
      handleWatchedChange();
    }
  };

  const handleAddToWatchlist = (movie: Movie) => {
    toggleWatchlist(movie);
    toast("Added to watchlist", "success");
  };

  const handleSearchFromDetails = (query: string) => {
    setSelectedMovie(null);
    handleSearch(query);
  };

  // Recently watched section
  const watchHistory = getWatchHistory().slice(0, 10);

  return (
    <main className="min-h-screen bg-[#0c0c0c]">
      <Navbar />

      {/* Hero */}
      {loading ? (
        <HeroSkeleton />
      ) : heroMovie ? (
        <Hero movie={heroMovie} onInfo={setSelectedMovie} onAddToWatchlist={handleAddToWatchlist} />
      ) : !backendAvailable ? (
        /* Offline hero banner */
        <div className="relative h-[35vh] md:h-[45vh] min-h-[260px] w-full overflow-hidden bg-gradient-to-b from-[#1a1a1a] to-[#0c0c0c] flex items-end">
          <div className="px-6 pb-10 md:px-16 md:pb-16">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-8 w-8 rounded-lg bg-yellow-400 flex items-center justify-center">
                <svg className="h-4 w-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <span className="text-2xl font-bold tracking-tight text-white">
                stream<span className="text-yellow-400">mind</span>
              </span>
            </div>
            <h1 className="text-xl md:text-3xl font-bold text-white mb-2">Your Movie Collection</h1>
            <p className="text-sm text-gray-500">Browse your saved movies offline. Search requires a connection.</p>
          </div>
        </div>
      ) : null}

      {/* Search bar + Mood chips — only when backend is available */}
      {backendAvailable && (
        <>
          <SearchBar onSearch={handleSearch} isLoading={isSearching} />
          <MoodChips onSelect={handleSearch} activeQuery={activeMoodQuery} disabled={isSearching} />
        </>
      )}

      {/* Offline notice */}
      {!backendAvailable && !loading && (
        <div className="mx-6 md:mx-16 mt-4 mb-4 p-3 rounded-lg bg-yellow-400/5 border border-yellow-400/10">
          <p className="text-xs text-yellow-400/70">
            <svg className="h-3.5 w-3.5 inline mr-1.5 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            Backend unavailable — showing your saved collection. Connect to search and discover new movies.
          </p>
        </div>
      )}

      {/* For You lane */}
      {forYouMovies.length > 0 && (
        <div className="mt-6">
          <Lane
            title="For You"
            movies={forYouMovies}
            onInfo={setSelectedMovie}
            onWatchedChange={handleWatchedChange}
            onDismiss={handleDismiss}
            icon={
              <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            }
          />
        </div>
      )}

      {/* For You teaser */}
      {forYouMovies.length === 0 && getLikedMovieIds().length < 3 && !loading && backendAvailable && (
        <div className="mx-6 md:mx-16 mt-4 mb-2 p-4 rounded-lg bg-white/[0.02] border border-white/5">
          <p className="text-sm text-gray-500">
            <span className="text-yellow-400/60">
              <svg className="h-4 w-4 inline mr-1 -mt-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </span>
            Rate a few movies to unlock personalized picks
          </p>
        </div>
      )}

      {/* Custom AI-generated lanes (always shown — stored in localStorage) */}
      <div className="mt-4">
        {customLanes.map((lane) => (
          <Lane
            key={lane.id}
            title={`"${lane.query}"`}
            movies={lane.movies}
            onInfo={setSelectedMovie}
            onWatchedChange={handleWatchedChange}
            onRemove={() => handleRemoveLane(lane.id)}
            onDismiss={handleDismiss}
            insights={lane.insights}
            stagger
          />
        ))}
      </div>

      {/* Standard lanes (only when backend is available) */}
      {loading ? (
        <>
          <LaneSkeleton />
          <LaneSkeleton />
          <LaneSkeleton />
        </>
      ) : (
        standardLanes.map((lane) => (
          <Lane
            key={lane.name}
            title={lane.name}
            movies={lane.movies}
            onInfo={setSelectedMovie}
            onWatchedChange={handleWatchedChange}
            onDismiss={handleDismiss}
          />
        ))
      )}

      {/* Recently Watched (always available — localStorage) */}
      {watchHistory.length > 0 && (
        <RecentlyWatched
          movies={watchHistory}
          onInfo={setSelectedMovie}
          onWatchedChange={handleWatchedChange}
        />
      )}

      {/* Bottom spacer for mobile nav */}
      <div className="h-24 md:h-20" />

      <BottomNav />
      <InstallPrompt />

      {/* Movie details modal */}
      {selectedMovie && (
        <MovieDetails
          movie={selectedMovie}
          onClose={() => setSelectedMovie(null)}
          onWatchedChange={handleWatchedChange}
          onSearch={backendAvailable ? handleSearchFromDetails : undefined}
        />
      )}

      {/* Dismiss popup */}
      {dismissingMovie && (
        <DismissPopup
          onSelect={handleDismissReason}
          onCancel={() => setDismissingMovie(null)}
        />
      )}
    </main>
  );
}

function RecentlyWatched({
  movies,
  onInfo,
  onWatchedChange,
}: {
  movies: Movie[];
  onInfo: (movie: Movie) => void;
  onWatchedChange: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-4 mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-6 md:px-16 py-2 text-sm text-gray-500 hover:text-gray-300 transition-colors min-h-[44px]"
      >
        <svg
          className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Recently Watched ({movies.length})
      </button>
      {expanded && (
        <Lane
          title=""
          movies={movies}
          onInfo={onInfo}
          onWatchedChange={onWatchedChange}
        />
      )}
    </div>
  );
}

export default function Home() {
  return (
    <ToastProvider>
      <HomeContent />
    </ToastProvider>
  );
}

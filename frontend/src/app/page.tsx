"use client";

import { useState, useEffect, useCallback } from "react";
import { Movie, Lane as LaneType, CustomLane } from "@/lib/types";
import { searchMovies, getStandardLanes, getHeroMovie } from "@/lib/api";
import { getWatchedIds, getCustomLanes, saveCustomLane, removeCustomLane } from "@/lib/storage";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import SearchBar from "@/components/SearchBar";
import Lane from "@/components/Lane";
import MovieDetails from "@/components/MovieDetails";

export default function Home() {
  const [heroMovie, setHeroMovie] = useState<Movie | null>(null);
  const [standardLanes, setStandardLanes] = useState<LaneType[]>([]);
  const [customLanes, setCustomLanes] = useState<CustomLane[]>([]);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadData = useCallback(async () => {
    const watchedIds = getWatchedIds();
    try {
      const [hero, lanes] = await Promise.all([
        getHeroMovie(watchedIds),
        getStandardLanes(watchedIds),
      ]);
      setHeroMovie(hero);
      setStandardLanes(lanes);
      setError(null);
    } catch (err) {
      console.error("Failed to load data:", err);
      setError("Could not connect to the recommendation service. Make sure the backend is running.");
    }
  }, []);

  useEffect(() => {
    loadData();
    setCustomLanes(getCustomLanes());
  }, [loadData, refreshKey]);

  const handleSearch = async (query: string, model?: string) => {
    setIsSearching(true);
    setError(null);
    try {
      const watchedIds = getWatchedIds();
      const result = await searchMovies(query, 10, watchedIds, model);

      const newLane: CustomLane = {
        id: `lane_${Date.now()}`,
        query,
        movies: result.movies,
        created_at: Date.now(),
      };

      saveCustomLane(newLane);
      setCustomLanes(getCustomLanes());
    } catch (err) {
      console.error("Search failed:", err);
      setError("Search failed. Make sure the embedding and recommendation services are running.");
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

  return (
    <main className="min-h-screen bg-[#141414]">
      <Navbar />

      {/* Hero */}
      {heroMovie && (
        <Hero movie={heroMovie} onInfo={setSelectedMovie} />
      )}

      {/* Search bar */}
      <SearchBar onSearch={handleSearch} isLoading={isSearching} />

      {/* Error message */}
      {error && (
        <div className="mx-8 md:mx-16 mb-6 rounded bg-red-900/50 border border-red-700 px-4 py-3 text-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Custom AI-generated lanes */}
      {customLanes.map((lane) => (
        <Lane
          key={lane.id}
          title={`"${lane.query}"`}
          movies={lane.movies}
          onInfo={setSelectedMovie}
          onWatchedChange={handleWatchedChange}
          onRemove={() => handleRemoveLane(lane.id)}
        />
      ))}

      {/* Standard lanes */}
      {standardLanes.map((lane) => (
        <Lane
          key={lane.name}
          title={lane.name}
          movies={lane.movies}
          onInfo={setSelectedMovie}
          onWatchedChange={handleWatchedChange}
        />
      ))}

      {/* Spacer at bottom */}
      <div className="h-20" />

      {/* Movie details modal */}
      {selectedMovie && (
        <MovieDetails
          movie={selectedMovie}
          onClose={() => setSelectedMovie(null)}
          onWatchedChange={handleWatchedChange}
        />
      )}
    </main>
  );
}

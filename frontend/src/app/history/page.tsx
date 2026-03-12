"use client";

import { useState, useEffect } from "react";
import { Movie } from "@/lib/types";
import { getWatchHistory } from "@/lib/storage";
import Navbar from "@/components/Navbar";
import MovieCard from "@/components/MovieCard";
import MovieDetails from "@/components/MovieDetails";

export default function HistoryPage() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);

  const reload = () => {
    setMovies(getWatchHistory());
  };

  useEffect(() => {
    reload();
  }, []);

  return (
    <main className="min-h-screen bg-[#141414]">
      <Navbar />

      <div className="px-8 md:px-16 pt-24 pb-8">
        <h1 className="text-3xl font-bold text-white mb-2">My List</h1>
        <p className="text-gray-400 mb-8">
          {movies.length} movie{movies.length !== 1 ? "s" : ""} watched
        </p>

        {movies.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500">
            <svg className="h-16 w-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
            <p className="text-lg">No movies watched yet</p>
            <p className="text-sm mt-1">Mark movies as watched to see them here</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {movies.map((movie) => (
              <MovieCard
                key={movie.id}
                movie={movie}
                onInfo={setSelectedMovie}
                onWatchedChange={reload}
              />
            ))}
          </div>
        )}
      </div>

      {selectedMovie && (
        <MovieDetails
          movie={selectedMovie}
          onClose={() => setSelectedMovie(null)}
          onWatchedChange={reload}
        />
      )}
    </main>
  );
}

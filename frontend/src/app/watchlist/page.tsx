"use client";

import { useState, useEffect } from "react";
import { Movie } from "@/lib/types";
import { getWatchlistMovies } from "@/lib/storage";
import { ToastProvider, useToast } from "@/components/Toast";
import Navbar from "@/components/Navbar";
import BottomNav from "@/components/BottomNav";
import MovieCard from "@/components/MovieCard";
import MovieDetails from "@/components/MovieDetails";

function WatchlistContent() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const { toast } = useToast();

  const reload = () => {
    setMovies(getWatchlistMovies());
  };

  useEffect(() => {
    reload();
  }, []);

  const handleShareList = async () => {
    if (!movies.length) return;
    const lines = movies.slice(0, 10).map((m) => {
      const year = m.release_date?.slice(0, 4);
      return `${m.title}${year ? ` (${year})` : ""} · ${m.vote_average?.toFixed(1)}`;
    });
    const text = `My StreamMind Watchlist\n\n${lines.join("\n")}${movies.length > 10 ? `\n...and ${movies.length - 10} more` : ""}`;

    if (navigator.share) {
      try {
        await navigator.share({ title: "My StreamMind Watchlist", text });
        return;
      } catch {}
    }
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to clipboard!", "success");
    } catch {
      toast("Couldn't share", "error");
    }
  };

  return (
    <main className="min-h-screen bg-[#0c0c0c]">
      <Navbar />

      <div className="px-6 md:px-16 pt-6 md:pt-24 pb-8">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-2xl md:text-3xl font-bold text-white">Watchlist</h1>
          {movies.length > 0 && (
            <button
              onClick={handleShareList}
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors min-h-[44px] px-3 rounded-lg hover:bg-white/5"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" />
              </svg>
              Share List
            </button>
          )}
        </div>
        <p className="text-gray-400 text-sm mb-8">
          {movies.length} movie{movies.length !== 1 ? "s" : ""} saved
        </p>

        {movies.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500">
            <svg className="h-16 w-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={0.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
            <p className="text-lg">No movies in your watchlist</p>
            <p className="text-sm mt-1 text-gray-600">Save movies to watch later</p>
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-3 md:gap-4">
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

      <div className="h-24 md:h-20" />
      <BottomNav />

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

export default function WatchlistPage() {
  return (
    <ToastProvider>
      <WatchlistContent />
    </ToastProvider>
  );
}

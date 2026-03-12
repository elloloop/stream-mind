import type { Movie, Lane, SearchResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function searchMovies(
  query: string,
  topK: number = 10,
  watchedIds: number[] = []
): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      top_k: topK,
      watched_ids: watchedIds,
    }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

export async function getStandardLanes(
  watchedIds: number[] = []
): Promise<Lane[]> {
  const params = watchedIds.length
    ? `?watched_ids=${watchedIds.join(",")}`
    : "";
  const res = await fetch(`${API_BASE}/api/lanes${params}`);
  if (!res.ok) throw new Error(`Lanes failed: ${res.status}`);
  const data = await res.json();
  return data.lanes;
}

export async function getHeroMovie(
  watchedIds: number[] = []
): Promise<Movie> {
  const params = watchedIds.length
    ? `?watched_ids=${watchedIds.join(",")}`
    : "";
  const res = await fetch(`${API_BASE}/api/hero${params}`);
  if (!res.ok) throw new Error(`Hero failed: ${res.status}`);
  const data = await res.json();
  return data.movie;
}

export async function getMovie(movieId: number): Promise<Movie> {
  const res = await fetch(`${API_BASE}/api/movie/${movieId}`);
  if (!res.ok) throw new Error(`Movie failed: ${res.status}`);
  return res.json();
}

export function tmdbImageUrl(
  path: string,
  size: "w200" | "w300" | "w500" | "w780" | "original" = "w500"
): string {
  if (!path) return "";
  return `https://image.tmdb.org/t/p/${size}${path}`;
}

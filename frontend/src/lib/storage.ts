import type { Movie, CustomLane, DismissReason, DismissedMovies, Ratings } from "./types";

const WATCHED_KEY = "streammind_watched";
const HISTORY_KEY = "streammind_history_objs";
const LANES_KEY = "streammind_lanes";
const DISMISSED_KEY = "streammind_dismissed";
const RATINGS_KEY = "streammind_ratings";
const WATCHLIST_KEY = "streammind_watchlist";
const WATCHLIST_OBJS_KEY = "streammind_watchlist_objs";

// ── Helpers ──────────────────────────────────────────────────────────

function getJSON<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function setJSON(key: string, value: unknown): void {
  localStorage.setItem(key, JSON.stringify(value));
}

// ── Watched ──────────────────────────────────────────────────────────

export function getWatchedIds(): number[] {
  return getJSON<number[]>(WATCHED_KEY, []);
}

export function setWatchedIds(ids: number[]): void {
  setJSON(WATCHED_KEY, ids);
}

export function toggleWatched(movie: Movie): boolean {
  const ids = getWatchedIds();
  const history = getHistoryMovies();
  const watched = ids.includes(movie.id);

  if (watched) {
    setWatchedIds(ids.filter((id) => id !== movie.id));
    setHistoryMovies(history.filter((m) => m.id !== movie.id));
    return false;
  } else {
    setWatchedIds([...ids, movie.id]);
    setHistoryMovies([...history, movie]);
    return true;
  }
}

export function isWatched(movieId: number): boolean {
  return getWatchedIds().includes(movieId);
}

function getHistoryMovies(): Movie[] {
  return getJSON<Movie[]>(HISTORY_KEY, []);
}

function setHistoryMovies(movies: Movie[]): void {
  setJSON(HISTORY_KEY, movies);
}

export function getWatchHistory(): Movie[] {
  return getHistoryMovies();
}

// ── Custom Lanes ─────────────────────────────────────────────────────

export function getCustomLanes(): CustomLane[] {
  return getJSON<CustomLane[]>(LANES_KEY, []);
}

export function saveCustomLane(lane: CustomLane): void {
  const lanes = getCustomLanes();
  lanes.unshift(lane);
  setJSON(LANES_KEY, lanes.slice(0, 10));
}

export function removeCustomLane(laneId: string): void {
  const lanes = getCustomLanes().filter((l) => l.id !== laneId);
  setJSON(LANES_KEY, lanes);
}

// ── Dismissed ────────────────────────────────────────────────────────

export function getDismissedMovies(): DismissedMovies {
  return getJSON<DismissedMovies>(DISMISSED_KEY, {});
}

export function dismissMovie(movieId: number, reason: DismissReason["reason"]): void {
  const dismissed = getDismissedMovies();
  dismissed[movieId] = { reason, timestamp: Date.now() };
  setJSON(DISMISSED_KEY, dismissed);

  // "Already seen it" auto-marks as watched
  if (reason === "seen") {
    const ids = getWatchedIds();
    if (!ids.includes(movieId)) {
      // We don't have the full movie object here, just mark the ID
      setWatchedIds([...ids, movieId]);
    }
  }
}

export function isDismissed(movieId: number): boolean {
  return movieId in getDismissedMovies();
}

export function getDismissedIds(): number[] {
  return Object.keys(getDismissedMovies()).map(Number);
}

// ── Ratings ──────────────────────────────────────────────────────────

export function getRatings(): Ratings {
  return getJSON<Ratings>(RATINGS_KEY, {});
}

export function setRating(movieId: number, rating: "up" | "down"): void {
  const ratings = getRatings();
  ratings[movieId] = rating;
  setJSON(RATINGS_KEY, ratings);
}

export function getRating(movieId: number): "up" | "down" | null {
  return getRatings()[movieId] ?? null;
}

export function getLikedMovieIds(): number[] {
  const ratings = getRatings();
  return Object.entries(ratings)
    .filter(([, v]) => v === "up")
    .map(([k]) => Number(k));
}

// ── Watchlist ────────────────────────────────────────────────────────

export function getWatchlistIds(): number[] {
  return getJSON<number[]>(WATCHLIST_KEY, []);
}

export function getWatchlistMovies(): Movie[] {
  return getJSON<Movie[]>(WATCHLIST_OBJS_KEY, []);
}

export function toggleWatchlist(movie: Movie): boolean {
  const ids = getWatchlistIds();
  const objs = getWatchlistMovies();
  const inList = ids.includes(movie.id);

  if (inList) {
    setJSON(WATCHLIST_KEY, ids.filter((id) => id !== movie.id));
    setJSON(WATCHLIST_OBJS_KEY, objs.filter((m) => m.id !== movie.id));
    return false;
  } else {
    setJSON(WATCHLIST_KEY, [movie.id, ...ids]);
    setJSON(WATCHLIST_OBJS_KEY, [movie, ...objs]);
    return true;
  }
}

export function isInWatchlist(movieId: number): boolean {
  return getWatchlistIds().includes(movieId);
}

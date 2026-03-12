import type { Movie, CustomLane } from "./types";

const WATCHED_KEY = "streammind_watched";
const HISTORY_KEY = "streammind_history_objs";
const LANES_KEY = "streammind_lanes";

export function getWatchedIds(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(WATCHED_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function setWatchedIds(ids: number[]): void {
  localStorage.setItem(WATCHED_KEY, JSON.stringify(ids));
}

export function toggleWatched(movie: Movie): boolean {
  const ids = getWatchedIds();
  const history = getHistoryMovies();
  const isWatched = ids.includes(movie.id);

  if (isWatched) {
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
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function setHistoryMovies(movies: Movie[]): void {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(movies));
}

export function getWatchHistory(): Movie[] {
  return getHistoryMovies();
}

export function getCustomLanes(): CustomLane[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LANES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveCustomLane(lane: CustomLane): void {
  const lanes = getCustomLanes();
  lanes.unshift(lane);
  // Keep max 10 custom lanes
  localStorage.setItem(LANES_KEY, JSON.stringify(lanes.slice(0, 10)));
}

export function removeCustomLane(laneId: string): void {
  const lanes = getCustomLanes().filter((l) => l.id !== laneId);
  localStorage.setItem(LANES_KEY, JSON.stringify(lanes));
}

export interface Movie {
  id: number;
  title: string;
  overview: string;
  poster_path: string;
  backdrop_path: string;
  vote_average: number;
  vote_count: number;
  release_date: string;
  genres: string[];
  popularity: number;
  match_score: number;
  cast?: string[];
  director?: string;
  imdb_rating?: number;
}

export interface Lane {
  name: string;
  movies: Movie[];
}

export interface SearchInsights {
  search_text: string;
  filters_applied: string;
  total_time_ms: number;
}

export interface SearchResponse {
  movies: Movie[];
  query: string;
  rewritten_query: string;
  search_text: string;
  filters_applied: string;
  model: string;
  rewrite_time_ms: number;
  embedding_time_ms: number;
  knn_time_ms: number;
  total_time_ms: number;
}

export interface CustomLane {
  id: string;
  query: string;
  movies: Movie[];
  created_at: number;
  insights?: SearchInsights;
}

export interface DismissReason {
  reason: "seen" | "not_interested" | "not_in_mood" | "bad_suggestion";
  timestamp: number;
}

export interface DismissedMovies {
  [id: number]: DismissReason;
}

export interface Ratings {
  [id: number]: "up" | "down";
}

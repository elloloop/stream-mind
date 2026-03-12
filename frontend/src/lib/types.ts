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
}

export interface Lane {
  name: string;
  movies: Movie[];
}

export interface SearchResponse {
  movies: Movie[];
  query: string;
  embedding_time_ms: number;
  knn_time_ms: number;
  rerank_time_ms: number;
  total_time_ms: number;
}

export interface CustomLane {
  id: string;
  query: string;
  movies: Movie[];
  created_at: number;
}

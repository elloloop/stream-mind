"""
In-memory movie state for KNN search.

Holds the embedding matrix (N, D) and movie metadata, providing fast KNN search
with metadata filtering (actor, director, genre, year, rating, language).
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import numpy as np

logger = logging.getLogger(__name__)

# Map common LLM genre outputs to our data's genre names
GENRE_ALIASES = {
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "romantic": "romance",
    "animated": "animation",
    "anime": "animation",
    "action-adventure": "action",
    "bio": "history",
    "biographical": "history",
    "suspense": "thriller",
}


@dataclass
class MovieFeatures:
    """Movie metadata stored alongside embeddings."""
    movie_id: int
    title: str
    overview: str = ""
    poster_path: str = ""
    backdrop_path: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    release_date: str = ""
    genres: List[str] = field(default_factory=list)
    popularity: float = 0.0
    original_language: str = ""
    imdb_rating: float = 0.0
    cast: List[str] = field(default_factory=list)
    director: str = ""


@dataclass
class QueryFilters:
    """Structured filters extracted from user query by the LLM."""
    actors: List[str] = field(default_factory=list)
    director: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    rating_min: Optional[float] = None
    language: Optional[str] = None


class MovieState:
    """
    In-memory state holding all movie embeddings and metadata.

    Embeddings are L2-normalized at load time so cosine similarity
    reduces to a simple dot product.
    """

    def __init__(self):
        self._embeddings: Optional[np.ndarray] = None  # (N, D) float32, L2-normed
        self._ids: List[int] = []
        self._features: Dict[int, MovieFeatures] = {}
        self._id_to_idx: Dict[int, int] = {}
        self._embedding_dim: int = 0

        # Inverted indexes for fast filtering
        self._actor_index: Dict[str, Set[int]] = defaultdict(set)  # lowercase name -> set of indices
        self._director_index: Dict[str, Set[int]] = defaultdict(set)
        self._genre_index: Dict[str, Set[int]] = defaultdict(set)  # lowercase genre -> set of indices
        self._lang_mask: Dict[str, np.ndarray] = {}

    @property
    def movie_count(self) -> int:
        return len(self._ids)

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    @property
    def embeddings_loaded(self) -> bool:
        return self._embeddings is not None and len(self._ids) > 0

    @property
    def embeddings(self) -> Optional[np.ndarray]:
        return self._embeddings

    def load(
        self,
        movie_ids: List[int],
        embeddings: np.ndarray,
        features_list: List[MovieFeatures],
    ):
        assert len(movie_ids) == embeddings.shape[0] == len(features_list)

        # L2 normalize embeddings for fast cosine similarity via dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-8, None)
        self._embeddings = (embeddings / norms).astype(np.float32)

        self._ids = list(movie_ids)
        self._id_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
        self._features = {f.movie_id: f for f in features_list}
        self._embedding_dim = embeddings.shape[1]

        # Build inverted indexes
        self._actor_index.clear()
        self._director_index.clear()
        self._genre_index.clear()
        self._lang_mask.clear()

        for idx, f in enumerate(features_list):
            for actor in f.cast:
                self._actor_index[actor.lower()].add(idx)
            if f.director:
                self._director_index[f.director.lower()].add(idx)
            for genre in f.genres:
                self._genre_index[genre.lower()].add(idx)

        logger.info(
            f"Loaded {len(movie_ids)} movies with dim={self._embedding_dim}, "
            f"actors={len(self._actor_index)}, directors={len(self._director_index)}, "
            f"genres={len(self._genre_index)}"
        )

    def _get_lang_mask(self, language: str) -> np.ndarray:
        """Get a boolean mask for movies in a given language. Cached."""
        if language not in self._lang_mask:
            mask = np.array(
                [self._features[mid].original_language == language for mid in self._ids],
                dtype=bool,
            )
            self._lang_mask[language] = mask
        return self._lang_mask[language]

    def build_filter_mask(self, filters: QueryFilters) -> np.ndarray:
        """Build a boolean mask from structured filters. True = candidate."""
        n = len(self._ids)
        mask = np.ones(n, dtype=bool)

        # Language filter
        if filters.language:
            mask &= self._get_lang_mask(filters.language)

        # Actor filter — movie must contain ALL requested actors
        for actor in filters.actors:
            actor_key = actor.lower()
            # Fuzzy: check all indexed actors that contain the search term
            matching_indices: Set[int] = set()
            for indexed_name, idx_set in self._actor_index.items():
                if actor_key in indexed_name or indexed_name in actor_key:
                    matching_indices |= idx_set
            if matching_indices:
                actor_mask = np.zeros(n, dtype=bool)
                for idx in matching_indices:
                    actor_mask[idx] = True
                mask &= actor_mask
            else:
                logger.warning(f"Actor '{actor}' not found in index")

        # Director filter
        if filters.director:
            director_key = filters.director.lower()
            matching_indices = set()
            for indexed_name, idx_set in self._director_index.items():
                if director_key in indexed_name or indexed_name in director_key:
                    matching_indices |= idx_set
            if matching_indices:
                dir_mask = np.zeros(n, dtype=bool)
                for idx in matching_indices:
                    dir_mask[idx] = True
                mask &= dir_mask
            else:
                logger.warning(f"Director '{filters.director}' not found in index")

        # Genre filter — movie must match at least one requested genre
        if filters.genres:
            genre_mask = np.zeros(n, dtype=bool)
            for genre in filters.genres:
                genre_key = genre.lower()
                # Apply alias mapping
                genre_key = GENRE_ALIASES.get(genre_key, genre_key)
                if genre_key in self._genre_index:
                    for idx in self._genre_index[genre_key]:
                        genre_mask[idx] = True
            if genre_mask.any():
                mask &= genre_mask

        # Year range filter
        if filters.year_min is not None or filters.year_max is not None:
            for i, mid in enumerate(self._ids):
                if not mask[i]:
                    continue
                f = self._features[mid]
                year_str = f.release_date[:4] if f.release_date else ""
                if not year_str or not year_str.isdigit():
                    mask[i] = False
                    continue
                year = int(year_str)
                if filters.year_min and year < filters.year_min:
                    mask[i] = False
                if filters.year_max and year > filters.year_max:
                    mask[i] = False

        # Rating filter
        if filters.rating_min is not None:
            for i, mid in enumerate(self._ids):
                if not mask[i]:
                    continue
                f = self._features[mid]
                rating = max(f.vote_average, f.imdb_rating)
                if rating < filters.rating_min:
                    mask[i] = False

        return mask

    def get_features(self, movie_id: int) -> Optional[MovieFeatures]:
        return self._features.get(movie_id)

    def get_all_features(self) -> List[MovieFeatures]:
        return [self._features[mid] for mid in self._ids if mid in self._features]

    def search_knn(
        self,
        query_embedding: np.ndarray,
        k: int,
        exclude_ids: Optional[Set[int]] = None,
        candidate_mask: Optional[np.ndarray] = None,
        language: Optional[str] = None,
        boost_popularity: bool = False,
    ) -> List[tuple[int, float]]:
        """
        Exact KNN search using cosine similarity (dot product on L2-normed vectors).

        Args:
            query_embedding: (D,) query vector (will be L2-normalized)
            k: Number of results
            exclude_ids: Movie IDs to exclude
            candidate_mask: Boolean mask (N,) — True = eligible candidate
            language: Language filter (applied if no candidate_mask)
            boost_popularity: If True, blend popularity into scores (for filter-only queries)

        Returns:
            List of (movie_id, score) sorted descending
        """
        if self._embeddings is None:
            return []

        # Normalize query
        q = query_embedding.astype(np.float32)
        norm = np.linalg.norm(q)
        if norm > 1e-8:
            q = q / norm

        # Compute cosine similarities via dot product
        scores = self._embeddings @ q  # (N,)

        # Blend in popularity for filter-heavy queries with little semantic signal
        if boost_popularity:
            pop = np.array(
                [self._features[mid].popularity for mid in self._ids],
                dtype=np.float32,
            )
            # Normalize popularity to [0, 1]
            pop_max = pop.max()
            if pop_max > 0:
                pop_norm = pop / pop_max
            else:
                pop_norm = pop
            # 50/50 blend: embedding similarity + popularity
            scores = 0.5 * scores + 0.5 * pop_norm

        # Apply candidate mask from filters
        if candidate_mask is not None:
            scores[~candidate_mask] = -1e9
        elif language:
            lang_mask = self._get_lang_mask(language)
            scores[~lang_mask] = -1e9

        # Mask excluded IDs
        if exclude_ids:
            for mid in exclude_ids:
                idx = self._id_to_idx.get(mid)
                if idx is not None:
                    scores[idx] = -1e9

        # Get top-k via argpartition (faster than full sort for large N)
        if k >= len(self._ids):
            top_indices = np.argsort(scores)[::-1]
        else:
            partition_indices = np.argpartition(scores, -k)[-k:]
            top_indices = partition_indices[np.argsort(scores[partition_indices])[::-1]]

        return [(self._ids[i], float(scores[i])) for i in top_indices if scores[i] > -1e8]

    def get_embedding(self, movie_id: int) -> Optional[np.ndarray]:
        idx = self._id_to_idx.get(movie_id)
        if idx is None or self._embeddings is None:
            return None
        return self._embeddings[idx]

    def get_movies_by_sort(
        self,
        sort_key: str,
        limit: int = 20,
        exclude_ids: Optional[Set[int]] = None,
        language: Optional[str] = None,
        min_rating: float = 5.0,
    ) -> List[MovieFeatures]:
        """Get movies sorted by a metadata field (for standard lanes)."""
        all_features = self.get_all_features()

        if language:
            all_features = [f for f in all_features if f.original_language == language]

        if exclude_ids:
            all_features = [f for f in all_features if f.movie_id not in exclude_ids]

        # Filter out low-rated movies (use best available rating)
        if min_rating > 0:
            all_features = [
                f for f in all_features
                if max(f.vote_average, f.imdb_rating) >= min_rating
                or f.vote_count < 10  # keep unrated/new movies
            ]

        if sort_key == "popularity":
            all_features.sort(key=lambda f: f.popularity, reverse=True)
        elif sort_key == "vote_average":
            all_features = [f for f in all_features if f.vote_count >= 50]
            all_features.sort(key=lambda f: f.vote_average, reverse=True)
        elif sort_key == "release_date":
            all_features.sort(key=lambda f: f.release_date, reverse=True)
        else:
            all_features.sort(key=lambda f: f.popularity, reverse=True)

        return all_features[:limit]

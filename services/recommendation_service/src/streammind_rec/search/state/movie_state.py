"""
In-memory movie state for KNN search.

Adapted from recommendation_service's MerchantState but simplified for movies.
Holds the embedding matrix (N, D) and movie metadata, providing fast KNN search.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import numpy as np

logger = logging.getLogger(__name__)


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


class MovieState:
    """
    In-memory state holding all movie embeddings and metadata.

    Embeddings are L2-normalized at load time so cosine similarity
    reduces to a simple dot product (exactly like the persona4 service).
    """

    def __init__(self):
        self._embeddings: Optional[np.ndarray] = None  # (N, D) float32, L2-normed
        self._ids: List[int] = []
        self._features: Dict[int, MovieFeatures] = {}
        self._id_to_idx: Dict[int, int] = {}
        self._embedding_dim: int = 0

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
        """
        Load movies into memory.

        Args:
            movie_ids: List of movie IDs (length N)
            embeddings: (N, D) float32 matrix
            features_list: Movie metadata (length N)
        """
        assert len(movie_ids) == embeddings.shape[0] == len(features_list)

        # L2 normalize embeddings for fast cosine similarity via dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-8, None)
        self._embeddings = (embeddings / norms).astype(np.float32)

        self._ids = list(movie_ids)
        self._id_to_idx = {mid: idx for idx, mid in enumerate(movie_ids)}
        self._features = {f.movie_id: f for f in features_list}
        self._embedding_dim = embeddings.shape[1]

        logger.info(
            f"Loaded {len(movie_ids)} movies with dim={self._embedding_dim}"
        )

    def get_features(self, movie_id: int) -> Optional[MovieFeatures]:
        return self._features.get(movie_id)

    def get_all_features(self) -> List[MovieFeatures]:
        return [self._features[mid] for mid in self._ids if mid in self._features]

    def search_knn(
        self,
        query_embedding: np.ndarray,
        k: int,
        exclude_ids: Optional[Set[int]] = None,
    ) -> List[tuple[int, float]]:
        """
        Exact KNN search using cosine similarity (dot product on L2-normed vectors).

        Adapted from ExactKNN in persona4 recommendation_service.

        Args:
            query_embedding: (D,) query vector (will be L2-normalized)
            k: Number of results
            exclude_ids: Movie IDs to exclude

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
            # argpartition gets the top-k in O(N), then we sort just those
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
    ) -> List[MovieFeatures]:
        """Get movies sorted by a metadata field (for standard lanes)."""
        all_features = self.get_all_features()

        if exclude_ids:
            all_features = [f for f in all_features if f.movie_id not in exclude_ids]

        if sort_key == "popularity":
            all_features.sort(key=lambda f: f.popularity, reverse=True)
        elif sort_key == "vote_average":
            # Only consider movies with enough votes
            all_features = [f for f in all_features if f.vote_count >= 50]
            all_features.sort(key=lambda f: f.vote_average, reverse=True)
        elif sort_key == "release_date":
            all_features.sort(key=lambda f: f.release_date, reverse=True)
        else:
            all_features.sort(key=lambda f: f.popularity, reverse=True)

        return all_features[:limit]

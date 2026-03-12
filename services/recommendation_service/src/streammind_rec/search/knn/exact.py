"""
Exact KNN search for movie recommendations.

Reuses the approach from persona4's ExactKNN: brute-force cosine similarity
on L2-normalized embeddings via numpy dot product. Fast enough for ~50K movies.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from streammind_rec.search.state.movie_state import MovieState

logger = logging.getLogger(__name__)


class ExactKNN:
    """
    Exact KNN search using cosine similarity.
    Delegates to MovieState.search_knn for the actual computation.
    """

    def __init__(self, candidate_multiplier: int = 5):
        self._candidate_multiplier = candidate_multiplier

    def search_with_embeddings(
        self,
        state: MovieState,
        query_embedding: np.ndarray,
        k: int,
        exclude_ids: Optional[Set[int]] = None,
    ) -> Tuple[List[Tuple[int, float]], Dict[int, np.ndarray]]:
        """
        Search and return both results and their embeddings (for reranking).

        Returns:
            - List of (movie_id, score) sorted descending
            - Dict mapping movie_id -> embedding vector
        """
        num_candidates = k * self._candidate_multiplier

        results = state.search_knn(
            query_embedding=query_embedding,
            k=num_candidates,
            exclude_ids=exclude_ids,
        )

        embeddings_map: Dict[int, np.ndarray] = {}
        for movie_id, _ in results:
            emb = state.get_embedding(movie_id)
            if emb is not None:
                embeddings_map[movie_id] = emb

        return results, embeddings_map

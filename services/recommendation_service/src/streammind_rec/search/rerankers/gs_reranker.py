"""
Gram-Schmidt Reranker for movie recommendations.

Ported from persona4's GSReranker. Uses orthogonal basis projection
to select diverse results while maintaining relevance to the query.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RerankerResult:
    ranked_ids: List[int]
    ranked_scores: List[float]
    stats: Dict = None

    def __post_init__(self):
        if self.stats is None:
            self.stats = {}


def _l2n(x: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """L2 normalize a vector."""
    if x.ndim == 1:
        n = float(np.linalg.norm(x))
        return x / max(n, eps)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.clip(n, eps, None)


def _proj_onto_basis(vec: np.ndarray, B: Optional[np.ndarray]) -> np.ndarray:
    """Project vector onto orthonormal basis B."""
    if B is None:
        return np.zeros_like(vec)
    return B.T @ (B @ vec)


def gs_select(
    corpus: np.ndarray,
    q: np.ndarray,
    k: int,
    *,
    alpha: float = 0.85,
    block_sim_threshold: Optional[float] = 0.98,
) -> List[int]:
    """
    Gram-Schmidt greedy selection with diversity constraints.

    Directly ported from persona4's _gs_select_np.

    At each step:
    1. Adjust query by subtracting projection onto picked items
    2. Select highest similarity to adjusted query
    3. Block near-duplicates of selected item
    4. Update orthonormal basis
    """
    M = corpus.shape[0]
    k = min(k, M)
    mask = np.zeros(M, dtype=bool)

    picked: List[int] = []
    B: Optional[np.ndarray] = None

    # Pre-compute similarity matrix for duplicate blocking
    sim_matrix: Optional[np.ndarray] = None
    if block_sim_threshold is not None:
        sim_matrix = corpus @ corpus.T

    for _ in range(k):
        # Adjust query for diversity
        if B is None:
            adjusted_q = q
        else:
            adjusted_q = _l2n(q - alpha * _proj_onto_basis(q, B))

        # Score candidates
        scores = corpus @ adjusted_q
        scores[mask] = -1e9
        j = int(np.argmax(scores))
        picked.append(j)
        mask[j] = True

        # Block near-duplicates
        if sim_matrix is not None:
            mask |= sim_matrix[j] >= float(block_sim_threshold)

        # Update orthonormal basis
        v = corpus[j]
        if B is not None:
            v = v - _proj_onto_basis(v, B)
        v = _l2n(v)
        B = v.reshape(1, -1) if B is None else np.vstack([B, v.reshape(1, -1)])

    return picked


class GSReranker:
    """
    Gram-Schmidt reranker for diverse movie recommendations.
    """

    def __init__(
        self,
        alpha: float = 0.85,
        block_sim_threshold: float = 0.98,
    ):
        self._alpha = alpha
        self._block_sim_threshold = block_sim_threshold

    def rank(
        self,
        candidate_ids: List[int],
        candidate_embeddings: Dict[int, np.ndarray],
        candidate_scores: Dict[int, float],
        query_embedding: np.ndarray,
        top_k: int = 10,
    ) -> RerankerResult:
        """Rank candidates using GS diversity selection."""
        if not candidate_ids:
            return RerankerResult(ranked_ids=[], ranked_scores=[])

        valid_ids = [mid for mid in candidate_ids if mid in candidate_embeddings]
        if not valid_ids:
            return RerankerResult(
                ranked_ids=candidate_ids[:top_k],
                ranked_scores=[candidate_scores.get(mid, 0.0) for mid in candidate_ids[:top_k]],
            )

        vectors = np.array(
            [candidate_embeddings[mid] for mid in valid_ids], dtype=np.float32
        )
        corpus = _l2n(vectors)
        q = _l2n(query_embedding.astype(np.float32))

        indices = gs_select(
            corpus,
            q,
            k=top_k,
            alpha=self._alpha,
            block_sim_threshold=self._block_sim_threshold,
        )

        ranked_ids = [valid_ids[i] for i in indices]
        ranked_scores = [candidate_scores.get(mid, 0.0) for mid in ranked_ids]

        return RerankerResult(
            ranked_ids=ranked_ids,
            ranked_scores=ranked_scores,
            stats={
                "alpha": self._alpha,
                "block_sim_threshold": self._block_sim_threshold,
                "valid_candidates": len(valid_ids),
            },
        )

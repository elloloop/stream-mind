"""
Search pipeline: query -> embedding -> KNN -> rerank -> results.

Orchestrates the full recommendation flow, adapted from persona4's SearchPipeline.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import numpy as np
import httpx

from streammind_rec.search.state.movie_state import MovieState, MovieFeatures
from streammind_rec.search.knn.exact import ExactKNN
from streammind_rec.search.rerankers.gs_reranker import GSReranker, RerankerResult

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    movie: MovieFeatures
    score: float


@dataclass
class SearchResponse:
    results: List[SearchResult]
    embedding_time_ms: float = 0.0
    knn_time_ms: float = 0.0
    rerank_time_ms: float = 0.0
    total_time_ms: float = 0.0


class SearchPipeline:
    """
    Orchestrates: query text -> embedding service -> KNN -> GS rerank -> results.
    """

    def __init__(
        self,
        state: MovieState,
        embedding_service_url: str = "http://embedding-service:8000",
        knn_candidate_multiplier: int = 5,
        reranker_alpha: float = 0.85,
        reranker_block_threshold: float = 0.98,
    ):
        self._state = state
        self._embedding_url = embedding_service_url
        self._knn = ExactKNN(candidate_multiplier=knn_candidate_multiplier)
        self._reranker = GSReranker(
            alpha=reranker_alpha,
            block_sim_threshold=reranker_block_threshold,
        )
        self._http_client = httpx.AsyncClient(timeout=10.0)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        exclude_ids: Optional[Set[int]] = None,
    ) -> SearchResponse:
        """
        Full search pipeline: text -> embed -> KNN -> rerank -> results.
        """
        total_start = time.perf_counter()

        # Step 1: Get query embedding from embedding service
        embed_start = time.perf_counter()
        query_embedding = await self._get_query_embedding(query)
        embedding_time_ms = (time.perf_counter() - embed_start) * 1000

        # Step 2: KNN search
        knn_start = time.perf_counter()
        knn_results, embeddings_map = self._knn.search_with_embeddings(
            state=self._state,
            query_embedding=query_embedding,
            k=top_k,
            exclude_ids=exclude_ids,
        )
        knn_time_ms = (time.perf_counter() - knn_start) * 1000

        # Step 3: Rerank with GS diversity
        rerank_start = time.perf_counter()
        candidate_ids = [mid for mid, _ in knn_results]
        candidate_scores = {mid: score for mid, score in knn_results}

        rerank_result: RerankerResult = self._reranker.rank(
            candidate_ids=candidate_ids,
            candidate_embeddings=embeddings_map,
            candidate_scores=candidate_scores,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        rerank_time_ms = (time.perf_counter() - rerank_start) * 1000

        # Step 4: Build response with movie features
        results: List[SearchResult] = []
        for movie_id, score in zip(rerank_result.ranked_ids, rerank_result.ranked_scores):
            features = self._state.get_features(movie_id)
            if features:
                results.append(SearchResult(movie=features, score=score))

        total_time_ms = (time.perf_counter() - total_start) * 1000

        logger.info(
            f"Search '{query[:50]}' -> {len(results)} results "
            f"(embed={embedding_time_ms:.0f}ms knn={knn_time_ms:.0f}ms "
            f"rerank={rerank_time_ms:.0f}ms total={total_time_ms:.0f}ms)"
        )

        return SearchResponse(
            results=results,
            embedding_time_ms=embedding_time_ms,
            knn_time_ms=knn_time_ms,
            rerank_time_ms=rerank_time_ms,
            total_time_ms=total_time_ms,
        )

    async def _get_query_embedding(self, query: str) -> np.ndarray:
        """Call the embedding service to get a query vector."""
        resp = await self._http_client.post(
            f"{self._embedding_url}/v1/embeddings",
            json={"input": query},
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data["data"][0]["embedding"]
        return np.array(embedding, dtype=np.float32)

    async def close(self):
        await self._http_client.aclose()

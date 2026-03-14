"""
Search pipeline: query -> embedding -> KNN -> results.

Supports multiple embedding models for A/B testing.
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import numpy as np
import httpx

from streammind_rec.search.state.movie_state import MovieState, MovieFeatures

logger = logging.getLogger(__name__)

MODEL_CONFIGS = {
    "qwen": {
        "name": "Qwen/Qwen3-Embedding-0.6B",
        "label": "Qwen3 0.6B",
        "query_prompt": "Instruct: Given a movie search query, retrieve relevant movies\nQuery: ",
    },
    "bge": {
        "name": "BAAI/bge-large-en-v1.5",
        "label": "BGE-large",
        "query_prompt": None,
    },
}


@dataclass
class SearchResult:
    movie: MovieFeatures
    score: float


@dataclass
class SearchResponse:
    results: List[SearchResult]
    model: str = ""
    embedding_time_ms: float = 0.0
    knn_time_ms: float = 0.0
    total_time_ms: float = 0.0


class SearchPipeline:
    """
    Orchestrates: query text -> embedding -> KNN -> results.
    Supports multiple embedding models loaded side-by-side.
    """

    def __init__(
        self,
        states: Dict[str, MovieState],
        embedding_service_url: str = "http://embedding-service:8000",
        default_model: str = "minilm",
    ):
        self._states = states
        self._default_model = default_model
        self._embedding_url = embedding_service_url
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._local_models: Dict[str, object] = {}  # lazy-loaded

    @property
    def available_models(self) -> List[str]:
        return list(self._states.keys())

    @property
    def default_model(self) -> str:
        return self._default_model

    def get_state(self, model: str) -> Optional[MovieState]:
        return self._states.get(model)

    async def search(
        self,
        query: str,
        top_k: int = 10,
        exclude_ids: Optional[Set[int]] = None,
        model: Optional[str] = None,
    ) -> SearchResponse:
        """
        Search pipeline: text -> embed -> KNN -> results, ranked by relevance.
        """
        model_key = model if model in self._states else self._default_model
        state = self._states[model_key]

        total_start = time.perf_counter()

        # Step 1: Get query embedding
        embed_start = time.perf_counter()
        query_embedding = await self._get_query_embedding(query, model_key)
        embedding_time_ms = (time.perf_counter() - embed_start) * 1000

        # Step 2: KNN search
        knn_start = time.perf_counter()
        knn_results = state.search_knn(
            query_embedding=query_embedding,
            k=top_k,
            exclude_ids=exclude_ids,
        )
        knn_time_ms = (time.perf_counter() - knn_start) * 1000

        # Step 3: Build response
        results: List[SearchResult] = []
        for movie_id, score in knn_results:
            features = state.get_features(movie_id)
            if features:
                results.append(SearchResult(movie=features, score=score))

        total_time_ms = (time.perf_counter() - total_start) * 1000

        logger.info(
            f"Search[{model_key}] '{query[:50]}' -> {len(results)} results "
            f"(embed={embedding_time_ms:.0f}ms knn={knn_time_ms:.0f}ms "
            f"total={total_time_ms:.0f}ms)"
        )

        return SearchResponse(
            results=results,
            model=model_key,
            embedding_time_ms=embedding_time_ms,
            knn_time_ms=knn_time_ms,
            total_time_ms=total_time_ms,
        )

    async def _get_query_embedding(self, query: str, model_key: str) -> np.ndarray:
        """Call the embedding service or fall back to local model."""
        try:
            resp = await self._http_client.post(
                f"{self._embedding_url}/v1/embeddings",
                json={"input": query, "model": model_key},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data["data"][0]["embedding"]
            return np.array(embedding, dtype=np.float32)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.warning(
                f"Embedding service unavailable, using local {model_key} model: {e}"
            )
            return self._fallback_embedding(query, model_key)

    def _fallback_embedding(self, query: str, model_key: str) -> np.ndarray:
        """Embed query using a local model matching the index embeddings."""
        if model_key not in self._local_models:
            from sentence_transformers import SentenceTransformer
            model_name = MODEL_CONFIGS.get(model_key, {}).get("name", "all-MiniLM-L6-v2")
            logger.info(f"Loading local fallback model: {model_name}")
            self._local_models[model_key] = SentenceTransformer(model_name)
            logger.info(f"Fallback model {model_name} loaded")

        query_prompt = MODEL_CONFIGS.get(model_key, {}).get("query_prompt")
        emb = self._local_models[model_key].encode(
            query,
            prompt=query_prompt,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return emb.astype(np.float32)

    async def close(self):
        await self._http_client.aclose()

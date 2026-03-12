"""
gRPC server for the StreamMind recommendation service.

Implements the RecommendationService proto using grpclib (async-native gRPC).
"""

import logging
import os
import random
import sys
from typing import Optional, Set

# Add the generated proto directory to sys.path so that the generated
# `import streammind.v1.service_pb2` resolves correctly.
_generated_dir = os.path.join(os.path.dirname(__file__), "generated")
if _generated_dir not in sys.path:
    sys.path.insert(0, _generated_dir)

from grpclib.server import Server

from streammind.v1.service_grpc import (  # type: ignore[import-untyped]
    RecommendationServiceBase,
)
from streammind.v1.service_pb2 import (  # type: ignore[import-untyped]
    GetMovieRequest,
    GetMovieResponse,
    GetStandardLanesRequest,
    GetStandardLanesResponse,
    HealthRequest,
    HealthResponse,
    Lane,
    Movie,
    SearchMoviesRequest,
    SearchMoviesResponse,
)
from streammind_rec.search.pipeline import SearchPipeline
from streammind_rec.search.state.movie_state import MovieFeatures, MovieState

logger = logging.getLogger(__name__)


def _features_to_proto(features: MovieFeatures, score: float = 0.0) -> Movie:
    """Convert MovieFeatures to protobuf Movie message."""
    return Movie(
        id=features.movie_id,
        title=features.title,
        overview=features.overview,
        poster_path=features.poster_path,
        backdrop_path=features.backdrop_path,
        vote_average=features.vote_average,
        vote_count=features.vote_count,
        release_date=features.release_date,
        genres=features.genres,
        popularity=features.popularity,
        match_score=score,
    )


class RecommendationServicer(RecommendationServiceBase):
    """gRPC servicer implementing the RecommendationService."""

    def __init__(self, state: MovieState, pipeline: SearchPipeline):
        self._state = state
        self._pipeline = pipeline

    async def SearchMovies(
        self, stream
    ):
        request: SearchMoviesRequest = await stream.recv_message()

        query = request.query
        top_k = request.top_k or 10
        exclude_ids: Optional[Set[int]] = None
        if request.watched_ids:
            exclude_ids = set(request.watched_ids)

        logger.info(f"SearchMovies: query='{query}' top_k={top_k}")

        result = await self._pipeline.search(
            query=query,
            top_k=top_k,
            exclude_ids=exclude_ids,
        )

        movies = [
            _features_to_proto(r.movie, r.score) for r in result.results
        ]

        response = SearchMoviesResponse(
            movies=movies,
            query=query,
            embedding_time_ms=result.embedding_time_ms,
            knn_time_ms=result.knn_time_ms,
            rerank_time_ms=result.rerank_time_ms,
            total_time_ms=result.total_time_ms,
            request_id=request.request_id or "",
        )
        await stream.send_message(response)

    async def GetStandardLanes(self, stream):
        request: GetStandardLanesRequest = await stream.recv_message()

        exclude_ids = set(request.watched_ids) if request.watched_ids else None

        lanes = []

        # Trending Now (by popularity)
        trending = self._state.get_movies_by_sort("popularity", 20, exclude_ids)
        lanes.append(
            Lane(
                name="Trending Now",
                movies=[_features_to_proto(f) for f in trending],
            )
        )

        # Top Rated (by vote_average, min 50 votes)
        top_rated = self._state.get_movies_by_sort("vote_average", 20, exclude_ids)
        lanes.append(
            Lane(
                name="Top Rated",
                movies=[_features_to_proto(f) for f in top_rated],
            )
        )

        # Coming Soon / Recent (by release_date desc)
        recent = self._state.get_movies_by_sort("release_date", 20, exclude_ids)
        lanes.append(
            Lane(
                name="New Releases",
                movies=[_features_to_proto(f) for f in recent],
            )
        )

        await stream.send_message(GetStandardLanesResponse(lanes=lanes))

    async def GetMovie(self, stream):
        request: GetMovieRequest = await stream.recv_message()

        features = self._state.get_features(request.movie_id)
        if not features:
            await stream.send_message(GetMovieResponse())
            return

        await stream.send_message(
            GetMovieResponse(movie=_features_to_proto(features))
        )

    async def Health(self, stream):
        await stream.recv_message()
        await stream.send_message(
            HealthResponse(
                status="ok",
                movie_count=self._state.movie_count,
                embeddings_loaded=self._state.embeddings_loaded,
            )
        )


async def start_grpc_server(
    state: MovieState,
    pipeline: SearchPipeline,
    host: str = "0.0.0.0",
    port: int = 50051,
) -> Server:
    """Start the gRPC server."""
    servicer = RecommendationServicer(state, pipeline)
    server = Server([servicer])
    await server.start(host, port)
    logger.info(f"gRPC server started on {host}:{port}")
    return server

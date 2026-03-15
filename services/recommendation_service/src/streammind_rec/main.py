"""
StreamMind Recommendation Service entry point.

Starts both:
1. A gRPC server (port 50051) for mobile/native clients
2. A FastAPI HTTP server (port 8001) with REST endpoints mirroring the gRPC API

Loads movie embeddings from Arrow files at startup. Supports multiple
embedding models (loaded side-by-side) for A/B testing.
"""

import asyncio
import logging
import os
import random
from typing import Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

from streammind_rec.infra.loader import load_movie_state
from streammind_rec.search.pipeline import SearchPipeline
from streammind_rec.search.state.movie_state import MovieState, MovieFeatures
from streammind_rec.api.grpc.server import start_grpc_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────

# Base directory for Arrow files (contains movies_minilm.arrow, movies_bge.arrow)
DATA_DIR = os.environ.get("DATA_DIR", "/data")
# Legacy single-file path (fallback)
ARROW_PATH = os.environ.get("ARROW_PATH", "")

S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_KEY = os.environ.get("S3_KEY", "")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")

EMBEDDING_SERVICE_URL = os.environ.get(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8000"
)
GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8001"))
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen")

# ── Globals ─────────────────────────────────────────────────────────────

search_pipeline: SearchPipeline | None = None
# Primary state used for non-search endpoints (lanes, hero, etc.)
primary_state: MovieState = MovieState()
grpc_server = None


# ── Pydantic models for REST API ────────────────────────────────────────

class MovieResponse(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: str
    backdrop_path: str
    vote_average: float
    vote_count: int
    release_date: str
    genres: list[str]
    popularity: float
    match_score: float = 0.0
    cast: list[str] = []
    director: str = ""
    imdb_rating: float = 0.0


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    watched_ids: list[int] = []


class SearchResponse(BaseModel):
    movies: list[MovieResponse]
    query: str
    rewritten_query: str = ""
    search_text: str = ""
    filters_applied: str = ""
    model: str
    rewrite_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    knn_time_ms: float = 0.0
    total_time_ms: float = 0.0


class LaneResponse(BaseModel):
    name: str
    movies: list[MovieResponse]


class StandardLanesResponse(BaseModel):
    lanes: list[LaneResponse]


class HeroResponse(BaseModel):
    movie: MovieResponse


class SimilarResponse(BaseModel):
    movies: list[MovieResponse]


class ForYouRequest(BaseModel):
    liked_ids: list[int]
    exclude_ids: list[int] = []


class ForYouResponse(BaseModel):
    movies: list[MovieResponse]


def _to_movie_response(f: MovieFeatures, score: float = 0.0) -> MovieResponse:
    return MovieResponse(
        id=f.movie_id,
        title=f.title,
        overview=f.overview,
        poster_path=f.poster_path,
        backdrop_path=f.backdrop_path,
        vote_average=f.vote_average,
        vote_count=f.vote_count,
        release_date=f.release_date,
        genres=f.genres,
        popularity=f.popularity,
        match_score=score,
        cast=f.cast,
        director=f.director,
        imdb_rating=f.imdb_rating,
    )


# ── App lifecycle ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global primary_state, search_pipeline, grpc_server

    # Pick Arrow file based on backend mode
    backend_mode = os.environ.get("BACKEND_MODE", "hybrid")
    if backend_mode == "gemini":
        arrow_file = os.path.join(DATA_DIR, "movies_gemini.arrow")
    else:
        # local and hybrid both use Qwen embeddings
        arrow_file = os.path.join(DATA_DIR, "movies_qwen.arrow")
    if not os.path.exists(arrow_file) and ARROW_PATH:
        arrow_file = ARROW_PATH

    if os.path.exists(arrow_file):
        logger.info(f"Loading embeddings from {arrow_file}...")
        primary_state = await load_movie_state(arrow_path=arrow_file)
        logger.info(f"  {primary_state.movie_count} movies (dim={primary_state.embedding_dim})")
    else:
        logger.error("No Arrow file found! Check DATA_DIR or ARROW_PATH.")

    search_pipeline = SearchPipeline(
        state=primary_state,
        embedding_service_url=EMBEDDING_SERVICE_URL,
    )

    grpc_server = await start_grpc_server(
        state=primary_state,
        pipeline=search_pipeline,
        port=GRPC_PORT,
    )

    yield

    if grpc_server:
        grpc_server.close()
        await grpc_server.wait_closed()
    if search_pipeline:
        await search_pipeline.close()


app = FastAPI(title="StreamMind Recommendation Service", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "movie_count": primary_state.movie_count,
        "embedding_dim": primary_state.embedding_dim,
    }


@app.post("/api/search", response_model=SearchResponse)
async def search_movies(request: SearchRequest):
    """AI-powered semantic search: user query -> LLM rewrite -> embed -> ranked movies."""
    if not search_pipeline:
        return SearchResponse(
            movies=[], query=request.query, model="",
            embedding_time_ms=0, knn_time_ms=0, total_time_ms=0,
        )

    exclude = set(request.watched_ids) if request.watched_ids else None

    result = await search_pipeline.search(
        query=request.query,
        top_k=request.top_k,
        exclude_ids=exclude,
    )

    movies = [
        _to_movie_response(r.movie, r.score) for r in result.results
        if max(r.movie.vote_average, r.movie.imdb_rating) >= 5.0 or r.movie.vote_count < 10
    ]

    return SearchResponse(
        movies=movies,
        query=request.query,
        rewritten_query=result.query_analysis,
        search_text=result.search_text,
        filters_applied=result.filters_applied,
        model=result.model,
        rewrite_time_ms=result.rewrite_time_ms,
        embedding_time_ms=result.embedding_time_ms,
        knn_time_ms=result.knn_time_ms,
        total_time_ms=result.total_time_ms,
    )


@app.get("/api/lanes", response_model=StandardLanesResponse)
async def get_standard_lanes(
    watched_ids: Optional[str] = Query(None, description="Comma-separated watched movie IDs"),
):
    """Standard browsing lanes (trending, top rated, new releases)."""
    exclude = None
    if watched_ids:
        exclude = set(int(x) for x in watched_ids.split(",") if x.strip())

    lanes = []

    trending = primary_state.get_movies_by_sort("popularity", 20, exclude, language="en")
    lanes.append(LaneResponse(
        name="Trending Now",
        movies=[_to_movie_response(f) for f in trending],
    ))

    top_rated = primary_state.get_movies_by_sort("vote_average", 20, exclude, language="en")
    lanes.append(LaneResponse(
        name="Top Rated",
        movies=[_to_movie_response(f) for f in top_rated],
    ))

    recent = primary_state.get_movies_by_sort("release_date", 20, exclude, language="en")
    lanes.append(LaneResponse(
        name="New Releases",
        movies=[_to_movie_response(f) for f in recent],
    ))

    return StandardLanesResponse(lanes=lanes)


@app.get("/api/hero", response_model=HeroResponse)
async def get_hero(
    watched_ids: Optional[str] = Query(None, description="Comma-separated watched movie IDs"),
):
    """Get a featured movie for the hero section."""
    exclude = None
    if watched_ids:
        exclude = set(int(x) for x in watched_ids.split(",") if x.strip())

    popular = primary_state.get_movies_by_sort("popularity", 10, exclude, language="en")
    with_backdrops = [f for f in popular if f.backdrop_path]
    if not with_backdrops:
        with_backdrops = popular

    if not with_backdrops:
        return HeroResponse(movie=MovieResponse(
            id=0, title="Welcome to StreamMind", overview="Discover movies with AI",
            poster_path="", backdrop_path="", vote_average=0, vote_count=0,
            release_date="", genres=[], popularity=0,
        ))

    featured = random.choice(with_backdrops[:5])
    return HeroResponse(movie=_to_movie_response(featured))


@app.get("/api/movie/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int):
    """Get a single movie's details."""
    features = primary_state.get_features(movie_id)
    if not features:
        raise HTTPException(404, f"Movie {movie_id} not found")
    return _to_movie_response(features)


@app.get("/api/similar/{movie_id}", response_model=SimilarResponse)
async def get_similar(movie_id: int, limit: int = Query(10, ge=1, le=50)):
    """Get similar movies using KNN on the movie's embedding vector."""
    embedding = primary_state.get_embedding(movie_id)
    if embedding is None:
        raise HTTPException(404, f"Movie {movie_id} not found")

    results = primary_state.search_knn(
        query_embedding=embedding,
        k=limit + 1,  # +1 to exclude the movie itself
        exclude_ids={movie_id},
    )

    movies = []
    for mid, score in results[:limit]:
        f = primary_state.get_features(mid)
        if f and (max(f.vote_average, f.imdb_rating) >= 5.0 or f.vote_count < 10):
            movies.append(_to_movie_response(f, score))

    return SimilarResponse(movies=movies)


@app.post("/api/for-you", response_model=ForYouResponse)
async def get_for_you(request: ForYouRequest):
    """Personalized recommendations based on liked movie embeddings."""
    if len(request.liked_ids) < 1:
        return ForYouResponse(movies=[])

    # Collect embeddings for liked movies
    embeddings = []
    for mid in request.liked_ids:
        emb = primary_state.get_embedding(mid)
        if emb is not None:
            embeddings.append(emb)

    if not embeddings:
        return ForYouResponse(movies=[])

    # Average the embeddings to create a taste vector
    taste_vector = np.mean(embeddings, axis=0)

    exclude = set(request.exclude_ids) if request.exclude_ids else set()
    exclude.update(request.liked_ids)

    results = primary_state.search_knn(
        query_embedding=taste_vector,
        k=20,
        exclude_ids=exclude,
    )

    movies = []
    for mid, score in results:
        f = primary_state.get_features(mid)
        if f and (max(f.vote_average, f.imdb_rating) >= 5.0 or f.vote_count < 10):
            movies.append(_to_movie_response(f, score))

    return ForYouResponse(movies=movies)


def main():
    uvicorn.run(
        "streammind_rec.main:app",
        host="0.0.0.0",
        port=HTTP_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()

"""
StreamMind Recommendation Service entry point.

Starts both:
1. A gRPC server (port 50051) for mobile/native clients
2. A FastAPI HTTP server (port 8001) with REST endpoints mirroring the gRPC API

Loads movie embeddings from Arrow files at startup.
"""

import asyncio
import logging
import os
import random
from typing import Optional

import uvicorn
from fastapi import FastAPI, Query
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

ARROW_PATH = os.environ.get("ARROW_PATH", "/data/movies.arrow")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_KEY = os.environ.get("S3_KEY", "")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")

EMBEDDING_SERVICE_URL = os.environ.get(
    "EMBEDDING_SERVICE_URL", "http://embedding-service:8000"
)
GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8001"))

# ── Globals ─────────────────────────────────────────────────────────────

movie_state: MovieState = MovieState()
search_pipeline: SearchPipeline | None = None
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


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    watched_ids: list[int] = []


class SearchResponse(BaseModel):
    movies: list[MovieResponse]
    query: str
    embedding_time_ms: float
    knn_time_ms: float
    rerank_time_ms: float
    total_time_ms: float


class LaneResponse(BaseModel):
    name: str
    movies: list[MovieResponse]


class StandardLanesResponse(BaseModel):
    lanes: list[LaneResponse]


class HeroResponse(BaseModel):
    movie: MovieResponse


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
    )


# ── App lifecycle ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global movie_state, search_pipeline, grpc_server

    logger.info("Loading movie data...")
    movie_state = await load_movie_state(
        arrow_path=ARROW_PATH,
        s3_bucket=S3_BUCKET or None,
        s3_key=S3_KEY or None,
        s3_endpoint=S3_ENDPOINT or None,
    )
    logger.info(f"Loaded {movie_state.movie_count} movies (dim={movie_state.embedding_dim})")

    search_pipeline = SearchPipeline(
        state=movie_state,
        embedding_service_url=EMBEDDING_SERVICE_URL,
    )

    grpc_server = await start_grpc_server(
        state=movie_state,
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


# ── REST endpoints (mirror gRPC interface) ──────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "movie_count": movie_state.movie_count,
        "embeddings_loaded": movie_state.embeddings_loaded,
        "embedding_dim": movie_state.embedding_dim,
    }


@app.post("/api/search", response_model=SearchResponse)
async def search_movies(request: SearchRequest):
    """AI-powered semantic search: user query -> ranked movies."""
    if not search_pipeline:
        return SearchResponse(
            movies=[], query=request.query,
            embedding_time_ms=0, knn_time_ms=0, rerank_time_ms=0, total_time_ms=0,
        )

    exclude = set(request.watched_ids) if request.watched_ids else None

    result = await search_pipeline.search(
        query=request.query,
        top_k=request.top_k,
        exclude_ids=exclude,
    )

    movies = [_to_movie_response(r.movie, r.score) for r in result.results]

    return SearchResponse(
        movies=movies,
        query=request.query,
        embedding_time_ms=result.embedding_time_ms,
        knn_time_ms=result.knn_time_ms,
        rerank_time_ms=result.rerank_time_ms,
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

    trending = movie_state.get_movies_by_sort("popularity", 20, exclude)
    lanes.append(LaneResponse(
        name="Trending Now",
        movies=[_to_movie_response(f) for f in trending],
    ))

    top_rated = movie_state.get_movies_by_sort("vote_average", 20, exclude)
    lanes.append(LaneResponse(
        name="Top Rated",
        movies=[_to_movie_response(f) for f in top_rated],
    ))

    recent = movie_state.get_movies_by_sort("release_date", 20, exclude)
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

    popular = movie_state.get_movies_by_sort("popularity", 10, exclude)
    # Filter to movies with backdrop images
    with_backdrops = [f for f in popular if f.backdrop_path]
    if not with_backdrops:
        with_backdrops = popular

    if not with_backdrops:
        # Fallback
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
    features = movie_state.get_features(movie_id)
    if not features:
        from fastapi import HTTPException
        raise HTTPException(404, f"Movie {movie_id} not found")
    return _to_movie_response(features)


def main():
    uvicorn.run(
        "streammind_rec.main:app",
        host="0.0.0.0",
        port=HTTP_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()

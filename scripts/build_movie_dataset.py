"""
Build the movie embeddings Arrow file.

Fetches movies from TMDB API, generates embeddings via the embedding service,
and writes the result as an Apache Arrow IPC file.

Inspired by persona4's ingestion_service_v2 snapshot creation pipeline:
- Arrow schema with fixed_size_list<float32> for embeddings
- LZ4 compression
- Chunked processing

Usage:
    # With embedding service running locally:
    TMDB_API_KEY=your_key python scripts/build_movie_dataset.py

    # Or with pre-existing embeddings:
    python scripts/build_movie_dataset.py --skip-embeddings --input movies.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
EMBEDDING_SERVICE_URL = os.environ.get("EMBEDDING_SERVICE_URL", "http://localhost:8000")
BATCH_SIZE = 32  # Embedding batch size


async def fetch_tmdb_movies(
    api_key: str,
    pages: int = 50,
) -> list[dict]:
    """Fetch popular movies from TMDB API."""
    movies = []
    seen_ids = set()

    endpoints = [
        "/movie/popular",
        "/movie/top_rated",
        "/movie/now_playing",
        "/movie/upcoming",
        "/discover/movie?sort_by=vote_count.desc",
        "/discover/movie?sort_by=revenue.desc",
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints:
            pages_per_endpoint = pages // len(endpoints)
            for page in range(1, pages_per_endpoint + 1):
                sep = "&" if "?" in endpoint else "?"
                url = f"{TMDB_BASE_URL}{endpoint}{sep}api_key={api_key}&page={page}&language=en-US"
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()

                    for movie in data.get("results", []):
                        mid = movie["id"]
                        if mid not in seen_ids and movie.get("overview"):
                            seen_ids.add(mid)
                            movies.append(movie)

                except Exception as e:
                    logger.warning(f"Failed to fetch {endpoint} page {page}: {e}")
                    continue

                # Rate limit: TMDB allows ~40 req/10s
                await asyncio.sleep(0.25)

    logger.info(f"Fetched {len(movies)} unique movies from TMDB")
    return movies


async def fetch_movie_details(
    api_key: str,
    movie_ids: list[int],
) -> dict[int, dict]:
    """Fetch detailed movie info (genres, etc) from TMDB."""
    details = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, mid in enumerate(movie_ids):
            try:
                url = f"{TMDB_BASE_URL}/movie/{mid}?api_key={api_key}&language=en-US"
                resp = await client.get(url)
                resp.raise_for_status()
                details[mid] = resp.json()
            except Exception as e:
                logger.warning(f"Failed to fetch details for movie {mid}: {e}")

            if (i + 1) % 40 == 0:
                await asyncio.sleep(10)  # Rate limit
            else:
                await asyncio.sleep(0.25)

            if (i + 1) % 100 == 0:
                logger.info(f"Fetched details for {i + 1}/{len(movie_ids)} movies")

    return details


def build_embedding_text(movie: dict, details: dict | None = None) -> str:
    """Build text for embedding from movie metadata."""
    parts = []

    title = movie.get("title", "")
    if title:
        parts.append(f"Title: {title}")

    overview = movie.get("overview", "")
    if overview:
        parts.append(f"Overview: {overview}")

    # Get genres
    genres = []
    if details and "genres" in details:
        genres = [g["name"] for g in details["genres"]]
    elif "genre_ids" in movie:
        # Map genre IDs to names
        genre_map = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
            80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
            14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
            9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
            10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
        }
        genres = [genre_map.get(gid, "") for gid in movie["genre_ids"]]
        genres = [g for g in genres if g]

    if genres:
        parts.append(f"Genres: {', '.join(genres)}")

    release_date = movie.get("release_date", "")
    if release_date:
        year = release_date[:4]
        parts.append(f"Year: {year}")

    return " | ".join(parts)


async def generate_embeddings(
    texts: list[str],
    service_url: str,
) -> np.ndarray:
    """Generate embeddings via the embedding service."""
    all_embeddings = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            resp = await client.post(
                f"{service_url}/v1/embeddings",
                json={"input": batch},
            )
            resp.raise_for_status()
            data = resp.json()

            batch_embs = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embs)

            if (i + BATCH_SIZE) % 100 < BATCH_SIZE:
                logger.info(f"Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)} texts")

    return np.array(all_embeddings, dtype=np.float32)


def write_arrow_file(
    movies: list[dict],
    details_map: dict[int, dict],
    embeddings: np.ndarray,
    output_path: str,
):
    """
    Write the movie dataset as an Arrow IPC file.

    Schema mirrors persona4's snapshot format adapted for movies:
    - movie_id: int32
    - title: string
    - overview: string
    - poster_path, backdrop_path: string
    - vote_average: float64
    - vote_count: int32
    - release_date: string
    - genres: string (JSON array)
    - popularity: float64
    - embedding: fixed_size_list<float32>[D]
    """
    embedding_dim = embeddings.shape[1]

    movie_ids = []
    titles = []
    overviews = []
    poster_paths = []
    backdrop_paths = []
    vote_averages = []
    vote_counts = []
    release_dates = []
    genres_json = []
    popularities = []
    embedding_list = []

    for i, movie in enumerate(movies):
        mid = movie["id"]
        detail = details_map.get(mid, {})

        # Extract genre names
        genres = []
        if "genres" in detail:
            genres = [g["name"] for g in detail["genres"]]
        elif "genre_ids" in movie:
            genre_map = {
                28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
                80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
                14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
                9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
                10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
            }
            genres = [genre_map.get(gid, "") for gid in movie.get("genre_ids", [])]
            genres = [g for g in genres if g]

        movie_ids.append(mid)
        titles.append(movie.get("title", ""))
        overviews.append(movie.get("overview", ""))
        poster_paths.append(movie.get("poster_path", ""))
        backdrop_paths.append(movie.get("backdrop_path", ""))
        vote_averages.append(float(movie.get("vote_average", 0)))
        vote_counts.append(int(movie.get("vote_count", 0)))
        release_dates.append(movie.get("release_date", ""))
        genres_json.append(json.dumps(genres))
        popularities.append(float(movie.get("popularity", 0)))
        embedding_list.append(embeddings[i].tolist())

    # Build Arrow schema with fixed_size_list for embeddings
    embedding_type = pa.list_(pa.float32(), embedding_dim)

    schema = pa.schema([
        ("movie_id", pa.int32()),
        ("title", pa.string()),
        ("overview", pa.string()),
        ("poster_path", pa.string()),
        ("backdrop_path", pa.string()),
        ("vote_average", pa.float64()),
        ("vote_count", pa.int32()),
        ("release_date", pa.string()),
        ("genres", pa.string()),
        ("popularity", pa.float64()),
        ("embedding", embedding_type),
    ])

    table = pa.table(
        {
            "movie_id": pa.array(movie_ids, type=pa.int32()),
            "title": pa.array(titles, type=pa.string()),
            "overview": pa.array(overviews, type=pa.string()),
            "poster_path": pa.array(poster_paths, type=pa.string()),
            "backdrop_path": pa.array(backdrop_paths, type=pa.string()),
            "vote_average": pa.array(vote_averages, type=pa.float64()),
            "vote_count": pa.array(vote_counts, type=pa.int32()),
            "release_date": pa.array(release_dates, type=pa.string()),
            "genres": pa.array(genres_json, type=pa.string()),
            "popularity": pa.array(popularities, type=pa.float64()),
            "embedding": pa.FixedSizeListArray.from_arrays(
                pa.array(np.array(embedding_list).flatten(), type=pa.float32()),
                embedding_dim,
            ),
        },
        schema=schema,
    )

    # Write with LZ4 compression (as in persona4's snapshot pipeline)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    options = ipc.IpcWriteOptions(compression="lz4")
    with ipc.new_file(output_path, schema, options=options) as writer:
        writer.write_table(table)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(
        f"Wrote {len(movies)} movies to {output_path} "
        f"({file_size_mb:.1f} MB, dim={embedding_dim})"
    )


async def main():
    parser = argparse.ArgumentParser(description="Build StreamMind movie dataset")
    parser.add_argument("--output", default="data/movies.arrow", help="Output Arrow file path")
    parser.add_argument("--pages", type=int, default=50, help="TMDB pages to fetch")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embedding generation")
    parser.add_argument("--embedding-url", default=EMBEDDING_SERVICE_URL)
    parser.add_argument("--movies-json", help="Load movies from JSON instead of TMDB")
    args = parser.parse_args()

    api_key = os.environ.get("TMDB_API_KEY", "")

    # Step 1: Get movies
    if args.movies_json:
        with open(args.movies_json) as f:
            movies = json.load(f)
        logger.info(f"Loaded {len(movies)} movies from {args.movies_json}")
    else:
        if not api_key:
            logger.error("Set TMDB_API_KEY environment variable")
            sys.exit(1)
        movies = await fetch_tmdb_movies(api_key, pages=args.pages)

    if not movies:
        logger.error("No movies found")
        sys.exit(1)

    # Step 2: Fetch details (for genres)
    details_map = {}
    if api_key and not args.movies_json:
        logger.info("Fetching movie details for genre info...")
        details_map = await fetch_movie_details(
            api_key, [m["id"] for m in movies]
        )

    # Step 3: Generate embeddings
    if args.skip_embeddings:
        # Generate random embeddings for testing
        logger.info("Generating random embeddings (skip-embeddings mode)")
        embedding_dim = 1536  # Qwen2 1.5B dim
        embeddings = np.random.randn(len(movies), embedding_dim).astype(np.float32)
    else:
        logger.info(f"Generating embeddings via {args.embedding_url}...")
        texts = [build_embedding_text(m, details_map.get(m["id"])) for m in movies]
        embeddings = await generate_embeddings(texts, args.embedding_url)

    # Step 4: Write Arrow file
    write_arrow_file(movies, details_map, embeddings, args.output)

    # Also save raw movies JSON for debugging
    json_path = args.output.replace(".arrow", ".json")
    with open(json_path, "w") as f:
        json.dump(movies, f, indent=2)
    logger.info(f"Saved raw movies JSON to {json_path}")


if __name__ == "__main__":
    asyncio.run(main())

"""
Movie data loader from Arrow files.

Loads pre-computed movie embeddings from Arrow files (local or S3).
Inspired by persona4's SnapshotLoader but simplified for the movie domain.

Arrow Schema:
  - movie_id: int32
  - title: string
  - overview: string
  - poster_path: string
  - backdrop_path: string
  - vote_average: float64
  - vote_count: int32
  - release_date: string
  - genres: string (JSON array)
  - popularity: float64
  - embedding: fixed_size_list<float32>[D]
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc

from streammind_rec.search.state.movie_state import MovieFeatures, MovieState

logger = logging.getLogger(__name__)


def load_arrow_file(path: str) -> pa.Table:
    """Load an Arrow IPC file from local disk."""
    logger.info(f"Loading Arrow file: {path}")
    with pa.memory_map(path, "r") as source:
        reader = ipc.open_file(source)
        table = reader.read_all()
    logger.info(f"Loaded {table.num_rows} rows from {path}")
    return table


async def load_arrow_from_s3(
    bucket: str,
    key: str,
    endpoint_url: Optional[str] = None,
    region: str = "us-east-1",
) -> pa.Table:
    """Load an Arrow IPC file from S3."""
    import aioboto3

    session = aioboto3.Session()
    kwargs = {"region_name": region}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    async with session.client("s3", **kwargs) as s3:
        resp = await s3.get_object(Bucket=bucket, Key=key)
        data = await resp["Body"].read()

    reader = ipc.open_file(pa.BufferReader(data))
    table = reader.read_all()
    logger.info(f"Loaded {table.num_rows} rows from s3://{bucket}/{key}")
    return table


def arrow_table_to_state(table: pa.Table) -> MovieState:
    """
    Convert an Arrow table into MovieState (in-memory embeddings + metadata).

    This is the equivalent of persona4's snapshot loading pipeline.
    """
    state = MovieState()

    movie_ids = table.column("movie_id").to_pylist()

    # Extract embeddings from the fixed_size_list column
    embedding_col = table.column("embedding")
    embeddings_list = []
    for i in range(len(embedding_col)):
        chunk = embedding_col[i].as_py()
        embeddings_list.append(chunk)
    embeddings = np.array(embeddings_list, dtype=np.float32)

    # Extract features
    titles = table.column("title").to_pylist()
    overviews = table.column("overview").to_pylist()
    poster_paths = table.column("poster_path").to_pylist()
    backdrop_paths = table.column("backdrop_path").to_pylist()
    vote_averages = table.column("vote_average").to_pylist()
    vote_counts = table.column("vote_count").to_pylist()
    release_dates = table.column("release_date").to_pylist()
    genres_raw = table.column("genres").to_pylist()
    popularities = table.column("popularity").to_pylist()

    features_list = []
    for i in range(len(movie_ids)):
        # Parse genres (stored as JSON string)
        genres = []
        if genres_raw[i]:
            try:
                genres = json.loads(genres_raw[i]) if isinstance(genres_raw[i], str) else genres_raw[i]
            except (json.JSONDecodeError, TypeError):
                genres = []

        features_list.append(
            MovieFeatures(
                movie_id=movie_ids[i],
                title=titles[i] or "",
                overview=overviews[i] or "",
                poster_path=poster_paths[i] or "",
                backdrop_path=backdrop_paths[i] or "",
                vote_average=float(vote_averages[i] or 0),
                vote_count=int(vote_counts[i] or 0),
                release_date=release_dates[i] or "",
                genres=genres,
                popularity=float(popularities[i] or 0),
            )
        )

    state.load(movie_ids, embeddings, features_list)
    return state


async def load_movie_state(
    arrow_path: Optional[str] = None,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
    s3_endpoint: Optional[str] = None,
) -> MovieState:
    """
    Load movie state from either local Arrow file or S3.

    Priority: local path > S3.
    """
    if arrow_path and os.path.exists(arrow_path):
        table = load_arrow_file(arrow_path)
        return arrow_table_to_state(table)

    if s3_bucket and s3_key:
        table = await load_arrow_from_s3(
            bucket=s3_bucket,
            key=s3_key,
            endpoint_url=s3_endpoint,
        )
        return arrow_table_to_state(table)

    raise ValueError(
        "Must provide either arrow_path (local file) or s3_bucket+s3_key"
    )

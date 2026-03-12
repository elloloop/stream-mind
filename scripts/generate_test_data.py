"""
Generate Arrow files from TMDB movie JSONL data with semantic embeddings.

Produces one Arrow file per model for A/B testing:
  - movies_minilm.arrow  (all-MiniLM-L6-v2, 384-dim, fast)
  - movies_bge.arrow      (BAAI/bge-large-en-v1.5, 1024-dim, higher quality)
"""

import json
import os
import sys
import time

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc
from sentence_transformers import SentenceTransformer

DEFAULT_JSONL_PATH = os.path.expanduser("~/Downloads/tmdb_movies.jsonl")

BATCH_SIZE = 256

MODELS = {
    "minilm": "all-MiniLM-L6-v2",
    "bge": "BAAI/bge-large-en-v1.5",
}


def build_embedding_text(raw: dict) -> str:
    """Build a content-focused text representation of a movie for embedding.

    Overview and thematic metadata (genres, keywords) come first to anchor
    the embedding in what the movie is about. Title and credits are appended
    at the end so they inform but don't dominate the vector.
    """
    parts = []

    overview = raw.get("overview", "")
    if overview:
        parts.append(overview)

    tagline = raw.get("tagline", "")
    if tagline:
        parts.append(tagline)

    genres = raw.get("genres", "")
    if genres:
        parts.append(genres.replace("|", ", "))

    keywords = raw.get("keywords", "")
    if keywords:
        kws = [k.strip() for k in keywords.split("|") if k.strip()][:10]
        if kws:
            parts.append(", ".join(kws))

    director = raw.get("director", "")
    if director:
        parts.append(f"directed by {director}")

    cast = raw.get("cast_top10", "")
    if cast:
        actors = []
        for entry in cast.split("|")[:5]:
            name = entry.split(" as ")[0].strip()
            if name:
                actors.append(name)
        if actors:
            parts.append(f"starring {', '.join(actors)}")

    title = raw.get("title", "")
    if title:
        parts.append(title)

    return ". ".join(parts)


def load_movies(jsonl_path: str) -> tuple[list[dict], list[str]]:
    """Load movies from JSONL, returning schema-mapped dicts and embedding texts."""
    movies = []
    texts = []

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)

            genres_str = raw.get("genres", "")
            genres = [g.strip() for g in genres_str.split("|") if g.strip()] if genres_str else []

            movies.append({
                "id": int(raw["tmdb_id"]),
                "title": raw.get("title", ""),
                "overview": raw.get("overview", ""),
                "poster_path": raw.get("poster_path", ""),
                "backdrop_path": raw.get("backdrop_path", ""),
                "vote_average": float(raw.get("vote_average", 0) or 0),
                "vote_count": int(raw.get("vote_count", 0) or 0),
                "release_date": raw.get("release_date", ""),
                "genres": genres,
                "popularity": float(raw.get("popularity", 0) or 0),
            })

            texts.append(build_embedding_text(raw))

    return movies, texts


def write_arrow(movies: list[dict], embeddings: np.ndarray, embedding_dim: int, output_path: str):
    """Write movies + embeddings to an Arrow IPC file."""
    embedding_type = pa.list_(pa.float32(), embedding_dim)

    table = pa.table(
        {
            "movie_id": pa.array([m["id"] for m in movies], type=pa.int32()),
            "title": pa.array([m["title"] for m in movies], type=pa.string()),
            "overview": pa.array([m["overview"] for m in movies], type=pa.string()),
            "poster_path": pa.array([m["poster_path"] for m in movies], type=pa.string()),
            "backdrop_path": pa.array([m["backdrop_path"] for m in movies], type=pa.string()),
            "vote_average": pa.array([m["vote_average"] for m in movies], type=pa.float64()),
            "vote_count": pa.array([m["vote_count"] for m in movies], type=pa.int32()),
            "release_date": pa.array([m["release_date"] for m in movies], type=pa.string()),
            "genres": pa.array([json.dumps(m["genres"]) for m in movies], type=pa.string()),
            "popularity": pa.array([m["popularity"] for m in movies], type=pa.float64()),
            "embedding": pa.FixedSizeListArray.from_arrays(
                pa.array(embeddings.flatten(), type=pa.float32()),
                embedding_dim,
            ),
        },
        schema=pa.schema([
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
        ]),
    )

    options = ipc.IpcWriteOptions(compression="lz4")
    with ipc.new_file(output_path, table.schema, options=options) as writer:
        writer.write_table(table)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  -> {output_path} ({file_size_mb:.1f} MB)")


def main():
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSONL_PATH

    # Allow generating a single model: python generate_test_data.py [jsonl_path] [model_key]
    only_model = sys.argv[2] if len(sys.argv) > 2 else None
    models_to_run = {only_model: MODELS[only_model]} if only_model else MODELS

    if not os.path.exists(jsonl_path):
        print(f"Error: {jsonl_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading movies from {jsonl_path}...")
    movies, texts = load_movies(jsonl_path)
    print(f"Loaded {len(movies)} movies")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(output_dir, exist_ok=True)

    for key, model_name in models_to_run.items():
        print(f"\n{'='*60}")
        print(f"Model: {model_name} ({key})")
        print(f"{'='*60}")

        model = SentenceTransformer(model_name)
        embedding_dim = model.get_sentence_embedding_dimension()
        print(f"Loaded (dim={embedding_dim})")

        start = time.perf_counter()
        embeddings = model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        elapsed = time.perf_counter() - start
        print(f"Encoded in {elapsed:.1f}s ({len(texts)/elapsed:.0f} movies/sec)")

        embeddings = embeddings.astype(np.float32)
        output_path = os.path.join(output_dir, f"movies_{key}.arrow")
        write_arrow(movies, embeddings, embedding_dim, output_path)

        # Free model memory before loading next
        del model, embeddings

    print(f"\nDone! Files in {output_dir}/")


if __name__ == "__main__":
    main()

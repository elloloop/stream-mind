"""
Generate Arrow files from TMDB movie JSONL data with semantic embeddings.

Produces one Arrow file per model for A/B testing:
  - movies_qwen.arrow  (Qwen/Qwen3-Embedding-0.6B, 1024-dim)
  - movies_bge.arrow   (BAAI/bge-large-en-v1.5, 1024-dim)

Document embedding text uses labeled fields so the model understands
the role of each piece of metadata (plot vs cast vs genre etc.).
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
    "qwen": "Qwen/Qwen3-Embedding-0.6B",
    "bge": "BAAI/bge-large-en-v1.5",
}


def build_embedding_text(raw: dict) -> str:
    """Build a labeled, structured text representation for embedding.

    Uses explicit field labels (Plot:, Genres:, etc.) so the embedding model
    understands the role of each piece of metadata. This enables accurate
    retrieval for diverse query types:
      - thematic:  "uplifting prison drama about hope"
      - by person: "Christopher Nolan movies"
      - by genre:  "sci-fi with time travel"
      - by mood:   "dark psychological thriller"
    """
    parts = []

    overview = raw.get("overview", "")
    if overview:
        parts.append(f"Plot: {overview}")

    tagline = raw.get("tagline", "")
    if tagline:
        parts.append(f"Tagline: {tagline}")

    genres = raw.get("genres", "")
    if genres:
        parts.append(f"Genres: {genres.replace('|', ', ')}")

    keywords = raw.get("keywords", "")
    if keywords:
        kws = [k.strip() for k in keywords.split("|") if k.strip()][:15]
        if kws:
            parts.append(f"Themes: {', '.join(kws)}")

    director = raw.get("director", "")
    if director:
        parts.append(f"Director: {director}")

    cast = raw.get("cast_top10", "")
    if cast:
        actors = []
        for entry in cast.split("|")[:5]:
            name = entry.split(" as ")[0].strip()
            if name:
                actors.append(name)
        if actors:
            parts.append(f"Cast: {', '.join(actors)}")

    title = raw.get("title", "")
    year = (raw.get("release_date", "") or "")[:4]
    if title:
        parts.append(f"Title: {title}" + (f" ({year})" if year else ""))

    lang = raw.get("original_language", "")
    if lang and lang != "en":
        spoken = raw.get("spoken_languages", "")
        parts.append(f"Language: {spoken if spoken else lang}")

    collection = raw.get("belongs_to_collection", "")
    if collection:
        parts.append(f"Collection: {collection}")

    return "\n".join(parts)


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

    # Process in chunks to avoid tokenizing all texts at once (OOM on large datasets)
    CHUNK_SIZE = 10000

    for key, model_name in models_to_run.items():
        print(f"\n{'='*60}")
        print(f"Model: {model_name} ({key})")
        print(f"{'='*60}")

        model = SentenceTransformer(model_name)
        embedding_dim = model.get_sentence_embedding_dimension()
        print(f"Loaded (dim={embedding_dim})")

        n = len(texts)
        all_embeddings = np.empty((n, embedding_dim), dtype=np.float32)

        start = time.perf_counter()
        for chunk_start in range(0, n, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, n)
            chunk_texts = texts[chunk_start:chunk_end]

            chunk_embs = model.encode(
                chunk_texts,
                batch_size=BATCH_SIZE,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
            all_embeddings[chunk_start:chunk_end] = chunk_embs.astype(np.float32)

            elapsed_so_far = time.perf_counter() - start
            done = chunk_end
            rate = done / elapsed_so_far
            eta = (n - done) / rate if rate > 0 else 0
            print(f"  [{done}/{n}] {rate:.0f} movies/sec, ETA {eta/60:.0f}min")

        elapsed = time.perf_counter() - start
        print(f"Encoded in {elapsed:.1f}s ({n/elapsed:.0f} movies/sec)")

        output_path = os.path.join(output_dir, f"movies_{key}.arrow")
        write_arrow(movies, all_embeddings, embedding_dim, output_path)

        del model, all_embeddings

    print(f"\nDone! Files in {output_dir}/")


if __name__ == "__main__":
    main()

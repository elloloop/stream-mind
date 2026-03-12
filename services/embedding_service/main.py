"""
StreamMind Embedding Service.

Lightweight FastAPI service wrapping the Alibaba-NLP/gte-Qwen2-1.5B-instruct
embedding model via sentence-transformers. Provides a simple /v1/embeddings
endpoint that converts text queries into dense vectors for KNN search.

Inspired by the compression_embedding_service architecture but simplified
for text-only embedding (no rep tokens, no vLLM, no Redis).
"""

import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional

import torch
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────

MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL",
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
)
DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "512"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "32"))
PORT = int(os.environ.get("PORT", "8000"))


# ── Models ──────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    input: str | list[str]
    model: Optional[str] = None
    request_id: Optional[str] = None


class EmbeddingData(BaseModel):
    index: int
    embedding: list[float]


class EmbedResponse(BaseModel):
    data: list[EmbeddingData]
    model: str
    usage: dict


class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
    embedding_dim: int


# ── App state ───────────────────────────────────────────────────────────

class AppState:
    def __init__(self, model, model_name: str, device: str, embedding_dim: int):
        self.model = model
        self.model_name = model_name
        self.device = device
        self.embedding_dim = embedding_dim


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Loading model: {MODEL_NAME} on {DEVICE}")
    start = time.perf_counter()

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        MODEL_NAME,
        device=DEVICE,
        trust_remote_code=True,
    )
    # Set max sequence length
    model.max_seq_length = MAX_LENGTH

    # Get embedding dimension from a test encode
    test_emb = model.encode(["test"], normalize_embeddings=True)
    embedding_dim = test_emb.shape[1]

    elapsed = time.perf_counter() - start
    logger.info(
        f"Model loaded in {elapsed:.1f}s | dim={embedding_dim} | device={DEVICE}"
    )

    app.state.app_state = AppState(
        model=model,
        model_name=MODEL_NAME,
        device=DEVICE,
        embedding_dim=embedding_dim,
    )
    yield
    logger.info("Shutting down embedding service")


app = FastAPI(title="StreamMind Embedding Service", lifespan=lifespan)


def _get_state() -> AppState:
    state = app.state.app_state
    if state is None:
        raise HTTPException(503, "Model not loaded yet")
    return state


# ── Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    state = _get_state()
    return HealthResponse(
        status="ok",
        model=state.model_name,
        device=state.device,
        embedding_dim=state.embedding_dim,
    )


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbedRequest):
    """
    OpenAI-compatible embedding endpoint.
    Accepts single string or list of strings, returns normalized embeddings.
    """
    state = _get_state()
    start = time.perf_counter()

    # Normalize input to list
    texts = [request.input] if isinstance(request.input, str) else request.input
    if not texts:
        raise HTTPException(400, "input cannot be empty")

    # Encode in batches
    all_embeddings: list[np.ndarray] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embs = state.model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        all_embeddings.append(embs)

    embeddings = np.vstack(all_embeddings) if len(all_embeddings) > 1 else all_embeddings[0]

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"Embedded {len(texts)} text(s) in {elapsed_ms:.1f}ms"
    )

    data = [
        EmbeddingData(index=i, embedding=emb.tolist())
        for i, emb in enumerate(embeddings)
    ]

    return EmbedResponse(
        data=data,
        model=state.model_name,
        usage={"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": 0},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)

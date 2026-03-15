"""
Search pipeline: user query -> LLM intent extraction -> metadata filter -> embedding -> KNN.

The LLM extracts structured filters (actor, director, genre, year, rating) from
the query and separates them from the semantic search text. Filters are applied
as hard metadata constraints, and only the remaining descriptive text is embedded
for semantic KNN search.
"""

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import numpy as np
import httpx

from streammind_rec.search.state.movie_state import MovieState, MovieFeatures, QueryFilters

logger = logging.getLogger(__name__)

# Backend mode:
#   "local"  — local Qwen3 for both LLM + embedding (needs GPU/fast CPU, ~6GB RAM for models)
#   "hybrid" — Gemini API for LLM, local Qwen3 for embedding (no GPU needed, ~1.5GB for embedding model)
#   "gemini" — Gemini API for both LLM + embedding (no local models, needs movies_gemini.arrow)
BACKEND_MODE = os.environ.get("BACKEND_MODE", "hybrid")

# Local model config (used when BACKEND_MODE=local)
EMBEDDING_MODEL = {
    "name": "Qwen/Qwen3-Embedding-0.6B",
    "query_prompt": "Instruct: Given a movie search query, retrieve relevant movies\nQuery: ",
}
REWRITER_MODEL = "Qwen/Qwen3-1.7B"

# Gemini config (used when BACKEND_MODE=gemini)
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_LLM_MODEL = os.environ.get("GEMINI_LLM_MODEL", "gemini-2.5-flash-lite")

INTENT_SYSTEM_PROMPT = """\
You are a movie search query analyzer. Given a user query, extract structured \
filters and the remaining semantic search text.

Extract these filters when explicitly mentioned:
- actors: list of actor/actress names mentioned (people who ACT in movies)
- director: director name if mentioned (people who DIRECT movies — e.g. Spielberg, Nolan, Scorsese, Tarantino, Wes Anderson, Ridley Scott, Kubrick, Coppola are directors, NOT actors). People like Denzel Washington, Clint Eastwood, Ben Affleck are primarily ACTORS even though they sometimes direct — put them in actors unless the user says "directed by".
- genres: ONLY from this list: Action, Comedy, Drama, Romance, Thriller, Horror, Sci-Fi, Fantasy, Animation, Documentary, Mystery, Crime, Adventure, Family, War, Western, Musical, History, Science Fiction. Do NOT invent genres like "Time Travel", "Heist", "Dialogue" — those belong in search_text.
- year_min: earliest year if a year range or specific year is mentioned
- year_max: latest year if a year range is mentioned (same as year_min for a specific year)
- rating_min: minimum rating (out of 10) if mentioned
- language: ISO 639-1 code if a specific language/country is mentioned (e.g. "ja" for Japanese, "ko" for Korean, "fr" for French, "hi" for Hindi, "es" for Spanish, "de" for German, "it" for Italian, "zh" for Chinese). Only set this if user explicitly asks for movies in a specific language or from a specific country.

The search_text should contain ONLY the descriptive/semantic part of the query \
with all filter entities (actor names, director names, genre names, years, \
"movies"/"films") REMOVED. This text will be used for semantic embedding search.

Output valid JSON only, no markdown, no explanation.

Examples:
User: "romantic movies where hero wanders in the desert of leonardo dicaprio"
{"actors":["Leonardo DiCaprio"],"genres":["Romance"],"search_text":"hero wanders in the desert"}

User: "christopher nolan sci-fi movies after 2010"
{"director":"Christopher Nolan","genres":["Sci-Fi"],"year_min":2010,"search_text":""}

User: "feel good comedy with friends hanging out"
{"genres":["Comedy"],"search_text":"feel good friends hanging out"}

User: "dark thriller like Se7en"
{"genres":["Thriller"],"search_text":"dark gritty atmosphere like Se7en"}

User: "tom hanks and meg ryan"
{"actors":["Tom Hanks","Meg Ryan"],"search_text":""}

User: "best movies of 2024 rated above 8"
{"year_min":2024,"year_max":2024,"rating_min":8.0,"search_text":"best highly acclaimed"}

User: "visually stunning anime with deep storyline"
{"genres":["Animation"],"search_text":"visually stunning deep storyline"}

User: "visually stunning ridley scott movies"
{"director":"Ridley Scott","search_text":"visually stunning epic cinematic"}

User: "90s action movies with explosions"
{"genres":["Action"],"year_min":1990,"year_max":1999,"search_text":"explosions"}

User: "movies like inception"
{"search_text":"mind-bending science fiction thriller with complex narrative and dream worlds like Inception"}

User: "japanese horror movies"
{"genres":["Horror"],"language":"ja","search_text":"japanese horror supernatural"}

User: "korean thriller"
{"genres":["Thriller"],"language":"ko","search_text":"korean thriller intense suspense"}

User: "martin scorsese crime drama"
{"director":"Martin Scorsese","genres":["Crime","Drama"],"search_text":""}

User: "wes anderson quirky comedy"
{"director":"Wes Anderson","genres":["Comedy"],"search_text":"quirky whimsical stylized"}

User: "brad pitt and george clooney heist movies"
{"actors":["Brad Pitt","George Clooney"],"search_text":"heist"}

User: "denzel washington thriller"
{"actors":["Denzel Washington"],"genres":["Thriller"],"search_text":""}

User: "movies about time travel"
{"genres":["Science Fiction"],"search_text":"time travel temporal paradox going back in time"}

User: "movies about a bank robbery gone wrong"
{"genres":["Crime","Thriller"],"search_text":"bank robbery gone wrong heist failure"}"""


CACHE_DB_PATH = os.environ.get("GEMINI_CACHE_DB", os.path.join(
    os.environ.get("DATA_DIR", "/data"), "gemini_cache.db"
))


class GeminiCache:
    """SQLite cache for Gemini API calls — saves every request/response for training data."""

    def __init__(self, db_path: str = CACHE_DB_PATH):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _ensure_db(self):
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                query TEXT PRIMARY KEY,
                raw_response TEXT NOT NULL,
                model TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model TEXT NOT NULL,
                dim INTEGER NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        self._conn.commit()
        logger.info(f"Gemini cache initialized at {self._db_path}")

    def get_llm(self, query: str) -> Optional[str]:
        self._ensure_db()
        row = self._conn.execute(
            "SELECT raw_response FROM llm_cache WHERE query = ?", (query,)
        ).fetchone()
        return row[0] if row else None

    def put_llm(self, query: str, raw_response: str, model: str):
        self._ensure_db()
        self._conn.execute(
            "INSERT OR REPLACE INTO llm_cache (query, raw_response, model, timestamp) VALUES (?, ?, ?, ?)",
            (query, raw_response, model, time.time()),
        )
        self._conn.commit()

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        self._ensure_db()
        row = self._conn.execute(
            "SELECT embedding, dim FROM embedding_cache WHERE text = ?", (text,)
        ).fetchone()
        if row:
            return np.frombuffer(row[0], dtype=np.float32).copy()
        return None

    def put_embedding(self, text: str, embedding: np.ndarray, model: str):
        self._ensure_db()
        self._conn.execute(
            "INSERT OR REPLACE INTO embedding_cache (text, embedding, model, dim, timestamp) VALUES (?, ?, ?, ?, ?)",
            (text, embedding.astype(np.float32).tobytes(), model, len(embedding), time.time()),
        )
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


@dataclass
class SearchResult:
    movie: MovieFeatures
    score: float


@dataclass
class SearchResponse:
    results: List[SearchResult]
    model: str = ""
    query_analysis: str = ""
    search_text: str = ""
    filters_applied: str = ""
    rewrite_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    knn_time_ms: float = 0.0
    total_time_ms: float = 0.0


def _parse_analysis_json(raw: str) -> tuple[QueryFilters, str]:
    """Parse LLM JSON output into QueryFilters + search_text."""
    filters = QueryFilters()
    search_text = ""

    json_str = raw
    if "{" in json_str:
        start = json_str.index("{")
        depth = 0
        end = start
        for i in range(start, len(json_str)):
            if json_str[i] == "{":
                depth += 1
            elif json_str[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        json_str = json_str[start:end]

    data = json.loads(json_str)

    if "actors" in data and isinstance(data["actors"], list):
        filters.actors = [a for a in data["actors"] if isinstance(a, str) and a.strip()]
    if "director" in data and data["director"]:
        filters.director = str(data["director"]).strip()
    if "genres" in data and isinstance(data["genres"], list):
        filters.genres = [g for g in data["genres"] if isinstance(g, str) and g.strip()]
    if "year_min" in data and data["year_min"] is not None:
        filters.year_min = int(data["year_min"])
    if "year_max" in data and data["year_max"] is not None:
        filters.year_max = int(data["year_max"])
    if "rating_min" in data and data["rating_min"] is not None:
        filters.rating_min = float(data["rating_min"])
    if "language" in data and data["language"]:
        filters.language = str(data["language"]).strip()
    if "search_text" in data:
        search_text = str(data["search_text"]).strip()

    return filters, search_text


class QueryAnalyzerLocal:
    """Extracts structured intent using a local Qwen3 model (GPU/CPU)."""

    def __init__(self):
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is not None:
            return
        from transformers import AutoModelForCausalLM, AutoTokenizer
        logger.info(f"Loading query analyzer: {REWRITER_MODEL}")
        self._tokenizer = AutoTokenizer.from_pretrained(REWRITER_MODEL)
        self._model = AutoModelForCausalLM.from_pretrained(
            REWRITER_MODEL,
            torch_dtype="auto",
            device_map="auto",
        )
        logger.info("Query analyzer loaded")

    def analyze(self, query: str) -> tuple[QueryFilters, str, str]:
        self._load()
        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
        )
        generated = outputs[0][inputs["input_ids"].shape[1]:]
        raw = self._tokenizer.decode(generated, skip_special_tokens=True).strip()

        filters = QueryFilters()
        search_text = query
        try:
            filters, search_text = _parse_analysis_json(raw)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse LLM output: {e}. Raw: {raw[:200]}")

        return filters, search_text, raw


class QueryAnalyzerGemini:
    """Extracts structured intent using Gemini API (no local GPU needed)."""

    def __init__(self, cache: Optional[GeminiCache] = None):
        self._client = None
        self._cache = cache
        self._last_failure_time: float = 0  # timestamp of last API failure
        self._backoff_until: float = 0  # don't retry until this timestamp

    def _load(self):
        if self._client is not None:
            return
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set")
        self._client = genai.Client(api_key=api_key)
        logger.info(f"Gemini query analyzer ready (model={GEMINI_LLM_MODEL})")

    def analyze(self, query: str) -> tuple[QueryFilters, str, str]:
        # Check cache first
        if self._cache:
            cached = self._cache.get_llm(query)
            if cached is not None:
                logger.info(f"LLM cache hit for: '{query[:50]}'")
                filters = QueryFilters()
                search_text = query
                try:
                    filters, search_text = _parse_analysis_json(cached)
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass
                return filters, search_text, cached

        self._load()

        # Skip retries if we recently failed (backoff for 60s after repeated failures)
        now = time.time()
        if now < self._backoff_until:
            logger.debug("Gemini in backoff period, using fallback")
            return QueryFilters(), query, f"[fallback] {query}"

        # Retry with backoff for transient rate limits
        last_error = None
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=GEMINI_LLM_MODEL,
                    contents=f"{INTENT_SYSTEM_PROMPT}\n\nUser: \"{query}\"",
                    config={"temperature": 0},
                )
                raw = response.text.strip()

                # Success — clear backoff state
                self._backoff_until = 0

                # Cache the response
                if self._cache:
                    self._cache.put_llm(query, raw, GEMINI_LLM_MODEL)

                filters = QueryFilters()
                search_text = query
                try:
                    filters, search_text = _parse_analysis_json(raw)
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse Gemini output: {e}. Raw: {raw[:200]}")

                return filters, search_text, raw
            except Exception as e:
                last_error = e
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = 2 ** attempt * 2  # 2s, 4s, 8s
                    logger.warning(f"Gemini rate limited (attempt {attempt+1}/3), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"Gemini API error: {e}")
                    break

        # Set backoff so subsequent requests don't all wait through retries
        self._backoff_until = time.time() + 60
        logger.warning(f"Gemini unavailable, backing off 60s. Error: {last_error}")
        return QueryFilters(), query, f"[fallback] {query}"


class SearchPipeline:
    """
    Orchestrates: user query -> LLM extract filters -> metadata filter -> embed -> KNN.

    Supports two modes via BACKEND_MODE env var:
    - "local": Uses local Qwen3 models (needs GPU/CPU with ~6GB RAM for models)
    - "gemini": Uses Gemini API for both LLM and embeddings (needs only API key, no GPU)
    """

    def __init__(
        self,
        state: MovieState,
        embedding_service_url: str = "http://embedding-service:8000",
    ):
        self._state = state
        self._embedding_url = embedding_service_url
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._embedding_model = None  # lazy-loaded local model
        self._gemini_client = None  # lazy-loaded Gemini client
        self._mode = BACKEND_MODE
        self._cache = GeminiCache()

        if self._mode in ("gemini", "hybrid"):
            self._analyzer = QueryAnalyzerGemini(cache=self._cache)
            logger.info(f"Pipeline mode: {self._mode} (Gemini LLM)")
        else:
            self._analyzer = QueryAnalyzerLocal()
            logger.info("Pipeline mode: local (Qwen3 models)")

    @property
    def state(self) -> MovieState:
        return self._state

    async def search(
        self,
        query: str,
        top_k: int = 10,
        exclude_ids: Optional[Set[int]] = None,
        language: Optional[str] = "en",
    ) -> SearchResponse:
        total_start = time.perf_counter()

        # Step 1: Extract structured filters + semantic search text
        analyze_start = time.perf_counter()
        filters, search_text, raw_analysis = self._analyzer.analyze(query)
        # Use LLM-extracted language if present, otherwise use default
        if not filters.language:
            filters.language = language
        analyze_time_ms = (time.perf_counter() - analyze_start) * 1000

        # Build filter description for logging/response
        filter_parts = []
        if filters.actors:
            filter_parts.append(f"actors={filters.actors}")
        if filters.director:
            filter_parts.append(f"director={filters.director}")
        if filters.genres:
            filter_parts.append(f"genres={filters.genres}")
        if filters.year_min:
            filter_parts.append(f"year>={filters.year_min}")
        if filters.year_max:
            filter_parts.append(f"year<={filters.year_max}")
        if filters.rating_min:
            filter_parts.append(f"rating>={filters.rating_min}")
        if filters.language:
            filter_parts.append(f"lang={filters.language}")
        filters_desc = ", ".join(filter_parts) if filter_parts else "none"

        logger.info(f"Query: '{query}' -> filters=[{filters_desc}], search_text='{search_text}'")

        # Step 2: Build candidate mask from filters
        candidate_mask = self._state.build_filter_mask(filters)
        candidate_count = int(candidate_mask.sum())
        logger.info(f"Filter narrowed to {candidate_count} candidates")

        # If filters are too restrictive (< 3 results), relax by dropping genre filter
        if candidate_count < 3 and filters.genres:
            logger.info("Too few candidates, relaxing genre filter")
            relaxed = QueryFilters(
                actors=filters.actors,
                director=filters.director,
                year_min=filters.year_min,
                year_max=filters.year_max,
                rating_min=filters.rating_min,
                language=filters.language,
            )
            candidate_mask = self._state.build_filter_mask(relaxed)
            candidate_count = int(candidate_mask.sum())
            logger.info(f"Relaxed to {candidate_count} candidates")

        # Step 3: Embed the semantic search text
        embed_start = time.perf_counter()
        embed_text = search_text if search_text else query
        query_embedding = await self._get_query_embedding(embed_text)
        embedding_time_ms = (time.perf_counter() - embed_start) * 1000

        # Step 4: KNN search within filtered candidates
        # Boost popularity when there's no semantic search text (pure filter queries)
        knn_start = time.perf_counter()
        knn_results = self._state.search_knn(
            query_embedding=query_embedding,
            k=top_k,
            exclude_ids=exclude_ids,
            candidate_mask=candidate_mask,
            boost_popularity=not search_text,
        )
        knn_time_ms = (time.perf_counter() - knn_start) * 1000

        # Step 5: Build response
        results: List[SearchResult] = []
        for movie_id, score in knn_results:
            features = self._state.get_features(movie_id)
            if features:
                results.append(SearchResult(movie=features, score=score))

        total_time_ms = (time.perf_counter() - total_start) * 1000

        logger.info(
            f"Search '{query[:50]}' -> {len(results)} results "
            f"(analyze={analyze_time_ms:.0f}ms embed={embedding_time_ms:.0f}ms "
            f"knn={knn_time_ms:.0f}ms total={total_time_ms:.0f}ms)"
        )

        return SearchResponse(
            results=results,
            model=self._mode,
            query_analysis=raw_analysis,
            search_text=search_text,
            filters_applied=filters_desc,
            rewrite_time_ms=analyze_time_ms,
            embedding_time_ms=embedding_time_ms,
            knn_time_ms=knn_time_ms,
            total_time_ms=total_time_ms,
        )

    async def _get_query_embedding(self, query: str) -> np.ndarray:
        """Get query embedding using configured backend, with SQLite caching."""
        # Check cache first
        cached = self._cache.get_embedding(query)
        if cached is not None:
            logger.info(f"Embedding cache hit for: '{query[:50]}'")
            return cached

        if self._mode == "gemini":
            emb = self._gemini_embed(query)
        else:
            # Local/hybrid mode: try embedding service first, fall back to local model
            try:
                resp = await self._http_client.post(
                    f"{self._embedding_url}/v1/embeddings",
                    json={"input": query, "model": "qwen"},
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data["data"][0]["embedding"]
                emb = np.array(embedding, dtype=np.float32)
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                logger.warning(f"Embedding service unavailable, using local model: {e}")
                emb = self._local_embed(query)

        # Cache the embedding
        model_name = GEMINI_EMBEDDING_MODEL if self._mode == "gemini" else "qwen"
        self._cache.put_embedding(query, emb, model_name)
        return emb

    def _gemini_embed(self, query: str) -> np.ndarray:
        """Embed query using Gemini API."""
        if self._gemini_client is None:
            from google import genai
            from google.genai import types
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set")
            self._gemini_client = genai.Client(api_key=api_key)

        from google.genai import types
        result = self._gemini_client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return np.array(result.embeddings[0].values, dtype=np.float32)

    def _local_embed(self, query: str) -> np.ndarray:
        """Embed query using a local Qwen3-Embedding model."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL['name']}")
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL["name"])
            logger.info("Embedding model loaded")

        emb = self._embedding_model.encode(
            query,
            prompt=EMBEDDING_MODEL["query_prompt"],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return emb.astype(np.float32)

    async def close(self):
        await self._http_client.aclose()
        self._cache.close()

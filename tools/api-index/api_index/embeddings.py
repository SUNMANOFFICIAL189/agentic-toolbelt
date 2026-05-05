"""Local embeddings for semantic search.

Uses fastembed (ONNX-based, no torch dependency) with BAAI/bge-small-en-v1.5
(384 dims). Outputs are L2-normalised, so cosine similarity = dot product.

Storage: separate `apis_embeddings` table keyed by api_id, embedding stored
as float32 BLOB (1,536 bytes per row).
"""
from __future__ import annotations

import sqlite3
from typing import Iterable

import numpy as np

EMBEDDING_DIM = 384
MODEL_NAME = "BAAI/bge-small-en-v1.5"

EMBEDDINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS apis_embeddings (
    api_id      INTEGER PRIMARY KEY,
    embedding   BLOB NOT NULL,
    model       TEXT NOT NULL,
    embedded_at TEXT NOT NULL,
    FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(EMBEDDINGS_SCHEMA)


def _model():
    """Lazy-import fastembed (heavy on first call — downloads ~50MB model)."""
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=MODEL_NAME)


def embed_query(text: str) -> np.ndarray:
    """Embed a single query string. Returns float32 (EMBEDDING_DIM,)."""
    model = _model()
    vec = next(iter(model.embed([text])))
    return np.asarray(vec, dtype=np.float32)


def embed_batch(texts: list[str], batch_size: int = 64) -> Iterable[np.ndarray]:
    """Embed a batch of strings. Yields float32 (EMBEDDING_DIM,) per input."""
    model = _model()
    for vec in model.embed(texts, batch_size=batch_size):
        yield np.asarray(vec, dtype=np.float32)


def has_embeddings(conn: sqlite3.Connection) -> int:
    ensure_schema(conn)
    return conn.execute("SELECT COUNT(*) FROM apis_embeddings").fetchone()[0]


def load_all(conn: sqlite3.Connection) -> tuple[list[int], np.ndarray]:
    """Load all stored embeddings as (ids, matrix shape (N, EMBEDDING_DIM))."""
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT api_id, embedding FROM apis_embeddings ORDER BY api_id"
    ).fetchall()
    if not rows:
        return [], np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    ids = [r[0] for r in rows]
    matrix = np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(
        len(rows), EMBEDDING_DIM
    )
    return ids, matrix


def semantic_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 20,
    candidate_ids: list[int] | None = None,
) -> list[tuple[int, float]]:
    """Return [(api_id, score), ...] ranked by cosine similarity to query.

    If candidate_ids is provided, restrict search to those rows (used for the
    hybrid FTS+rerank flow).
    """
    ids, matrix = load_all(conn)
    if not ids:
        return []

    if candidate_ids:
        mask = np.array([i in set(candidate_ids) for i in ids])
        ids = [i for i, m in zip(ids, mask) if m]
        matrix = matrix[mask]
        if not ids:
            return []

    q = embed_query(query)
    scores = matrix @ q  # both already L2-normalised → dot = cosine
    order = np.argsort(-scores)[:limit]
    return [(ids[i], float(scores[i])) for i in order]

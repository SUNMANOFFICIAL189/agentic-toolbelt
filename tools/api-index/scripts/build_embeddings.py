"""Generate embeddings for every row in the apis table.

Run once after `build_index.py`, then any time the apis table is rebuilt.
Idempotent — `INSERT OR REPLACE` per row.

Total time on M-series Mac: ~30-60s for ~4,000 entries.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from api_index.db import connect  # noqa: E402
from api_index import embeddings as E  # noqa: E402


def _row_text(row) -> str:
    """Combine name + category + description into one string for embedding."""
    parts = [row["name"]]
    if row["category"]:
        parts.append(f"[{row['category']}]")
    if row["description"]:
        parts.append(row["description"])
    return " — ".join(parts)


def main() -> None:
    conn = connect()
    E.ensure_schema(conn)

    rows = conn.execute("SELECT id, name, description, category FROM apis").fetchall()
    print(f"Embedding {len(rows)} rows with {E.MODEL_NAME}...")

    texts = [_row_text(r) for r in rows]
    ids = [r["id"] for r in rows]
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    inserted = 0
    batch_size = 256

    # Stream embeddings in batches to keep memory low.
    for start in range(0, len(rows), batch_size):
        chunk_ids = ids[start : start + batch_size]
        chunk_texts = texts[start : start + batch_size]
        chunk_vecs = list(E.embed_batch(chunk_texts, batch_size=64))

        params = [
            (
                api_id,
                vec.astype(np.float32).tobytes(),
                E.MODEL_NAME,
                now,
            )
            for api_id, vec in zip(chunk_ids, chunk_vecs)
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO apis_embeddings "
            "(api_id, embedding, model, embedded_at) VALUES (?, ?, ?, ?)",
            params,
        )
        conn.commit()
        inserted += len(params)
        print(f"  {inserted}/{len(rows)} embedded")

    print(f"\nDone — {inserted} embeddings stored in {E.MODEL_NAME}")
    conn.close()


if __name__ == "__main__":
    main()

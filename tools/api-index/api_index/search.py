"""Query helpers — keyword search via FTS5, plus filters."""
from __future__ import annotations

import re
import sqlite3

from .db import connect

# FTS5 reserves: " ( ) * : - AND OR NOT NEAR
# We let users use quotes/OR/AND etc. intentionally, but auto-escape bare words
# that contain hyphens or colons (which FTS5 treats as column qualifiers).
_FTS_OPERATORS = {"AND", "OR", "NOT", "NEAR"}
_BARE_TOKEN_RE = re.compile(r'^[A-Za-z0-9_\']+\*?$')


def _sanitise_query(query: str) -> str:
    """Quote bare tokens that would otherwise confuse FTS5 (e.g. 'real-time')."""
    if '"' in query:
        # User opted into explicit phrase syntax — trust them.
        return query

    parts = query.split()
    out: list[str] = []
    for tok in parts:
        if tok in _FTS_OPERATORS or _BARE_TOKEN_RE.match(tok):
            out.append(tok)
        else:
            cleaned = tok.replace('"', "")
            out.append(f'"{cleaned}"')
    return " ".join(out)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def search(
    query: str,
    *,
    auth: str | None = None,
    https_only: bool = False,
    has_openapi: bool = False,
    source: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Full-text search with optional filters."""
    conn = connect()
    try:
        sql = [
            "SELECT a.*, bm25(apis_fts) AS rank",
            "FROM apis a JOIN apis_fts ON a.id = apis_fts.rowid",
            "WHERE apis_fts MATCH ?",
        ]
        params: list = [_sanitise_query(query)]

        if auth:
            sql.append("AND a.auth = ?")
            params.append(auth)
        if https_only:
            sql.append("AND a.https = 1")
        if has_openapi:
            sql.append("AND a.openapi_url IS NOT NULL")
        if source:
            sql.append("AND a.source = ?")
            params.append(source)

        sql.append("ORDER BY rank LIMIT ?")
        params.append(limit)

        rows = conn.execute(" ".join(sql), params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def by_category(category: str, *, limit: int = 50) -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM apis WHERE category = ? ORDER BY name LIMIT ?",
            (category, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def list_categories() -> list[tuple[str, int]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n FROM apis "
            "WHERE category IS NOT NULL GROUP BY category ORDER BY n DESC"
        ).fetchall()
        return [(r["category"], r["n"]) for r in rows]
    finally:
        conn.close()


def show(api_id: int) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM apis WHERE id = ?", (api_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def stats() -> dict:
    conn = connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM apis").fetchone()[0]
        by_source = dict(
            conn.execute("SELECT source, COUNT(*) FROM apis GROUP BY source").fetchall()
        )
        with_openapi = conn.execute(
            "SELECT COUNT(*) FROM apis WHERE openapi_url IS NOT NULL"
        ).fetchone()[0]
        no_auth = conn.execute(
            "SELECT COUNT(*) FROM apis WHERE auth IN ('No', 'apiKey: No', '')"
        ).fetchone()[0]
        cats = len(list_categories())
        return {
            "total": total,
            "by_source": by_source,
            "with_openapi_schema": with_openapi,
            "no_auth_required": no_auth,
            "categories": cats,
        }
    finally:
        conn.close()

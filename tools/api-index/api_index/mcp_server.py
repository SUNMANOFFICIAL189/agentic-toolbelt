"""MCP server exposing the API index over stdio.

Tools:
  - search_apis           — FTS5 keyword search (cheap, fast, default)
  - semantic_search_apis  — embedding-based semantic search
  - hybrid_search_apis    — FTS5 retrieval + embedding rerank (best quality)
  - get_api               — full record by id
  - list_categories       — all categories with counts
  - apis_by_category      — list APIs in a category
  - index_stats           — health metrics

Register in Claude Code's settings.json (mcpServers section):

    {
      "mcpServers": {
        "api-index": {
          "command": "/Users/sunil_rajput/claude-hq/tools/api-index/bin/api-index-mcp",
          "args": []
        }
      }
    }
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import search as S
from .db import connect
from . import embeddings as E

mcp = FastMCP("api-index")


@mcp.tool()
def search_apis(
    query: str,
    limit: int = 20,
    auth: str | None = None,
    https_only: bool = False,
    with_openapi: bool = False,
    source: str | None = None,
) -> list[dict]:
    """Full-text keyword search over the API index. Fast, default search method.

    Args:
        query: FTS5 query (supports OR, AND, NEAR, prefix*).
        limit: max results to return (default 20).
        auth: filter by auth value (e.g. "No", "apiKey", "OAuth").
        https_only: if true, only HTTPS APIs.
        with_openapi: if true, only entries with OpenAPI schemas (apis.guru).
        source: filter to "public-apis" or "apis.guru" only.

    Returns: list of API records.
    """
    return S.search(
        query,
        auth=auth,
        https_only=https_only,
        has_openapi=with_openapi,
        source=source,
        limit=limit,
    )


@mcp.tool()
def semantic_search_apis(query: str, limit: int = 20) -> list[dict]:
    """Embedding-based semantic search — finds APIs even without literal keyword overlap.

    Use when keyword search misses the mark. Slower than search_apis but better recall.

    Example:
        query="real-time market sentiment data" might match Reddit, Twitter, news APIs
        without any of those literal words appearing.
    """
    conn = connect()
    try:
        results = E.semantic_search(conn, query, limit=limit)
        if not results:
            return []
        ids = [api_id for api_id, _ in results]
        rows = {
            r["id"]: dict(r)
            for r in conn.execute(
                f"SELECT * FROM apis WHERE id IN ({','.join('?' * len(ids))})",
                ids,
            )
        }
        return [
            {**rows[api_id], "score": score}
            for api_id, score in results
            if api_id in rows
        ]
    finally:
        conn.close()


@mcp.tool()
def hybrid_search_apis(query: str, limit: int = 20, candidates: int = 100) -> list[dict]:
    """Hybrid: FTS5 fetches `candidates` rows, embeddings rerank top `limit`.

    Best of both worlds — keyword precision plus semantic ranking quality.
    Use this as the default when running heavy research queries.
    """
    fts_rows = S.search(query, limit=candidates)
    if not fts_rows:
        # Fall back to pure semantic if no keyword hits.
        return semantic_search_apis(query, limit=limit)

    candidate_ids = [r["id"] for r in fts_rows]
    conn = connect()
    try:
        results = E.semantic_search(conn, query, limit=limit, candidate_ids=candidate_ids)
        rows = {r["id"]: r for r in fts_rows}
        return [{**rows[i], "score": score} for i, score in results if i in rows]
    finally:
        conn.close()


@mcp.tool()
def get_api(api_id: int) -> dict | None:
    """Fetch the full record for one API by id."""
    return S.show(api_id)


@mcp.tool()
def list_categories() -> list[dict]:
    """List all 157 categories with their API counts."""
    return [{"category": name, "count": n} for name, n in S.list_categories()]


@mcp.tool()
def apis_by_category(category: str, limit: int = 50) -> list[dict]:
    """List all APIs in one category."""
    return S.by_category(category, limit=limit)


@mcp.tool()
def index_stats() -> dict:
    """Index health: total, by source, with-OpenAPI, no-auth count, categories."""
    return S.stats()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()

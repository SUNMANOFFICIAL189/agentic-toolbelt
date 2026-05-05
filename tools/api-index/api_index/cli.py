"""Command-line front-end for the API index."""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

from . import search as S


def _print_row(row: dict, *, full: bool = False) -> None:
    auth = row.get("auth") or "—"
    https = "https" if row.get("https") == 1 else "http"
    src_tag = "[OAS]" if row.get("openapi_url") else "     "
    line = f"  #{row['id']:<5} {src_tag} {row['name']:<35} {auth:<14} {https}"
    print(line)
    desc = (row.get("description") or "").strip()
    if desc:
        wrapped = textwrap.fill(
            desc, width=92, initial_indent="          ", subsequent_indent="          "
        )
        print(wrapped)
    if full:
        print(f"          category: {row.get('category')}")
        print(f"          link:     {row.get('link')}")
        if row.get("openapi_url"):
            print(f"          openapi:  {row['openapi_url']} ({row.get('openapi_version')})")
        print(f"          source:   {row.get('source')}")


def cmd_search(args: argparse.Namespace) -> int:
    if args.semantic or args.hybrid:
        from .db import connect
        from . import embeddings as E

        conn = connect()
        try:
            if args.hybrid:
                fts_rows = S.search(args.query, limit=args.candidates)
                if not fts_rows:
                    print(f"No FTS matches; falling back to pure semantic.", file=sys.stderr)
                    candidate_ids = None
                else:
                    candidate_ids = [r["id"] for r in fts_rows]
                results = E.semantic_search(
                    conn, args.query, limit=args.limit, candidate_ids=candidate_ids
                )
                fts_lookup = {r["id"]: r for r in fts_rows} if fts_rows else {}
                rows = []
                for api_id, score in results:
                    row = fts_lookup.get(api_id) or S.show(api_id)
                    if row:
                        rows.append({**row, "_score": score})
            else:  # pure semantic
                results = E.semantic_search(conn, args.query, limit=args.limit)
                rows = []
                for api_id, score in results:
                    row = S.show(api_id)
                    if row:
                        rows.append({**row, "_score": score})
        finally:
            conn.close()
        mode = "hybrid" if args.hybrid else "semantic"
    else:
        rows = S.search(
            args.query,
            auth=args.auth,
            https_only=args.https,
            has_openapi=args.with_openapi,
            source=args.source,
            limit=args.limit,
        )
        mode = "fts5"

    if not rows:
        print(f"No matches for {args.query!r}.", file=sys.stderr)
        return 1
    print(f"\n{len(rows)} match(es) for {args.query!r} ({mode}):\n")
    for row in rows:
        _print_row(row)
        if "_score" in row:
            print(f"          score:    {row['_score']:.3f}")
    print()
    return 0


def cmd_category(args: argparse.Namespace) -> int:
    rows = S.by_category(args.name, limit=args.limit)
    if not rows:
        print(f"No APIs in category {args.name!r}.", file=sys.stderr)
        return 1
    print(f"\n{args.name} — {len(rows)} APIs:\n")
    for row in rows:
        _print_row(row)
    print()
    return 0


def cmd_categories(args: argparse.Namespace) -> int:
    cats = S.list_categories()
    print(f"\n{len(cats)} categories:\n")
    for name, n in cats:
        print(f"  {n:>4}  {name}")
    print()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    row = S.show(args.id)
    if not row:
        print(f"No API with id {args.id}.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(row, indent=2))
    else:
        _print_row(row, full=True)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    s = S.stats()
    print()
    print(f"  Total APIs:           {s['total']:>5}")
    for src, n in s["by_source"].items():
        print(f"    {src:<18}  {n:>5}")
    print(f"  With OpenAPI schema:  {s['with_openapi_schema']:>5}")
    print(f"  No-auth required:     {s['no_auth_required']:>5}")
    print(f"  Categories:           {s['categories']:>5}")
    print()
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    from scripts.build_index import main as build_main

    build_main(refresh=True)
    return 0


def cmd_generate_client(args: argparse.Namespace) -> int:
    from scripts.generate_client import generate

    row = S.show(args.id)
    if not row:
        print(f"No API with id {args.id}.", file=sys.stderr)
        return 1
    if not row.get("openapi_url"):
        print(
            f"API {row['name']!r} has no OpenAPI schema (source: {row['source']}).\n"
            "Client generation only works for APIs.guru entries.",
            file=sys.stderr,
        )
        return 1
    out = Path(args.output) if args.output else Path.cwd() / "clients" / f"api-{args.id}"
    generate(row["openapi_url"], out, lang=args.lang)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="api-index",
        description="Searchable index of free public APIs (public-apis + APIs.guru).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", help="Search by keyword (default), semantic, or hybrid.")
    sp.add_argument("query")
    sp.add_argument("--auth", help="Filter by auth value (e.g. No, apiKey, OAuth).")
    sp.add_argument("--https", action="store_true", help="Only HTTPS APIs.")
    sp.add_argument("--with-openapi", action="store_true", help="Only APIs with OpenAPI schemas.")
    sp.add_argument("--source", choices=["public-apis", "apis.guru"])
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument(
        "--semantic", action="store_true",
        help="Pure embedding-based search (best for vague queries).",
    )
    sp.add_argument(
        "--hybrid", action="store_true",
        help="FTS retrieval + embedding rerank (best overall quality).",
    )
    sp.add_argument(
        "--candidates", type=int, default=100,
        help="FTS candidate pool size for --hybrid (default 100).",
    )
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("category", help="List APIs in a category.")
    sp.add_argument("name")
    sp.add_argument("--limit", type=int, default=50)
    sp.set_defaults(func=cmd_category)

    sp = sub.add_parser("categories", help="List all categories with counts.")
    sp.set_defaults(func=cmd_categories)

    sp = sub.add_parser("show", help="Show a single API by id.")
    sp.add_argument("id", type=int)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("stats", help="Index statistics.")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("refresh", help="Re-pull both sources and rebuild index.")
    sp.set_defaults(func=cmd_refresh)

    sp = sub.add_parser(
        "generate-client",
        help="Generate a typed client for an APIs.guru entry.",
    )
    sp.add_argument("id", type=int)
    sp.add_argument("--lang", default="typescript-fetch")
    sp.add_argument("-o", "--output", help="Output directory.")
    sp.set_defaults(func=cmd_generate_client)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

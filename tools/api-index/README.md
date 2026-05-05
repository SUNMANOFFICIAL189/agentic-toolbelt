# api-index

Local searchable index of free public APIs, drawn from two upstream sources:

- **public-apis/public-apis** — ~1,400 free APIs (markdown catalog)
- **APIs.guru** — ~3,000 APIs with machine-readable OpenAPI schemas

Stored in a single SQLite database with FTS5 full-text search. Use it at the
start of any project to discover free data sources before reaching for paid
SaaS or scraping.

## What this gives you

| Capability | How |
|---|---|
| Keyword (FTS5) search | `api-index search "weather"` |
| Semantic search (embeddings) | `api-index search "real-time market sentiment" --semantic` |
| Hybrid search (best quality) | `api-index search "<query>" --hybrid` |
| List APIs by category | `api-index category Finance` |
| Show full record | `api-index show <id>` |
| Auto-generate a typed client | `api-index generate-client <id>` (OpenAPI entries only) |
| Refresh both sources | `api-index refresh` |
| Use from agents | MCP server registered as `api-index` (7 tools) |

## Why two sources

- `public-apis` has wider coverage but is just a markdown list — you still
  hand-write the integration code per API.
- `APIs.guru` has narrower coverage but each entry includes a full OpenAPI
  schema. A code generator turns that schema into a typed client library
  in seconds.

When both sources have the same API, the OpenAPI schema is preferred.

## Install

```bash
cd ~/claude-hq/tools/api-index
python3 scripts/build_index.py         # first-time build (~30s)
python3 scripts/build_embeddings.py    # one-time embed (~60s, downloads 50MB model)
ln -sf "$(pwd)/bin/api-index" ~/.local/bin/api-index    # global CLI
```

Optional dependencies:

- `brew install openapi-generator` — required for `generate-client` subcommand
- `pip install --user mcp fastembed` — required for MCP server + semantic search

Refresh quarterly:

```bash
api-index refresh                       # rebuild index from upstream
python3 scripts/build_embeddings.py     # re-embed any new rows
```

## MCP server

Registered in `~/.claude.json` under `mcpServers.api-index`. Exposes 7 tools
to Claude Code agents:

- `search_apis(query, limit, ...)` — FTS5 keyword search
- `semantic_search_apis(query, limit)` — pure embedding-based
- `hybrid_search_apis(query, limit, candidates)` — FTS retrieval + embedding rerank
- `get_api(api_id)` — full record
- `list_categories()` — all 157 categories with counts
- `apis_by_category(category, limit)` — list within a category
- `index_stats()` — health metrics

Restart Claude Code after registration for the server to be discovered.

## Architecture

```
api-index/
├── api_index/
│   ├── cli.py            — argparse front-end (search/category/show/stats/refresh/generate-client)
│   ├── db.py             — SQLite + FTS5 schema
│   ├── search.py         — FTS5 query helpers + query sanitiser
│   ├── embeddings.py     — fastembed (BAAI/bge-small-en-v1.5, 384 dims, local)
│   └── mcp_server.py     — FastMCP server exposing 7 tools
├── scripts/
│   ├── parse_public_apis.py    — markdown → rows
│   ├── fetch_apis_guru.py      — apis.guru/v2/list.json → rows (curl-based, system certs)
│   ├── build_index.py          — orchestrates ingestion
│   ├── build_embeddings.py     — generates 384-dim vectors for every row
│   └── generate_client.py      — wraps openapi-generator
├── bin/
│   ├── api-index         — CLI entry point (symlink target for ~/.local/bin)
│   └── api-index-mcp     — MCP server stdio launcher
├── cache/                — cloned repos + downloaded JSON (gitignored)
└── data/
    └── apis.db           — SQLite: apis + apis_fts + apis_embeddings (gitignored)
```

## Data model

```sql
CREATE TABLE apis (
  id            INTEGER PRIMARY KEY,
  source        TEXT NOT NULL,        -- 'public-apis' or 'apis.guru'
  name          TEXT NOT NULL,
  description   TEXT,
  category      TEXT,
  auth          TEXT,                 -- 'No' / 'apiKey' / 'OAuth' / 'X-Mashape-Key' / etc.
  https         INTEGER,              -- 1 / 0 / NULL
  cors          TEXT,                 -- 'Yes' / 'No' / 'Unknown'
  link          TEXT,                 -- docs URL or API homepage
  openapi_url   TEXT,                 -- nullable; APIs.guru only
  openapi_version TEXT,
  indexed_at    TEXT NOT NULL
);

CREATE VIRTUAL TABLE apis_fts USING fts5(name, description, category, content='apis');
```

## Future work

- ✅ v2: Local embeddings (fastembed + BAAI/bge-small) for semantic search
- ✅ v2: MCP server wrapping the CLI so agents can query directly
- v3: per-project tag column (`relevant_to:artist-video-tool`) so an agent's project context filters results
- v3: `auth-status` column tracking which APIs you have keys for (resolved from Keychain)
- v3: scheduled refresh cron (currently manual `refresh` command)

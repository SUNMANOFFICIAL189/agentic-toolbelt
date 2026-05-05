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
| Find APIs by keyword | `api-index search "weather"` |
| List APIs by category | `api-index category Finance` |
| Show full record | `api-index show <id>` |
| Auto-generate a typed client | `api-index generate-client <id>` (OpenAPI entries only) |
| Refresh both sources | `api-index refresh` |

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
python3 scripts/build_index.py        # first-time build (~30s)
ln -sf "$(pwd)/bin/api-index" ~/.local/bin/api-index
```

Refresh quarterly:

```bash
api-index refresh
```

## Architecture

```
api-index/
├── api_index/
│   ├── cli.py            — argparse front-end
│   ├── db.py             — SQLite + FTS5 schema
│   └── search.py         — query helpers
├── scripts/
│   ├── parse_public_apis.py    — markdown → rows
│   ├── fetch_apis_guru.py      — apis.guru/v2/list.json → rows
│   ├── build_index.py          — orchestrates ingestion
│   └── generate_client.py      — wraps openapi-generator
├── bin/
│   └── api-index         — CLI entry point
├── cache/                — cloned repos + downloaded JSON (gitignored)
└── data/
    └── apis.db           — SQLite database (gitignored)
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

- v2: Gemini Flash embeddings for semantic search ("crypto mempool data" → matches APIs without literal keyword overlap)
- v2: MCP server wrapping the CLI so agents can query directly
- v2: per-project tag column (`relevant_to:artist-video-tool`) so an agent's project context filters results
- v2: `auth-status` column tracking which APIs you have keys for (resolved from Keychain)

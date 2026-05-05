"""Orchestrate ingestion: clone public-apis (if missing), fetch APIs.guru,
parse both, write to SQLite.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api_index.db import connect, reset  # noqa: E402
from scripts.fetch_apis_guru import fetch_directory, parse_directory  # noqa: E402
from scripts.parse_public_apis import parse_readme  # noqa: E402

CACHE_DIR = ROOT / "cache"
PUBLIC_APIS_DIR = CACHE_DIR / "public-apis"
APIS_GURU_CACHE = CACHE_DIR / "apis-guru.json"
PUBLIC_APIS_REPO = "https://github.com/public-apis/public-apis.git"


def ensure_public_apis(refresh: bool = False) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    if PUBLIC_APIS_DIR.exists():
        if refresh:
            print("[public-apis] refreshing via git pull")
            subprocess.run(
                ["git", "-C", str(PUBLIC_APIS_DIR), "pull", "--ff-only"],
                check=True,
            )
        else:
            print(f"[public-apis] cached at {PUBLIC_APIS_DIR}")
    else:
        print(f"[public-apis] cloning {PUBLIC_APIS_REPO}")
        subprocess.run(
            ["git", "clone", "--depth", "1", PUBLIC_APIS_REPO, str(PUBLIC_APIS_DIR)],
            check=True,
        )
    readme = PUBLIC_APIS_DIR / "README.md"
    if not readme.exists():
        raise FileNotFoundError(f"README.md missing in {PUBLIC_APIS_DIR}")
    return readme


def ensure_apis_guru(refresh: bool = False) -> Path:
    if refresh and APIS_GURU_CACHE.exists():
        APIS_GURU_CACHE.unlink()
    if not APIS_GURU_CACHE.exists():
        print(f"[apis.guru] downloading list.json")
        fetch_directory(cache_path=APIS_GURU_CACHE)
    else:
        print(f"[apis.guru] cached at {APIS_GURU_CACHE}")
    return APIS_GURU_CACHE


def main(refresh: bool = False) -> None:
    reset()  # full rebuild — fast and avoids stale rows
    conn = connect()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    # public-apis
    readme = ensure_public_apis(refresh=refresh)
    pa_count = 0
    for row in parse_readme(readme):
        try:
            conn.execute(
                """INSERT OR IGNORE INTO apis
                   (source, name, description, category, auth, https, cors, link,
                    openapi_url, openapi_version, indexed_at)
                   VALUES (:source, :name, :description, :category, :auth, :https, :cors,
                           :link, :openapi_url, :openapi_version, :indexed_at)""",
                {**row, "indexed_at": now},
            )
            pa_count += 1
        except Exception as e:
            print(f"  warn: skipped {row.get('name')!r}: {e}", file=sys.stderr)
    conn.commit()
    print(f"[public-apis] inserted {pa_count} rows")

    # apis.guru
    cache = ensure_apis_guru(refresh=refresh)
    import json as _json
    directory = _json.loads(cache.read_text(encoding="utf-8"))
    ag_count = 0
    for row in parse_directory(directory):
        try:
            conn.execute(
                """INSERT OR IGNORE INTO apis
                   (source, name, description, category, auth, https, cors, link,
                    openapi_url, openapi_version, indexed_at)
                   VALUES (:source, :name, :description, :category, :auth, :https, :cors,
                           :link, :openapi_url, :openapi_version, :indexed_at)""",
                {**row, "indexed_at": now},
            )
            ag_count += 1
        except Exception as e:
            print(f"  warn: skipped {row.get('name')!r}: {e}", file=sys.stderr)
    conn.commit()
    print(f"[apis.guru] inserted {ag_count} rows")

    total = conn.execute("SELECT COUNT(*) FROM apis").fetchone()[0]
    print(f"\nIndex built: {total} APIs total → {ROOT / 'data' / 'apis.db'}")
    conn.close()


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    main(refresh=refresh)

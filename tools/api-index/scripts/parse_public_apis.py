"""Parse public-apis/public-apis README.md into structured rows.

The README uses a category-grouped markdown table format:

    ### Animals
    API | Description | Auth | HTTPS | CORS
    ----|-------------|------|-------|-----
    [Cat Facts](https://catfact.ninja/) | Daily cat facts | No | Yes | No
    ...

We track the current category from `###` (or `##`) headings and parse
table rows into dicts.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

# Match: [Name](https://link/) - or [Name](https://link/) | etc.
NAME_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# A markdown table row has at least 4 pipe-separated cells (5 columns minimum).
MIN_CELLS = 5
# Category headings we care about (the README also has back-to-index TOC links;
# real content categories are h3, top-level intro/license/contributing are h2).
CAT_RE = re.compile(r"^###\s+(.+?)\s*$")


def _split_row(line: str) -> list[str] | None:
    """Split a `| a | b | c |` line into cells. Returns None if not a row."""
    s = line.strip()
    if not s.startswith("|") or not s.endswith("|"):
        # Some rows in this README use no leading/trailing pipe — accept either.
        if "|" not in s:
            return None
    # Strip leading/trailing pipes then split.
    s = s.strip("|")
    cells = [c.strip() for c in s.split("|")]
    if len(cells) < MIN_CELLS:
        return None
    return cells


def _is_separator(cells: list[str]) -> bool:
    """Detect the `---|---|---` separator row."""
    return all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def _parse_https(value: str) -> int | None:
    v = value.strip().lower()
    if v in ("yes", "true", "1"):
        return 1
    if v in ("no", "false", "0"):
        return 0
    return None


def parse_readme(readme_path: Path) -> Iterator[dict]:
    """Yield one dict per API row in the README."""
    current_category: str | None = None
    in_table = False
    seen_header = False

    for raw in readme_path.read_text(encoding="utf-8").splitlines():
        # Skip TOC entries (they appear early in the doc and look like list items).
        line = raw.rstrip()

        m = CAT_RE.match(line)
        if m:
            current_category = m.group(1).strip()
            in_table = False
            seen_header = False
            continue

        cells = _split_row(line)
        if cells is None:
            in_table = False
            seen_header = False
            continue

        if _is_separator(cells):
            in_table = True
            continue

        # First non-separator row in a table is the header — skip.
        if not seen_header and cells[0].lower().startswith(("api", "name")):
            seen_header = True
            continue

        if not in_table or current_category is None:
            continue

        # cells[0] is the [Name](link), cells[1] desc, cells[2] auth, cells[3] https, cells[4] cors
        name_match = NAME_LINK_RE.search(cells[0])
        if not name_match:
            # Skip malformed rows.
            continue

        name = name_match.group(1).strip()
        link = name_match.group(2).strip()
        description = cells[1] if len(cells) > 1 else ""
        auth = cells[2].strip() if len(cells) > 2 else ""
        https = _parse_https(cells[3]) if len(cells) > 3 else None
        cors = cells[4].strip() if len(cells) > 4 else ""

        # Normalise auth values — README uses backticks around values.
        auth = auth.strip("`").strip()
        cors = cors.strip("`").strip()

        yield {
            "source": "public-apis",
            "name": name,
            "description": description,
            "category": current_category,
            "auth": auth,
            "https": https,
            "cors": cors,
            "link": link,
            "openapi_url": None,
            "openapi_version": None,
        }


if __name__ == "__main__":
    import json
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cache/public-apis/README.md")
    rows = list(parse_readme(path))
    print(f"Parsed {len(rows)} APIs from {path}", file=sys.stderr)
    for row in rows[:3]:
        print(json.dumps(row, indent=2))

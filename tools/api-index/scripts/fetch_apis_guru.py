"""Fetch the APIs.guru directory and yield structured rows.

APIs.guru exposes the entire directory at:
    https://api.apis.guru/v2/list.json

The response is a dict keyed by provider/service identifier:

    {
      "stripe.com": {
        "added": "...",
        "preferred": "2022-11-15",
        "versions": {
          "2022-11-15": {
            "info": {"title": "Stripe API", "description": "...", "x-providerName": "stripe.com", ...},
            "swaggerUrl": "https://api.apis.guru/v2/specs/.../openapi.json",
            "openapiVer": "3.0.0",
            ...
          }
        }
      }
    }

We take the *preferred* version of each entry as the canonical row.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterator

LIST_URL = "https://api.apis.guru/v2/list.json"
USER_AGENT = "claude-hq/api-index/0.1 (+local-research-tool)"


def fetch_directory(cache_path: Path | None = None) -> dict:
    """Download the APIs.guru directory via curl (uses macOS system certs).

    Caches the JSON to disk so subsequent runs skip the network.
    """
    if cache_path and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    result = subprocess.run(
        [
            "curl", "-sSfL",
            "--max-time", "60",
            "-A", USER_AGENT,
            LIST_URL,
        ],
        capture_output=True,
        check=True,
    )
    data = json.loads(result.stdout)

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data), encoding="utf-8")

    return data


def parse_directory(directory: dict) -> Iterator[dict]:
    """Yield one dict per API (preferred version of each entry)."""
    for key, entry in directory.items():
        preferred = entry.get("preferred")
        versions = entry.get("versions", {})
        if not preferred or preferred not in versions:
            # Fall back to first version if 'preferred' is missing.
            if not versions:
                continue
            preferred = next(iter(versions))

        version_info = versions[preferred]
        info = version_info.get("info", {}) or {}

        title = info.get("title") or key
        description = info.get("description") or ""
        # Take first paragraph for description; full text can be huge.
        description = description.split("\n\n")[0].strip()
        if len(description) > 500:
            description = description[:497] + "..."

        category = (
            (info.get("x-apisguru-categories") or [None])[0]
            or info.get("x-providerName")
            or "Uncategorised"
        )
        link = info.get("contact", {}).get("url") or version_info.get("link") or ""

        # OpenAPI spec URL — prefer JSON (swaggerUrl) over YAML.
        openapi_url = version_info.get("swaggerUrl") or version_info.get("swaggerYamlUrl")
        openapi_version = version_info.get("openapiVer") or "unknown"

        # Auth: not always present in the directory metadata; leave blank if unknown.
        # Most APIs.guru entries require some form of auth (apiKey / OAuth);
        # the schema file itself encodes the exact securityScheme.
        security_schemes = (
            info.get("x-securityScheme") or version_info.get("x-securityScheme") or ""
        )
        if isinstance(security_schemes, dict):
            security_schemes = ",".join(security_schemes.keys())
        auth = security_schemes or ""

        yield {
            "source": "apis.guru",
            "name": title,
            "description": description,
            "category": str(category),
            "auth": auth,
            "https": 1,  # APIs.guru only catalogues HTTPS endpoints
            "cors": "",
            "link": link,
            "openapi_url": openapi_url,
            "openapi_version": str(openapi_version),
        }


if __name__ == "__main__":
    import sys

    cache = Path("cache/apis-guru.json")
    directory = fetch_directory(cache_path=cache)
    rows = list(parse_directory(directory))
    print(f"Fetched {len(rows)} APIs from apis.guru", file=sys.stderr)
    for row in rows[:3]:
        print(json.dumps(row, indent=2))

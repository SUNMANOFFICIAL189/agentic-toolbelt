#!/usr/bin/env python3
"""
Unified web-page fetcher for HQ.

Strategy:
  - Default ("quick"): try Jina Reader (https://r.jina.ai/<URL>). Free,
    hosted, fast, no daemon. ~80% quality, fails gracefully on JS-heavy
    SPAs and anti-bot pages.
  - Escalation ("deep"): use Crawl4AI locally via its venv. Same source
    code as the Docker image, but runs as a Python process — no Docker
    daemon required. Better quality on JS, better at extracting clean
    markdown from messy markup.
  - "auto": Jina first; if the result looks degraded (too short or
    matches known anti-bot signatures), retry with Crawl4AI.

Output: JSON to stdout
  {
    "url": "...",
    "status": "ok" | "error",
    "source": "jina" | "crawl4ai",
    "content": "<markdown>",
    "duration_ms": <int>,
    "error": "<msg if status=error>"
  }

Usage:
  fetch-page.py <url> [--mode quick|deep|auto] [--timeout 30]

Notes:
  - Jina free tier: 20 req/min without a key, 500 req/min with a free key.
    A key in env JINA_API_KEY upgrades the limit transparently.
  - Crawl4AI requires the venv at ~/claude-hq/.venv-crawl4ai. The script
    must be invoked via the venv's python (the bash wrapper handles this).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import os
import re
import sys
import time
from typing import Any

import httpx

# ----------------------------------------------------------------------------
# Heuristics for "degraded content" (when to escalate Jina → Crawl4AI)
# ----------------------------------------------------------------------------

DEGRADED_PATTERNS = [
    r"just a moment",                 # Cloudflare challenge page
    r"please verify (you are )?human", # generic anti-bot
    r"access denied",
    r"403 forbidden",
    r"cf-chl-bypass",
    r"checking your browser",
    r"enable javascript",
    r"this site (requires|uses) javascript",
    r"<noscript>.*?</noscript>",       # body falls back to a noscript shell
]
DEGRADED_RE = re.compile("|".join(f"({p})" for p in DEGRADED_PATTERNS), re.IGNORECASE | re.DOTALL)
MIN_CONTENT_CHARS = 100  # below this, treat as degraded regardless of patterns


def looks_degraded(content: str) -> tuple[bool, str]:
    """Return (degraded?, reason). Reason is empty if not degraded."""
    if not content or not content.strip():
        return True, "empty content"
    stripped = content.strip()
    if len(stripped) < MIN_CONTENT_CHARS:
        return True, f"too short ({len(stripped)} chars)"
    m = DEGRADED_RE.search(stripped[:5000])  # only scan top of doc
    if m:
        matched = next((g for g in m.groups() if g), "anti-bot pattern")
        return True, f"anti-bot signature: {matched[:50]!r}"
    return False, ""


# ----------------------------------------------------------------------------
# Jina Reader
# ----------------------------------------------------------------------------


async def fetch_jina(url: str, timeout: float = 30.0) -> dict[str, Any]:
    """Fetch via Jina Reader. Returns standard envelope."""
    start = time.monotonic()
    headers = {"Accept": "text/markdown"}
    if os.environ.get("JINA_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['JINA_API_KEY']}"
    jina_url = f"https://r.jina.ai/{url}"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(jina_url, headers=headers)
        duration_ms = int((time.monotonic() - start) * 1000)
        if r.status_code != 200:
            return {
                "status": "error",
                "source": "jina",
                "duration_ms": duration_ms,
                "error": f"HTTP {r.status_code}: {r.text[:200]}",
                "content": "",
            }
        return {
            "status": "ok",
            "source": "jina",
            "duration_ms": duration_ms,
            "content": r.text,
        }
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "error",
            "source": "jina",
            "duration_ms": duration_ms,
            "error": f"{type(e).__name__}: {e}",
            "content": "",
        }


# ----------------------------------------------------------------------------
# Crawl4AI (local, via venv)
# ----------------------------------------------------------------------------


async def fetch_crawl4ai(url: str, timeout: float = 60.0) -> dict[str, Any]:
    """Fetch via Crawl4AI. Returns standard envelope."""
    start = time.monotonic()
    try:
        # Lazy import — only imported when the deep path is actually used.
        # Crawl4AI deps are heavy (~95 packages). Quick path stays light.
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except ImportError as e:
        return {
            "status": "error",
            "source": "crawl4ai",
            "duration_ms": 0,
            "error": (
                "Crawl4AI not importable. Make sure this script runs via the "
                f"venv at ~/claude-hq/.venv-crawl4ai/bin/python. Underlying: {e}"
            ),
            "content": "",
        }
    # Crawl4AI ignores verbose=False for its progress/init lines (Rich + its
    # own logger). Capture stdout during the crawl so it can't corrupt our
    # JSON envelope; forward to stderr in finally for transparency.
    crawler_stdout = io.StringIO()
    try:
        try:
            with contextlib.redirect_stdout(crawler_stdout):
                async with AsyncWebCrawler(verbose=False) as crawler:
                    result = await asyncio.wait_for(crawler.arun(url=url), timeout=timeout)
        finally:
            if crawler_stdout.getvalue():
                sys.stderr.write(crawler_stdout.getvalue())
        duration_ms = int((time.monotonic() - start) * 1000)
        # Crawl4AI returns various forms; normalise to markdown when available
        markdown = ""
        if hasattr(result, "markdown") and result.markdown:
            markdown = (
                result.markdown.fit_markdown
                if hasattr(result.markdown, "fit_markdown") and result.markdown.fit_markdown
                else (result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown))
            )
        elif hasattr(result, "html"):
            markdown = result.html or ""
        if not getattr(result, "success", True):
            return {
                "status": "error",
                "source": "crawl4ai",
                "duration_ms": duration_ms,
                "error": getattr(result, "error_message", "crawler reported failure"),
                "content": markdown,
            }
        return {
            "status": "ok",
            "source": "crawl4ai",
            "duration_ms": duration_ms,
            "content": markdown,
        }
    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "error",
            "source": "crawl4ai",
            "duration_ms": duration_ms,
            "error": f"timeout after {timeout}s",
            "content": "",
        }
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "error",
            "source": "crawl4ai",
            "duration_ms": duration_ms,
            "error": f"{type(e).__name__}: {e}",
            "content": "",
        }


# ----------------------------------------------------------------------------
# Mode dispatch
# ----------------------------------------------------------------------------


async def fetch(url: str, mode: str, timeout: float) -> dict[str, Any]:
    if mode == "quick":
        result = await fetch_jina(url, timeout)
        result["url"] = url
        return result

    if mode == "deep":
        result = await fetch_crawl4ai(url, timeout)
        result["url"] = url
        return result

    if mode == "auto":
        first = await fetch_jina(url, timeout)
        first["url"] = url
        if first["status"] == "ok":
            degraded, reason = looks_degraded(first["content"])
            if not degraded:
                return first
            # Escalate
            second = await fetch_crawl4ai(url, timeout * 2)
            second["url"] = url
            second["jina_attempt"] = {
                "duration_ms": first["duration_ms"],
                "degraded_reason": reason,
            }
            return second
        # Jina failed — try Crawl4AI
        second = await fetch_crawl4ai(url, timeout * 2)
        second["url"] = url
        second["jina_attempt"] = {
            "duration_ms": first["duration_ms"],
            "error": first.get("error", "unknown"),
        }
        return second

    raise ValueError(f"Unknown mode: {mode}")


# ----------------------------------------------------------------------------
# Entry
# ----------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a web page as clean markdown. Jina-first by default; --deep forces Crawl4AI."
    )
    parser.add_argument("url", help="URL to fetch (with or without protocol).")
    parser.add_argument(
        "--mode",
        choices=["quick", "deep", "auto"],
        default="quick",
        help="quick=Jina only (default). deep=Crawl4AI only. auto=Jina then escalate to Crawl4AI on degraded result.",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-attempt timeout in seconds.")
    args = parser.parse_args()

    # Normalise URL — Jina Reader accepts either form, but Crawl4AI wants protocol
    url = args.url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    result = asyncio.run(fetch(url, args.mode, args.timeout))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

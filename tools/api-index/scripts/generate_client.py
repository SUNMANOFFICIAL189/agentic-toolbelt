"""Generate a typed client library for an APIs.guru entry.

Wraps openapi-generator-cli (must be installed separately, e.g. via
`brew install openapi-generator` or `npm i -g @openapitools/openapi-generator-cli`).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_LANG = "typescript-fetch"


def find_generator() -> str:
    for candidate in ("openapi-generator", "openapi-generator-cli"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError(
        "openapi-generator not found. Install via:\n"
        "  brew install openapi-generator\n"
        "  # or\n"
        "  npm i -g @openapitools/openapi-generator-cli"
    )


def generate(spec_url: str, output_dir: Path, lang: str = DEFAULT_LANG) -> None:
    gen = find_generator()
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [gen, "generate", "-i", spec_url, "-g", lang, "-o", str(output_dir)],
        check=True,
    )
    print(f"\nClient generated at {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "usage: generate_client.py <spec_url> <output_dir> [lang]\n"
            f"  default lang: {DEFAULT_LANG}",
            file=sys.stderr,
        )
        sys.exit(2)
    spec, out = sys.argv[1], Path(sys.argv[2])
    lang = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_LANG
    generate(spec, out, lang)

"""
Shared Finding type for PATS-Copy architectural watchdog runtime rules.

Each runtime rule emits one Finding per detected issue, as a JSON line on stdout.
The orchestrator collects them and decides whether to alert (severity gate +
plain-English wrapper via watchdog/telegram.py PlainAlert).

Convention:
    rule_id            stable identifier (e.g., 'pats-runtime-stale-open-rows')
    severity           info | warn | critical
    what_happened      one short plain-English sentence (Lesson 16)
    what_to_do         one concrete action verb-led instruction
    technical_detail   dict, logged to audit.log only — never reaches phone
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    what_happened: str
    what_to_do: str
    technical_detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warn", "critical"}:
            raise ValueError(f"severity must be info|warn|critical, got {self.severity!r}")
        if not self.what_happened.strip():
            raise ValueError("what_happened cannot be empty")
        if not self.what_to_do.strip():
            raise ValueError("what_to_do cannot be empty")

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), default=str, ensure_ascii=False)


def emit(finding: Finding) -> None:
    """Print one finding as a JSON line to stdout."""
    print(finding.to_json_line())


__all__ = ["Finding", "emit"]

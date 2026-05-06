#!/usr/bin/env python3
"""
HQ Watchdog — scoring engine.

Reads local data (session .tmp files, git log on claude-hq, LESSONS.md
velocity, Trust Gate log), computes metrics defined in metrics.yaml,
compares them against rolling baselines, and emits PlainAlerts through
telegram.py when something has gotten worse.

Zero API costs. No LLM calls. Stdlib only.

Usage:
    python3 watchdog.py              # single scoring pass (called by hooks)
    python3 watchdog.py --digest     # assemble the daily digest
    python3 watchdog.py --ingest     # parse session files + commits into DB
    python3 watchdog.py --stats      # print raw stats (for debugging)
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Local import — same directory
sys.path.insert(0, str(Path(__file__).parent))
from telegram import PlainAlert, send as send_telegram  # noqa: E402

# -----------------------------------------------------------------------------
# Paths and constants
# -----------------------------------------------------------------------------

WATCHDOG_DIR = Path(__file__).parent.resolve()
CLAUDE_HQ = WATCHDOG_DIR.parent
SESSIONS_DIR = Path.home() / ".claude" / "sessions"
LESSONS_FILE = CLAUDE_HQ / "commander" / "LESSONS.md"
TRUST_GATE_LOG = CLAUDE_HQ / "scripts" / ".trust-gate.log"
METRICS_YAML = WATCHDOG_DIR / "metrics.yaml"
HISTORY_DB = WATCHDOG_DIR / "history.db"
LEARNINGS_MD = WATCHDOG_DIR / "LEARNINGS.md"
BASELINE_JSON = WATCHDOG_DIR / "baseline.json"

# Correction phrase patterns — spoken by the user, captured in session summaries
CORRECTION_PATTERNS = [
    re.compile(r"\bno\b[,.\s]{0,20}(don't|dont|stop|wrong|not)\b", re.IGNORECASE),
    re.compile(r"\bactually\b", re.IGNORECASE),
    re.compile(r"\bthat'?s wrong\b", re.IGNORECASE),
    re.compile(r"\bstop\s+(doing|that)\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\s+(do|run|use|touch)\b", re.IGNORECASE),
    re.compile(r"\bundo\b", re.IGNORECASE),
    re.compile(r"\brevert\b", re.IGNORECASE),
]


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_file TEXT UNIQUE NOT NULL,
    session_date TEXT NOT NULL,
    project TEXT,
    branch TEXT,
    started_at TEXT,
    last_updated_at TEXT,
    user_messages INTEGER DEFAULT 0,
    files_modified INTEGER DEFAULT 0,
    tools_used INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,
    duration_minutes INTEGER DEFAULT 0,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commits (
    sha TEXT PRIMARY KEY,
    commit_date TEXT NOT NULL,
    message TEXT,
    files_changed INTEGER DEFAULT 0,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    is_revert INTEGER DEFAULT 0,
    touches_lessons INTEGER DEFAULT 0,
    lessons_rules_added INTEGER DEFAULT 0,
    captured_at TEXT NOT NULL,
    project TEXT NOT NULL DEFAULT 'claude-hq'
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    computed_at TEXT NOT NULL,
    metric_id TEXT NOT NULL,
    current_value REAL,
    baseline_value REAL,
    percent_delta REAL,
    severity TEXT,
    alert_sent INTEGER DEFAULT 0,
    suppressed INTEGER DEFAULT 0,
    suppression_reason TEXT,
    project TEXT NOT NULL DEFAULT 'claude-hq'
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_commits_date ON commits(commit_date);
CREATE INDEX IF NOT EXISTS idx_scores_computed ON scores(computed_at);
"""

# Default project tag for legacy rows + fallback when no explicit project given.
# Treated as just-another-project, NOT a code-level special case (B-readiness #5).
DEFAULT_PROJECT = "claude-hq"

PROJECTS_JSON = WATCHDOG_DIR / "projects.json"


@dataclass
class ProjectConfig:
    """One watched project: repo to ingest commits from, optional lessons file.

    name: canonical key. MUST match the basename of the repo directory because
      Claude Code's session-file capture uses basename to fill the
      'Project: X' header. Cross-system identity hinges on this.
    display_name: friendly label used in alerts and dashboards. Falls back to
      name when not set. Lets us tag '[PATS-Copy]' on alerts even though the
      canonical key is 'POLYMARKET_TRADING_3.0'.
    """
    name: str
    repo_path: Path
    lessons_path: Optional[Path]  # absolute, resolved against repo_path
    display_name: Optional[str] = None

    @property
    def label(self) -> str:
        return self.display_name or self.name

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProjectConfig":
        repo = Path(d["repo_path"]).expanduser()
        lessons_rel = d.get("lessons_path")
        lessons = (repo / lessons_rel) if lessons_rel else None
        return cls(
            name=d["name"],
            repo_path=repo,
            lessons_path=lessons,
            display_name=d.get("display_name"),
        )


def load_projects() -> list[ProjectConfig]:
    """Load projects.json. On missing/invalid, fall back to a single claude-hq entry.

    Externalized config (B-readiness #2) — splitting per-project later means
    splitting this file, not changing code paths.
    """
    fallback = [ProjectConfig(
        name=DEFAULT_PROJECT,
        repo_path=CLAUDE_HQ,
        lessons_path=LESSONS_FILE,
    )]
    if not PROJECTS_JSON.is_file():
        return fallback
    try:
        data = json.loads(PROJECTS_JSON.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback
    entries = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return fallback
    out: list[ProjectConfig] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("repo_path"):
            continue
        try:
            out.append(ProjectConfig.from_dict(entry))
        except (KeyError, TypeError):
            continue
    return out or fallback


def get_project(name: str) -> Optional[ProjectConfig]:
    """Look up a project by name. Returns None if not registered."""
    for p in load_projects():
        if p.name == name:
            return p
    return None


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema migrations for existing DBs created before project tagging.

    SQLite's CREATE TABLE IF NOT EXISTS won't add new columns to existing tables,
    so we detect missing columns via PRAGMA and add them with a sane default.
    """
    def has_column(table: str, col: str) -> bool:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r["name"] == col for r in rows)

    # commits.project — added 2026-04-27 (Option C migration)
    if not has_column("commits", "project"):
        conn.execute(
            f"ALTER TABLE commits ADD COLUMN project TEXT NOT NULL DEFAULT '{DEFAULT_PROJECT}'"
        )
        # Existing rows already get DEFAULT_PROJECT via the DEFAULT clause —
        # explicit UPDATE is belt-and-braces in case of any NULLs from older
        # SQLite versions that didn't apply DEFAULT during ALTER.
        conn.execute(
            "UPDATE commits SET project = ? WHERE project IS NULL OR project = ''",
            (DEFAULT_PROJECT,),
        )

    # scores.project — added 2026-04-27 (Option C migration)
    if not has_column("scores", "project"):
        conn.execute(
            f"ALTER TABLE scores ADD COLUMN project TEXT NOT NULL DEFAULT '{DEFAULT_PROJECT}'"
        )
        conn.execute(
            "UPDATE scores SET project = ? WHERE project IS NULL OR project = ''",
            (DEFAULT_PROJECT,),
        )

    # Project indices created post-migration so they only attempt to reference
    # columns that definitely exist (whether from CREATE TABLE on a fresh DB
    # or the ALTER TABLE migrations above).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_commits_project ON commits(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_project ON scores(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project)")

    conn.commit()


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate_schema(conn)
    return conn


# -----------------------------------------------------------------------------
# Session parsing
# -----------------------------------------------------------------------------

@dataclass
class SessionSummary:
    session_file: str
    session_date: str
    project: str
    branch: str
    started_at: str
    last_updated_at: str
    user_messages: int
    files_modified: int
    tools_used: int
    correction_count: int
    duration_minutes: int


def parse_session_file(path: Path) -> Optional[SessionSummary]:
    """Parse a session .tmp file. Returns None if unparseable."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    def find(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    session_date = find(r"\*\*Date:\*\*\s*(\S+)")
    if not session_date:
        return None

    started = find(r"\*\*Started:\*\*\s*(\S+)")
    last_updated = find(r"\*\*Last Updated:\*\*\s*(\S+)")
    project = find(r"\*\*Project:\*\*\s*(.+)$")
    branch = find(r"\*\*Branch:\*\*\s*(\S+)")

    # Tasks section contains the user messages (one per dash-prefixed line)
    user_msgs = _extract_section_items(text, "Tasks")
    files = _extract_section_items(text, "Files Modified")
    tools = _extract_section_items(text, "Tools Used")

    # Correction count — scan user_msgs for correction patterns
    correction_count = 0
    for msg in user_msgs:
        for pat in CORRECTION_PATTERNS:
            if pat.search(msg):
                correction_count += 1
                break

    duration_minutes = _compute_duration(session_date, started, last_updated)

    return SessionSummary(
        session_file=str(path),
        session_date=session_date,
        project=project,
        branch=branch,
        started_at=started,
        last_updated_at=last_updated,
        user_messages=len(user_msgs),
        files_modified=len(files),
        tools_used=len(tools) if tools else _count_tools_stats(text),
        correction_count=correction_count,
        duration_minutes=duration_minutes,
    )


def _extract_section_items(text: str, section: str) -> list[str]:
    """Extract bullet items under a ### heading."""
    pat = re.compile(
        rf"###\s+{re.escape(section)}\s*\n(.*?)(?=\n###|\n##|\n<!--|$)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pat.search(text)
    if not m:
        return []
    return [
        line.lstrip("-* \t").strip()
        for line in m.group(1).splitlines()
        if line.lstrip().startswith("-") or line.lstrip().startswith("*")
    ]


def _count_tools_stats(text: str) -> int:
    """Fallback: count 'Total user messages' or similar from Stats section."""
    m = re.search(r"Total user messages:\s*(\d+)", text, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _compute_duration(session_date: str, started: str, last_updated: str) -> int:
    """Rough session duration in minutes. 0 if unparseable."""
    if not started or not last_updated:
        return 0
    try:
        start = datetime.strptime(f"{session_date} {started}", "%Y-%m-%d %H:%M")
        end = datetime.strptime(f"{session_date} {last_updated}", "%Y-%m-%d %H:%M")
        delta = (end - start).total_seconds() / 60.0
        return max(0, int(delta))
    except ValueError:
        return 0


def ingest_sessions() -> int:
    """Walk ~/.claude/sessions/ and upsert into DB. Returns count of new rows."""
    if not SESSIONS_DIR.is_dir():
        return 0

    conn = db_connect()
    new_count = 0
    now = datetime.now().isoformat(timespec="seconds")
    for path in sorted(SESSIONS_DIR.glob("*.tmp")):
        summary = parse_session_file(path)
        if not summary:
            continue
        existing = conn.execute(
            "SELECT id FROM sessions WHERE session_file = ?", (summary.session_file,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE sessions SET
                    last_updated_at=?, user_messages=?, files_modified=?,
                    tools_used=?, correction_count=?, duration_minutes=?,
                    captured_at=?
                   WHERE id=?""",
                (
                    summary.last_updated_at, summary.user_messages, summary.files_modified,
                    summary.tools_used, summary.correction_count, summary.duration_minutes,
                    now, existing["id"],
                ),
            )
        else:
            conn.execute(
                """INSERT INTO sessions (session_file, session_date, project, branch,
                   started_at, last_updated_at, user_messages, files_modified,
                   tools_used, correction_count, duration_minutes, captured_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    summary.session_file, summary.session_date, summary.project, summary.branch,
                    summary.started_at, summary.last_updated_at, summary.user_messages,
                    summary.files_modified, summary.tools_used, summary.correction_count,
                    summary.duration_minutes, now,
                ),
            )
            new_count += 1
    conn.commit()
    conn.close()
    return new_count


# -----------------------------------------------------------------------------
# Git ingestion
# -----------------------------------------------------------------------------

def ingest_commits(days: int = 90) -> int:
    """Pull recent commits from every registered project into DB.

    Loops over all projects in projects.json and calls _ingest_one_repo per
    project. Returns total count of upserted rows across all projects.

    Project-aware (Option C, Decision Log 2026-04-27): each commit is tagged
    with its source project so cross-project metrics never conflate.
    """
    now = datetime.now().isoformat(timespec="seconds")
    conn = db_connect()
    total = 0
    try:
        for project in load_projects():
            total += _ingest_one_repo(conn, project, days, now)
        conn.commit()
    finally:
        conn.close()
    return total


def _ingest_one_repo(
    conn: sqlite3.Connection,
    project: ProjectConfig,
    days: int,
    now: str,
) -> int:
    """Pull commits from one repo, tagging each with project.name."""
    if not project.repo_path.is_dir() or not (project.repo_path / ".git").exists():
        return 0
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        out = subprocess.run(
            ["git", "-C", str(project.repo_path), "log",
             f"--since={since}",
             "--pretty=format:%H%x1f%cI%x1f%s",
             "--numstat", "--no-merges"],
            capture_output=True, text=True, timeout=30, check=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return 0

    upserted = 0
    current: Optional[dict[str, Any]] = None
    lessons_rel = (
        str(project.lessons_path.relative_to(project.repo_path))
        if project.lessons_path else None
    )

    def flush(commit: dict[str, Any]) -> None:
        nonlocal upserted
        commit["project"] = project.name
        _upsert_commit(conn, commit, now)
        upserted += 1

    for line in out.stdout.splitlines():
        if "\x1f" in line:
            if current:
                flush(current)
            parts = line.split("\x1f")
            if len(parts) != 3:
                continue
            sha, date, message = parts
            current = {
                "sha": sha, "date": date, "message": message,
                "files_changed": 0, "insertions": 0, "deletions": 0,
                "touches_lessons": 0, "lessons_rules_added": 0,
            }
        elif line.strip() and current:
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            ins, dele, path = parts
            try:
                current["insertions"] += int(ins) if ins.isdigit() else 0
                current["deletions"] += int(dele) if dele.isdigit() else 0
            except ValueError:
                pass
            current["files_changed"] += 1
            # Lessons-touch check is project-scoped: only the project's own
            # lessons_path counts. Avoids cross-project false positives where
            # an unrelated repo happens to have a "LESSONS.md" in its tree.
            if lessons_rel and path == lessons_rel:
                current["touches_lessons"] = 1
                current["lessons_rules_added"] = _count_new_rules_in_commit(
                    project.repo_path, current["sha"], lessons_rel
                )

    if current:
        flush(current)
    return upserted


def _upsert_commit(conn: sqlite3.Connection, c: dict[str, Any], now: str) -> None:
    is_revert = 1 if c["message"].lower().startswith(("revert ", "revert:")) else 0
    project = c.get("project", DEFAULT_PROJECT)
    conn.execute(
        """INSERT OR REPLACE INTO commits
           (sha, commit_date, message, files_changed, insertions, deletions,
            is_revert, touches_lessons, lessons_rules_added, captured_at, project)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            c["sha"], c["date"], c["message"],
            c["files_changed"], c["insertions"], c["deletions"],
            is_revert, c["touches_lessons"], c["lessons_rules_added"], now,
            project,
        ),
    )


def _count_new_rules_in_commit(repo_path: Path, sha: str, lessons_rel: str) -> int:
    """Count how many new rule headings landed in this project's lessons file
    for the given commit. repo_path + lessons_rel are project-scoped so this
    works for any registered project, not just claude-hq."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "show", f"{sha}", "--", lessons_rel],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except subprocess.SubprocessError:
        return 0
    return sum(
        1 for line in out.stdout.splitlines()
        if line.startswith("+### ") and not line.startswith("+++")
    )


# -----------------------------------------------------------------------------
# Metric computation
# -----------------------------------------------------------------------------

def compute_metric_values() -> dict[str, dict[str, dict[str, Any]]]:
    """Return {project: {metric_id: {current, baseline, percent_delta, ...}}}.

    Project-aware (Option C, Decision Log 2026-04-27): every metric is scoped
    to one project at a time. Some metrics are intrinsically global (e.g.
    trust_gate_overrides reads a single system-wide log) and only emit a row
    under the claude-hq project. The rest emit one row per registered project.

    Values may include metric-specific extras (e.g. 'pairs', 'sessions') used
    by the alert template — consumers should treat unexpected keys as opaque.
    """
    conn = db_connect()
    results: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        projects = load_projects()
        for project in projects:
            pname = project.name
            project_results: dict[str, dict[str, Any]] = {}

            # Per-project session-derived metrics
            project_results["user_corrections_per_session"] = _compute_with_baseline(
                conn, "AVG(correction_count)", "sessions",
                recent_days=3, baseline_days=14, project=pname,
            )
            project_results["messages_per_completed_task"] = _compute_with_baseline(
                conn, "AVG(user_messages * 1.0 / NULLIF(files_modified, 0))", "sessions",
                recent_days=3, baseline_days=14, where="files_modified > 0", project=pname,
            )
            project_results["subagents_per_task"] = _compute_with_baseline(
                conn, "AVG(tools_used * 1.0 / NULLIF(files_modified, 0))", "sessions",
                recent_days=3, baseline_days=14, where="files_modified > 0", project=pname,
            )
            project_results["session_duration_to_first_commit"] = _compute_with_baseline(
                conn, "AVG(duration_minutes)", "sessions",
                recent_days=3, baseline_days=14, where="duration_minutes > 0", project=pname,
            )

            # Per-project commit-derived metrics
            project_results["git_revert"] = _compute_revert_flag(conn, project=pname)
            project_results["lessons_rule_velocity"] = _compute_rule_velocity(conn, project=pname)

            # Per-project session-content scans
            project_results["mission_board_before_agents"] = (
                _compute_mission_board_before_agents(conn, project=pname)
            )

            # Lessons-file-dependent metric — only emits if the project has a
            # lessons_path. v1 keeps this scoped to claude-hq per Decision Log
            # Option A (PATS lessons not scanned).
            if project.lessons_path and project.lessons_path.is_file():
                project_results["repeated_mistake_signal"] = (
                    _compute_repeated_mistake_signal(project)
                )

            # Global signals — only attached to the default project (claude-hq).
            # B-readiness note: when splitting per-project later, leave these
            # under whichever instance owns the global infrastructure.
            if pname == DEFAULT_PROJECT:
                project_results["trust_gate_overrides"] = _compute_trust_gate_overrides()

            results[pname] = project_results
    finally:
        conn.close()
    return results


def _compute_with_baseline(
    conn: sqlite3.Connection,
    agg_expr: str,
    table: str,
    recent_days: int,
    baseline_days: int,
    where: str = "1=1",
    project: Optional[str] = None,
) -> dict[str, float]:
    cutoff_recent = (datetime.now() - timedelta(days=recent_days)).strftime("%Y-%m-%d")
    cutoff_baseline_start = (datetime.now() - timedelta(days=baseline_days)).strftime("%Y-%m-%d")

    project_clause = ""
    project_params: tuple = ()
    if project is not None:
        project_clause = " AND project = ?"
        project_params = (project,)

    current_row = conn.execute(
        f"SELECT {agg_expr} AS val FROM {table} "
        f"WHERE session_date >= ? AND {where}{project_clause}",
        (cutoff_recent, *project_params),
    ).fetchone()
    current = float(current_row["val"]) if current_row and current_row["val"] else 0.0

    baseline_row = conn.execute(
        f"SELECT {agg_expr} AS val FROM {table} "
        f"WHERE session_date >= ? AND session_date < ? AND {where}{project_clause}",
        (cutoff_baseline_start, cutoff_recent, *project_params),
    ).fetchone()
    baseline = float(baseline_row["val"]) if baseline_row and baseline_row["val"] else 0.0

    pct_delta = ((current - baseline) / baseline * 100.0) if baseline > 0 else 0.0
    return {"current": current, "baseline": baseline, "percent_delta": pct_delta}


def _compute_rule_velocity(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
) -> dict[str, float]:
    cutoff_7d = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    cutoff_24h = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    project_clause = " AND project = ?" if project else ""
    project_params: tuple = (project,) if project else ()
    rules_7d = conn.execute(
        f"SELECT COALESCE(SUM(lessons_rules_added),0) AS n FROM commits "
        f"WHERE commit_date >= ?{project_clause}",
        (cutoff_7d, *project_params),
    ).fetchone()["n"]
    rules_24h = conn.execute(
        f"SELECT COALESCE(SUM(lessons_rules_added),0) AS n FROM commits "
        f"WHERE commit_date >= ?{project_clause}",
        (cutoff_24h, *project_params),
    ).fetchone()["n"]
    return {
        "current": float(rules_24h),
        "baseline": float(rules_7d) / 7.0,
        "percent_delta": 0.0,
        "rules_24h": float(rules_24h),
        "rules_7d": float(rules_7d),
    }


def _compute_revert_flag(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
) -> dict[str, float]:
    cutoff_24h = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    project_clause = " AND project = ?" if project else ""
    project_params: tuple = (project,) if project else ()
    n = conn.execute(
        f"SELECT COUNT(*) AS n FROM commits "
        f"WHERE commit_date >= ? AND is_revert=1{project_clause}",
        (cutoff_24h, *project_params),
    ).fetchone()["n"]
    return {"current": float(n), "baseline": 0.0, "percent_delta": 0.0}


def _compute_trust_gate_overrides() -> dict[str, float]:
    if not TRUST_GATE_LOG.is_file():
        return {"current": 0.0, "baseline": 0.0, "percent_delta": 0.0}
    try:
        text = TRUST_GATE_LOG.read_text()
    except OSError:
        return {"current": 0.0, "baseline": 0.0, "percent_delta": 0.0}
    count_24h = 0
    cutoff = datetime.now() - timedelta(days=1)
    for line in text.splitlines():
        if "HQ_TRUST_OVERRIDE" not in line:
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if m:
            try:
                when = datetime.fromisoformat(m.group(1))
                if when >= cutoff:
                    count_24h += 1
            except ValueError:
                pass
    return {"current": float(count_24h), "baseline": 0.0, "percent_delta": 0.0}


# -----------------------------------------------------------------------------
# Repeated-mistake detection (claude-hq LESSONS.md scope only)
# -----------------------------------------------------------------------------

_TOKEN_STOPWORDS = {
    # Generic English
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "by", "at", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "this", "that", "these", "those", "have", "has", "had",
    "not", "no", "do", "does", "don't", "dont", "didn't", "should", "must",
    "can", "cannot", "could", "would", "will", "when", "where", "what",
    "why", "how", "if", "then", "than", "so", "also", "only", "just", "more",
    "most", "some", "any", "all", "every", "each", "both", "other", "same",
    "such", "into", "onto", "via", "without", "within", "over", "under",
    "they", "them", "their", "there", "here", "your", "you", "we're",
    "i'm", "it's", "thats", "still", "yet", "ever", "much", "many",
    # LESSONS-domain noise — words that recur across most rules and don't
    # carry topical meaning. Filtered so similarity reflects *what* the rule
    # is about, not the rule format itself.
    "rule", "rules", "apply", "applies", "applied", "example", "examples",
    "because", "claude", "commander", "lesson", "lessons", "session",
    "sessions", "mistake", "mistakes", "happened", "incident", "reason",
    "reasons", "always", "never", "instead", "before", "after", "during",
    "first", "next", "user", "users", "input", "output", "current",
    "code", "file", "files", "path", "paths", "step", "steps", "work",
    "working", "build", "built", "ship", "ships", "shipped", "make",
    "makes", "made", "real", "right", "wrong", "fail", "fails", "failed",
    "failure", "issue", "issues", "problem", "problems",
}


def _tokenize_for_similarity(text: str) -> set[str]:
    """Lowercase, keep alphabetic tokens >=5 chars, drop common stopwords."""
    tokens = re.findall(r"[a-z][a-z'-]{4,}", text.lower())
    return {t.strip("'-") for t in tokens if t.strip("'-") not in _TOKEN_STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse_lessons_rules(lessons_path: Path) -> list[dict[str, Any]]:
    """Return list of {title, body, tokens} for each ### rule in the given lessons file."""
    if not lessons_path.is_file():
        return []
    try:
        text = lessons_path.read_text()
    except OSError:
        return []
    pattern = re.compile(r"^### (.+?)\n(.*?)(?=\n### |\Z)", re.MULTILINE | re.DOTALL)
    rules: list[dict[str, Any]] = []
    for m in pattern.finditer(text):
        title = m.group(1).strip()
        body = m.group(2).strip()[:600]
        rules.append({
            "title": title,
            "body": body,
            "tokens": _tokenize_for_similarity(title + " " + body),
        })
    return rules


def _recently_added_rule_titles(
    repo_path: Path,
    lessons_rel: str,
    days: int = 14,
) -> set[str]:
    """Titles of rule headings added to the given lessons file in the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "log", f"--since={cutoff}",
             "--pretty=format:%H", "--", lessons_rel],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return set()
    titles: set[str] = set()
    for sha in (s.strip() for s in out.stdout.splitlines() if s.strip()):
        try:
            diff = subprocess.run(
                ["git", "-C", str(repo_path), "show", sha, "--", lessons_rel],
                capture_output=True, text=True, timeout=10, check=False,
            ).stdout
        except subprocess.SubprocessError:
            continue
        for line in diff.splitlines():
            if line.startswith("+### ") and not line.startswith("+++"):
                title = line[5:].strip()
                if title:
                    titles.add(title)
    return titles


def _compute_repeated_mistake_signal(project: ProjectConfig) -> dict[str, Any]:
    """Detect rules added in the last 14 days that overlap topically with
    other rules in the given project's lessons file.

    Similarity rule (v1, tuned for high specificity / low recall):
      * Jaccard token overlap >= 0.40  AND
      * >= 5 shared meaningful content tokens (5+ chars, non-stopword)

    Project-scoped (Option C): each project with a lessons_path gets its own
    repeat detection over its own lessons file. Only invoked by the caller
    when project.lessons_path is set, so we can assume it's not None here.
    """
    if not project.lessons_path:
        return {"current": 0.0, "baseline": 0.0, "percent_delta": 0.0, "pairs": []}
    lessons_rel = str(project.lessons_path.relative_to(project.repo_path))

    rules = _parse_lessons_rules(project.lessons_path)
    if len(rules) < 2:
        return {"current": 0.0, "baseline": 0.0, "percent_delta": 0.0, "pairs": []}

    new_titles = _recently_added_rule_titles(project.repo_path, lessons_rel, days=14)
    if not new_titles:
        return {"current": 0.0, "baseline": 0.0, "percent_delta": 0.0, "pairs": []}

    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for new_rule in rules:
        if new_rule["title"] not in new_titles:
            continue
        for other in rules:
            if other["title"] == new_rule["title"]:
                continue
            key = tuple(sorted([new_rule["title"], other["title"]]))
            if key in seen:
                continue
            jac = _jaccard(new_rule["tokens"], other["tokens"])
            shared = new_rule["tokens"] & other["tokens"]
            # AND not OR — both signals must agree for a high-confidence repeat
            if jac >= 0.40 and len(shared) >= 5:
                pairs.append(key)
                seen.add(key)

    return {
        "current": float(len(pairs)),
        "baseline": 0.0,
        "percent_delta": 0.0,
        "pairs": pairs,
    }


# -----------------------------------------------------------------------------
# Mission-board-before-agents detection
# -----------------------------------------------------------------------------

def _compute_mission_board_before_agents(
    conn: sqlite3.Connection,
    project: Optional[str] = None,
) -> dict[str, Any]:
    """Re-parse session .tmp files in the last N days. Flag sessions where
    the Task tool was used (subagent spawned) but no MISSION_BOARD reference
    appears anywhere in the session summary.

    Project-scoped: uses the sessions table to find which session files belong
    to the given project, then re-parses those files for tool/file content.
    Falls back to scanning all sessions if project is None.

    v1 caveat: misses ordering within a single session — a session that
    spawned helpers and *then* wrote MISSION_BOARD.md still passes.
    """
    cutoff = datetime.now() - timedelta(days=7)
    cutoff_date = cutoff.strftime("%Y-%m-%d")
    offenders: list[str] = []

    if project is not None:
        rows = conn.execute(
            "SELECT session_file FROM sessions WHERE project = ? AND session_date >= ?",
            (project, cutoff_date),
        ).fetchall()
        candidate_files = [Path(r["session_file"]) for r in rows]
    else:
        if not SESSIONS_DIR.is_dir():
            return {"current": 0.0, "baseline": 0.0, "percent_delta": 0.0, "sessions": []}
        candidate_files = list(SESSIONS_DIR.glob("*.tmp"))

    for path in candidate_files:
        if not path.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if mtime < cutoff:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        tools = _extract_section_items(text, "Tools Used")
        # The Tools section can be either a bullet list or a comma-separated line —
        # parse_session_file already counts both, so check the raw text too.
        used_task_tool = (
            any(re.search(r"\bTask\b", t) for t in tools)
            or bool(re.search(r"^Tools Used\s*\n.*\bTask\b", text, re.MULTILINE | re.IGNORECASE))
        )
        if not used_task_tool:
            continue

        # Mission board reference anywhere — Files Modified, body, headings.
        # Match common variants (MISSION_BOARD.md, mission-board, mission board).
        mentions_board = bool(
            re.search(r"mission[_\- ]?board", text, re.IGNORECASE)
        )
        if mentions_board:
            continue

        offenders.append(path.name)

    return {
        "current": float(len(offenders)),
        "baseline": 0.0,
        "percent_delta": 0.0,
        "sessions": offenders,
    }


# -----------------------------------------------------------------------------
# Alert generation
# -----------------------------------------------------------------------------

CRITICAL_THROTTLE = timedelta(hours=1)


def _should_suppress(conn: sqlite3.Connection, metric_id: str, severity: str) -> tuple[bool, str]:
    """Decide whether to suppress this alert based on history and runtime state.

    Rules:
      * Runtime pause silences warn-level. Critical still fires (rate-limited).
      * Runtime quiet window silences warn-level. Critical still fires.
      * Muted metrics are silenced entirely — EXCEPT critical metrics which
        cannot be muted (reverts, trust-gate overrides, repeat-mistake).
      * Critical alerts fire at most once per hour per metric.
      * Warn alerts fire once per incident (edge-triggered — waits for the
        metric to go quiet before re-firing).

    Returns (suppress_bool, reason_str).
    """
    state = _load_runtime_state()

    # Mute applies first — but protected metrics can't be muted
    if metric_id in state.get("muted_metrics", []) and metric_id not in PROTECTED_METRICS:
        return True, f"metric muted by user (unmute with 'unmute {_metric_alias(metric_id)}')"

    if severity == "critical":
        # Hourly throttle
        last_alert = conn.execute(
            "SELECT MAX(computed_at) AS t FROM scores "
            "WHERE metric_id = ? AND alert_sent = 1 AND severity = 'critical'",
            (metric_id,),
        ).fetchone()["t"]
        if last_alert:
            try:
                last_dt = datetime.fromisoformat(last_alert)
                if datetime.now() - last_dt < CRITICAL_THROTTLE:
                    return True, f"critical alert already sent at {last_alert[:16]}, waiting up to an hour"
            except ValueError:
                pass
        return False, ""

    # Warn-level from here on — pause and quiet apply
    if state.get("paused"):
        return True, "alerts paused by user — reply 'resume' to re-enable"

    quiet_until = state.get("quiet_until")
    if quiet_until:
        try:
            if datetime.now() < datetime.fromisoformat(quiet_until):
                return True, f"alerts quiet until {quiet_until[:16]}"
        except ValueError:
            pass

    # Edge-triggered de-dup for warn-level
    last_alert = conn.execute(
        "SELECT MAX(computed_at) AS t FROM scores WHERE metric_id = ? AND alert_sent = 1",
        (metric_id,),
    ).fetchone()["t"]
    if not last_alert:
        return False, ""  # never alerted for this metric — fire

    last_quiet = conn.execute(
        "SELECT MAX(computed_at) AS t FROM scores "
        "WHERE metric_id = ? AND alert_sent = 0 AND suppressed = 0",
        (metric_id,),
    ).fetchone()["t"]

    if last_quiet and last_quiet > last_alert:
        # Metric cleared between last alert and now — this is a new occurrence
        return False, ""

    return True, f"already alerted at {last_alert} and condition has not cleared since"


# -----------------------------------------------------------------------------
# Runtime state — read by the scoring engine, written by the Telegram listener
# -----------------------------------------------------------------------------

RUNTIME_STATE_FILE = Path(__file__).parent / "runtime_state.json"

# Protected metrics cannot be muted from Telegram (reverts, trust-gate, repeats,
# mission-board skipping). Kept in sync with evolve.py PROTECTED_METRICS.
# Renamed 2026-04-27: git_revert_on_claude_hq → git_revert (Option C — no
# claude-hq exceptionalism in metric IDs; project tagging now happens via the
# scores.project column).
PROTECTED_METRICS = {
    "git_revert",
    "trust_gate_overrides",
    "lessons_rule_velocity",
    "repeated_mistake_signal",
    "mission_board_before_agents",
}


def _load_runtime_state() -> dict[str, Any]:
    """Read runtime state (paused / quiet / muted). Safe on missing/corrupt file."""
    if not RUNTIME_STATE_FILE.is_file():
        return {"paused": False, "quiet_until": None, "muted_metrics": []}
    try:
        return json.loads(RUNTIME_STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"paused": False, "quiet_until": None, "muted_metrics": []}


def _metric_alias(metric_id: str) -> str:
    """Reverse lookup: metric_id → short Telegram alias."""
    aliases = {
        "lessons_rule_velocity": "rules",
        "tokens_per_task": "cost",
        "user_corrections_per_session": "corrections",
        "subagents_per_task": "helpers",
        "session_duration_to_first_commit": "timing",
        "messages_per_completed_task": "messages",
        "trust_gate_overrides": "security",
        "git_revert": "reverts",
    }
    return aliases.get(metric_id, metric_id)


def _record_score(
    conn: sqlite3.Connection,
    metric_id: str,
    vals: dict[str, Any],
    severity: Optional[str],
    alert_sent: bool,
    suppressed: bool,
    suppression_reason: str,
    project: str = DEFAULT_PROJECT,
) -> None:
    """Persist the outcome of this assessment to the scores table."""
    conn.execute(
        """INSERT INTO scores
           (computed_at, metric_id, current_value, baseline_value, percent_delta,
            severity, alert_sent, suppressed, suppression_reason, project)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(timespec="seconds"),
            metric_id,
            float(vals.get("current", 0.0)),
            float(vals.get("baseline", 0.0)),
            float(vals.get("percent_delta", 0.0)),
            severity,
            1 if alert_sent else 0,
            1 if suppressed else 0,
            suppression_reason,
            project,
        ),
    )
    conn.commit()


def route_alert(alert: PlainAlert, project: str) -> dict:
    """Single point of dispatch for outbound alerts. (B-readiness #3)

    For Option C, every project's alerts go through the one shared Telegram
    bot. To split into per-project bots later (Option B), swap this function
    to look up `project` in a routing table and pick the right credentials.
    Callers should not call telegram.send() directly — always go through here.
    """
    # project arg currently unused at the routing layer (single bot for all),
    # but the signature is the future hook for B. Don't remove.
    _ = project
    return send_telegram(alert)


def _try_send(
    conn: sqlite3.Connection,
    metric_id: str,
    vals: dict[str, Any],
    severity: str,
    reason: str,
    extra: Optional[dict[str, Any]] = None,
    project: str = DEFAULT_PROJECT,
    label: Optional[str] = None,
) -> dict[str, Any]:
    """Send an alert if suppression allows, and record the outcome.

    project is the canonical key (matches sessions.project / commits.project /
      scores.project). Used for DB writes and routing.
    label is the friendly display name shown in the alert body. Falls back to
      project when None.
    """
    display = label or project
    outcome: dict[str, Any] = {
        "metric": metric_id, "project": project, "value": vals,
        "action": "none", "reason": reason,
    }

    suppress, suppress_reason = _should_suppress(conn, metric_id, severity)
    if suppress:
        _record_score(conn, metric_id, vals, severity,
                      alert_sent=False, suppressed=True,
                      suppression_reason=suppress_reason, project=project)
        outcome["action"] = "suppressed"
        outcome["reason"] = f"{reason} — {suppress_reason}"
        return outcome

    alert = _build_alert(metric_id, vals, severity=severity, extra=extra, project=display)
    result = route_alert(alert, project)
    sent = bool(result.get("ok"))
    _record_score(conn, metric_id, vals, severity,
                  alert_sent=sent, suppressed=False, suppression_reason="",
                  project=project)
    outcome["action"] = "sent" if sent else "failed"
    return outcome


def _record_quiet(
    conn: sqlite3.Connection,
    metric_id: str,
    vals: dict[str, Any],
    project: str = DEFAULT_PROJECT,
) -> None:
    """Record a 'quiet' observation so edge-triggering knows the condition cleared."""
    _record_score(conn, metric_id, vals, severity=None,
                  alert_sent=False, suppressed=False, suppression_reason="",
                  project=project)


def assess_and_alert(
    warmup_sessions: int = 7,
    scope_project: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Compute metrics for every registered project, alert per (project, metric).

    Project-aware (Option C): outer loop over projects, inner loop over metrics.
    Every alert is tagged with its project so route_alert can dispatch
    correctly (single bot today; per-project bots in a future B split).

    Args:
      scope_project: when set, assess only this one project. Used by the
        per-project post-commit hook to avoid re-scoring everything on
        every commit. Must match a name in projects.json.

    De-dup rules:
      * critical severity always fires
      * warn severity fires once per occurrence (edge-triggered via scores table)
      * quiet observations are also recorded so re-occurrence can be detected
    """
    conn = db_connect()
    outcomes: list[dict[str, Any]] = []

    try:
        all_values = compute_metric_values()
        if scope_project is not None:
            all_values = {
                k: v for k, v in all_values.items() if k == scope_project
            }
        # Map canonical name → friendly label for alert prefixing
        labels = {p.name: p.label for p in load_projects()}
        for project, project_metrics in all_values.items():
            project_label = labels.get(project, project)
            # Per-project warmup gate — projects with fewer sessions still
            # benefit from critical alerts but have warn-tier suppressed.
            total_sessions = conn.execute(
                "SELECT COUNT(*) AS n FROM sessions WHERE project = ?",
                (project,),
            ).fetchone()["n"]

            for metric_id, vals in project_metrics.items():
                fired = False
                current = float(vals.get("current", 0.0) or 0.0)

                if metric_id == "git_revert" and current > 0:
                    outcomes.append(_try_send(
                        conn, metric_id, vals, "critical",
                        reason=f"revert on {project} ({int(current)} commits)",
                        project=project, label=project_label,
                    ))
                    fired = True

                elif metric_id == "trust_gate_overrides" and current > 0:
                    outcomes.append(_try_send(
                        conn, metric_id, vals, "critical",
                        reason=f"trust gate override used ({int(current)}x)",
                        project=project, label=project_label,
                    ))
                    fired = True

                elif metric_id == "repeated_mistake_signal" and current > 0:
                    pairs = vals.get("pairs", [])
                    pair_count = int(current)
                    outcomes.append(_try_send(
                        conn, metric_id, vals, "critical",
                        reason=f"repeated-mistake pairs in last 14d: {pair_count}",
                        extra={"count": pair_count, "pairs": pairs},
                        project=project, label=project_label,
                    ))
                    fired = True

                elif metric_id == "mission_board_before_agents" and current > 0:
                    offender_count = int(current)
                    outcomes.append(_try_send(
                        conn, metric_id, vals, "critical",
                        reason=f"sessions skipping mission board: {offender_count}",
                        extra={"count": offender_count},
                        project=project, label=project_label,
                    ))
                    fired = True

                elif metric_id == "lessons_rule_velocity":
                    rules_24h = float(vals.get("rules_24h", 0) or 0)
                    rules_7d = float(vals.get("rules_7d", 0) or 0)
                    if rules_24h > 2:
                        outcomes.append(_try_send(
                            conn, metric_id, vals, "warn",
                            reason=f"rules added in 24h: {int(rules_24h)}",
                            extra={"count": int(rules_24h), "window": "day"},
                            project=project, label=project_label,
                        ))
                        fired = True
                    elif rules_7d > 3:
                        outcomes.append(_try_send(
                            conn, metric_id, vals, "warn",
                            reason=f"rules added in 7d: {int(rules_7d)}",
                            extra={"count": int(rules_7d), "window": "week"},
                            project=project, label=project_label,
                        ))
                        fired = True

                elif total_sessions < warmup_sessions:
                    outcomes.append({
                        "metric": metric_id, "project": project, "value": vals,
                        "action": "warmup",
                        "reason": f"only {total_sessions}/{warmup_sessions} sessions captured for {project}",
                    })
                    fired = True

                else:
                    pct = float(vals.get("percent_delta", 0.0) or 0.0)
                    warn_threshold = {
                        "subagents_per_task": 50,
                        "tokens_per_task": 30,
                        "user_corrections_per_session": 50,
                        "messages_per_completed_task": 30,
                        "session_duration_to_first_commit": 50,
                    }.get(metric_id)
                    if warn_threshold and pct > warn_threshold:
                        outcomes.append(_try_send(
                            conn, metric_id, vals, "warn",
                            reason=f"up {int(pct)}% vs recent normal",
                            extra={"percent_more": int(pct)},
                            project=project, label=project_label,
                        ))
                        fired = True

                if not fired:
                    _record_quiet(conn, metric_id, vals, project=project)
                    outcomes.append({
                        "metric": metric_id, "project": project, "value": vals,
                        "action": "quiet", "reason": "",
                    })
    finally:
        conn.close()

    return outcomes


METRIC_EMOJI = {
    "user_corrections_per_session": "💬",
    "messages_per_completed_task": "💬",
    "lessons_rule_velocity": "📚",
    "repeated_mistake_signal": "🔁",
    "tokens_per_task": "💸",
    "subagents_per_task": "🧑‍🤝‍🧑",
    "session_duration_to_first_commit": "🐢",
    "mission_board_before_agents": "⚠️",
    "lessons_read_at_session_start": "📖",
    "trust_gate_overrides": "🚨",
    "git_revert": "⏪",
}


def _build_alert(
    metric_id: str,
    vals: dict[str, Any],
    severity: str,
    extra: Optional[dict[str, Any]] = None,
    project: str = DEFAULT_PROJECT,
) -> PlainAlert:
    """Construct a PlainAlert from metrics.yaml templates. Zero jargon allowed.

    Project-aware (Option C): a [PROJECT] tag is prefixed to what_happened so
    Sunil can tell at a glance which project an alert belongs to. The headline
    emoji + the [PROJECT] tag both appear before the prose body.
    """
    extra = extra or {}
    emoji = METRIC_EMOJI.get(metric_id, "")
    template_map = _load_alert_templates()
    tpl = template_map.get(metric_id)
    if not tpl:
        return PlainAlert(
            what_happened=(
                f"[{project}] A quality signal has shifted in the HQ system. "
                "Something in how Commander is working has changed."
            ),
            what_to_do=(
                "If you want to investigate, run: "
                "python3 ~/claude-hq/watchdog/watchdog.py --sessions"
            ),
            severity=severity,
            headline_emoji=emoji,
        )

    # Render template with safe defaults
    context = {
        "percent_more": int(abs(float(vals.get("percent_delta", 0) or 0))),
        "count": int(float(vals.get("current", 0) or 0)),
        "window": "recently",
        "missed_count": int(float(vals.get("current", 0) or 0)),
        "total_count": 5,
        "minutes_ago": 0,
        "project": project,
        **extra,
    }
    try:
        rendered = tpl.format(**context)
    except (KeyError, IndexError):
        rendered = tpl

    what_happened, _, what_to_do = rendered.partition("What to do:")
    if not what_to_do:
        what_happened = rendered
        what_to_do = (
            "If you want details, run: "
            "python3 ~/claude-hq/watchdog/watchdog.py --sessions"
        )

    body = _strip_leading_emoji(what_happened.strip())
    # Tag the alert body with the project so the recipient knows the scope.
    # Skipped if the body already references the project (template authors
    # may include {project} in their copy directly).
    if f"[{project}]" not in body:
        body = f"[{project}] {body}"

    return PlainAlert(
        what_happened=body,
        what_to_do=what_to_do.strip(),
        severity=severity,
        headline_emoji=emoji,
    )


def _strip_leading_emoji(text: str) -> str:
    """Remove leading emoji + whitespace so the alert doesn't double-emoji.

    Templates historically led with an emoji (e.g. '📚 Commander ...') and the
    header also had an emoji, producing visual clutter. We now put the emoji
    on the headline only; template bodies are plain text.
    """
    # Simple heuristic: if the first line looks like "<emoji> Title\n\nBody",
    # drop everything up to the first blank line.
    lines = text.splitlines()
    if not lines:
        return text
    first = lines[0].strip()
    # If first "line" is short and contains a non-ASCII emoji char, drop it
    if len(first) < 80 and any(ord(c) > 0x2600 for c in first):
        # Drop first line + any blank lines that follow
        idx = 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        return "\n".join(lines[idx:]).strip()
    return text


def _load_alert_templates() -> dict[str, str]:
    """Load alert_template strings from metrics.yaml (minimal YAML parsing)."""
    if not METRICS_YAML.is_file():
        return {}
    text = METRICS_YAML.read_text()
    templates: dict[str, str] = {}
    current_id: Optional[str] = None
    collecting_template = False
    buffer: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current_id and buffer:
                templates[current_id] = "\n".join(buffer).strip()
            current_id = stripped.split(":", 1)[1].strip()
            buffer = []
            collecting_template = False
        elif "alert_template:" in stripped and "|" in stripped:
            collecting_template = True
            buffer = []
        elif collecting_template:
            if line and not line.startswith(" " * 6):
                # End of block
                collecting_template = False
                if current_id:
                    templates[current_id] = "\n".join(buffer).strip()
                buffer = []
            else:
                buffer.append(line.strip())

    if current_id and buffer and collecting_template:
        templates[current_id] = "\n".join(buffer).strip()

    return templates


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Plain-language helpers — used by plain=True renderers
# -----------------------------------------------------------------------------

def _humanise_date(iso_date: str) -> str:
    """Convert '2026-04-21' into 'today' / 'yesterday' / '3 days ago' / '21 Apr'."""
    try:
        d = datetime.strptime(iso_date[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return iso_date[:10]
    today = datetime.now().date()
    delta = (today - d).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "yesterday"
    if 2 <= delta <= 6:
        return f"{delta} days ago"
    return d.strftime("%-d %b")


def _humanise_duration(minutes: int) -> str:
    if minutes <= 0:
        return "—"
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours} hr"
    return f"{hours} hr {mins} min"


def _humanise_message(text: str) -> str:
    """Strip conventional-commit prefix so the message reads naturally."""
    if not text:
        return ""
    cleaned = re.sub(r"^(feat|fix|docs|chore|refactor|test|lessons?|style)(\([^)]+\))?:\s*", "", text)
    return cleaned[:120]


# -----------------------------------------------------------------------------
# CLI commands — return strings; plain=True renders in conversational prose
# -----------------------------------------------------------------------------

def cli_rules(days: int = 7, plain: bool = False) -> str:
    """Report recent LESSONS.md rule additions."""
    _ingest_if_stale()
    conn = db_connect()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT sha, commit_date, message, lessons_rules_added
           FROM commits WHERE commit_date >= ? AND touches_lessons=1 AND lessons_rules_added > 0
           ORDER BY commit_date DESC""",
        (since,),
    ).fetchall()
    conn.close()
    total = sum(r["lessons_rules_added"] for r in rows)

    titles: list[str] = []
    if LESSONS_FILE.is_file():
        titles = re.findall(r"^### (.+)$", LESSONS_FILE.read_text(), re.MULTILINE)

    if plain:
        return _render_rules_plain(rows, total, titles, days)
    return _render_rules_terminal(rows, total, titles, days)


def _render_rules_terminal(rows: list[Any], total: int, titles: list[str], days: int) -> str:
    out: list[str] = [f"LESSONS.md updates in the last {days} days:", ""]
    for r in rows:
        out.append(f"  {r['commit_date'][:10]}  +{r['lessons_rules_added']} rule(s)  {r['sha'][:8]}")
        out.append(f"                {r['message'][:100]}")
        out.append("")
    out.append(f"Total new rules in the last {days} days: {total}")
    if titles:
        out.append("")
        out.append(f"All rule titles currently in LESSONS.md ({len(titles)} total):")
        for t in titles[-10:]:
            out.append(f"  • {t}")
    return "\n".join(out)


def _render_rules_plain(rows: list[Any], total: int, titles: list[str], days: int) -> str:
    lines: list[str] = []
    if total == 0:
        lines.append(f"No new lessons in the last {days} days. Commander has been running without needing to learn anything new.")
        return "\n".join(lines)

    if total == 1:
        lines.append(f"One new lesson got added in the last {days} days.")
    else:
        lines.append(f"Commander has picked up {total} new lessons in the last {days} days.")

    lines.append("")
    lines.append("Here's when each batch came in:")
    for r in rows:
        when = _humanise_date(r["commit_date"])
        n = r["lessons_rules_added"]
        desc = _humanise_message(r["message"])
        lines.append(f"• {when} — {n} new rule{'s' if n != 1 else ''} — {desc}")

    if titles:
        lines.append("")
        lines.append("Most recent rule titles:")
        for t in titles[-5:]:
            # Strip the leading "N. " if present
            clean = re.sub(r"^\d+\.\s*", "", t).strip()
            lines.append(f"• {clean}")

    lines.append("")
    lines.append(
        "Rough guide: if the lessons look like bugs being patched, something's going wrong. "
        "If they look like deliberate system improvements, you're good."
    )
    return "\n".join(lines)


def cli_sessions(limit: int = 10, plain: bool = False) -> str:
    """Report on the most recent sessions."""
    _ingest_if_stale()
    conn = db_connect()
    rows = conn.execute(
        """SELECT session_date, project, branch, user_messages, files_modified,
                  tools_used, correction_count, duration_minutes
           FROM sessions ORDER BY session_date DESC, id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    if plain:
        return _render_sessions_plain(rows)
    return _render_sessions_terminal(rows)


def _render_sessions_terminal(rows: list[Any]) -> str:
    out: list[str] = [f"Last {len(rows)} sessions:", ""]
    out.append(f"  {'date':<11}  {'project':<25}  {'msgs':>5}  {'files':>6}  {'tools':>6}  {'corrs':>6}  {'mins':>5}")
    out.append(f"  {'-'*11}  {'-'*25}  {'-'*5}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*5}")
    for r in rows:
        proj = (r["project"] or "?")[:25]
        out.append(
            f"  {r['session_date']:<11}  {proj:<25}  "
            f"{r['user_messages']:>5}  {r['files_modified']:>6}  {r['tools_used']:>6}  "
            f"{r['correction_count']:>6}  {r['duration_minutes']:>5}"
        )
    out.append("")
    out.append("  msgs = how many messages you sent     tools = how many tool calls Commander made")
    out.append("  files = how many files got touched     corrs = times you pushed back / corrected")
    return "\n".join(out)


def _render_sessions_plain(rows: list[Any]) -> str:
    if not rows:
        return "No sessions recorded yet."
    lines: list[str] = [f"Here are the last {len(rows)} sessions:", ""]
    for r in rows:
        when = _humanise_date(r["session_date"])
        proj = (r["project"] or "?").strip()
        msgs = r["user_messages"] or 0
        files = r["files_modified"] or 0
        corrs = r["correction_count"] or 0
        mins = _humanise_duration(r["duration_minutes"] or 0)
        corr_phrase = (
            "no corrections from you"
            if corrs == 0
            else f"{corrs} correction{'s' if corrs != 1 else ''} from you"
        )
        files_phrase = (
            "no file changes"
            if files == 0
            else f"{files} file{'s' if files != 1 else ''} changed"
        )
        lines.append(
            f"• {when} — {proj} — {msgs} of your messages, "
            f"{files_phrase}, {corr_phrase}, ran about {mins}."
        )
    return "\n".join(lines)


def cli_security(days: int = 30, plain: bool = False) -> str:
    """Report recent reverts + Trust Gate overrides."""
    _ingest_if_stale()
    conn = db_connect()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    reverts = conn.execute(
        """SELECT sha, commit_date, message FROM commits
           WHERE commit_date >= ? AND is_revert=1
           ORDER BY commit_date DESC""",
        (since,),
    ).fetchall()
    conn.close()

    overrides: list[str] = []
    if TRUST_GATE_LOG.is_file():
        try:
            text = TRUST_GATE_LOG.read_text()
            cutoff = datetime.now() - timedelta(days=days)
            for line in text.splitlines():
                if "HQ_TRUST_OVERRIDE" not in line:
                    continue
                m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
                if not m:
                    continue
                try:
                    when = datetime.fromisoformat(m.group(1))
                except ValueError:
                    continue
                if when >= cutoff:
                    overrides.append(line[:180])
        except OSError:
            pass

    if plain:
        return _render_security_plain(reverts, overrides, days)
    return _render_security_terminal(reverts, overrides, days)


def _render_security_terminal(reverts: list[Any], overrides: list[str], days: int) -> str:
    out: list[str] = [f"Reverts on claude-hq in the last {days} days:"]
    if not reverts:
        out.append("  (none)")
    for r in reverts:
        out.append(f"  {r['commit_date'][:10]}  {r['sha'][:8]}  {r['message'][:100]}")
    out.append("")
    out.append(f"Trust Gate overrides in the last {days} days:")
    if not overrides:
        out.append("  (none)")
    for line in overrides:
        out.append(f"  {line}")
    return "\n".join(out)


def _render_security_plain(reverts: list[Any], overrides: list[str], days: int) -> str:
    lines: list[str] = []
    all_clean = not reverts and not overrides

    if all_clean:
        lines.append(f"Good news — nothing risky in the last {days} days.")
        lines.append("")
        lines.append("✓ No commits on HQ have been rolled back.")
        lines.append("✓ The security gate (that checks outside code before letting it in) hasn't been bypassed.")
        lines.append("")
        lines.append("Both of these are the kind of thing you'd want to hear about immediately. Silence here is the right signal.")
        return "\n".join(lines)

    lines.append(f"A couple of security-relevant things in the last {days} days:")
    lines.append("")

    if reverts:
        lines.append(f"⏪ {len(reverts)} change{'s' if len(reverts) != 1 else ''} to HQ had to be rolled back:")
        for r in reverts:
            when = _humanise_date(r["commit_date"])
            desc = _humanise_message(r["message"])
            lines.append(f"   • {when} — {desc}")
    else:
        lines.append("✓ No commits on HQ have been rolled back.")

    lines.append("")

    if overrides:
        lines.append(f"🚨 The security gate was bypassed {len(overrides)} time{'s' if len(overrides) != 1 else ''}:")
        for line in overrides[:5]:
            lines.append(f"   • {line[:120]}")
    else:
        lines.append("✓ The security gate hasn't been bypassed.")

    return "\n".join(lines)


def cli_cost(plain: bool = False) -> str:
    """Report cost / efficiency numbers across recent vs older sessions."""
    _ingest_if_stale()
    values = compute_metric_values()
    labels = {
        "tokens_per_task": "thinking per task",
        "subagents_per_task": "helpers per task",
        "messages_per_completed_task": "your messages per task",
        "session_duration_to_first_commit": "minutes to first change",
    }
    ordered = [k for k in labels.keys() if values.get(k)]
    if plain:
        return _render_cost_plain(values, labels, ordered)
    return _render_cost_terminal(values, labels, ordered)


def _render_cost_terminal(values: dict, labels: dict, ordered: list[str]) -> str:
    out: list[str] = ["Cost & efficiency snapshot", ""]
    for key in ordered:
        v = values[key]
        current = v.get("current", 0.0)
        baseline = v.get("baseline", 0.0)
        delta = v.get("percent_delta", 0.0)
        direction = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        out.append(
            f"  {labels[key]:<28}  recent: {current:>7.2f}   "
            f"recent normal: {baseline:>7.2f}   {direction} {abs(delta):5.1f}%"
        )
    return "\n".join(out)


def _render_cost_plain(values: dict, labels: dict, ordered: list[str]) -> str:
    if not ordered:
        return "Not enough data yet for a cost snapshot — the watchdog needs a few more sessions."

    lines: list[str] = ["Here's how Commander has been performing lately.", ""]
    had_signal = False
    for key in ordered:
        v = values[key]
        delta = v.get("percent_delta", 0.0)
        label = labels[key]
        rounded = int(round(abs(delta) / 5) * 5)
        if rounded == 0 and abs(delta) >= 1:
            rounded = int(abs(delta))

        if abs(delta) < 2:
            lines.append(f"→ {label}: basically unchanged from normal.")
        elif delta > 0:
            # More of this thing than normal (for cost metrics, this is usually worse)
            lines.append(f"↑ {label}: about {rounded}% higher than normal.")
            had_signal = True
        else:
            # Less than normal — for cost metrics, this is usually good
            lines.append(f"✓ {label}: about {rounded}% lower than normal.")

    if had_signal:
        lines.append("")
        lines.append(
            "Worth watching if the 'higher than normal' numbers keep climbing — that's usually the "
            "first sign Commander is drifting."
        )
    return "\n".join(lines)


def _ingest_if_stale(max_age_minutes: int = 30) -> None:
    """Re-ingest sessions/commits if the DB hasn't been updated lately."""
    if not HISTORY_DB.is_file():
        ingest_sessions(); ingest_commits()
        return
    age_sec = (datetime.now() - datetime.fromtimestamp(HISTORY_DB.stat().st_mtime)).total_seconds()
    if age_sec > max_age_minutes * 60:
        ingest_sessions(); ingest_commits()


def main() -> int:
    parser = argparse.ArgumentParser(description="HQ Watchdog scoring engine")
    parser.add_argument("--ingest", action="store_true", help="Parse sessions + git log into DB")
    parser.add_argument("--stats", action="store_true", help="Print raw stats")
    parser.add_argument("--assess", action="store_true", help="Compute metrics + send alerts if needed")
    parser.add_argument("--digest", action="store_true", help="Send the daily digest")
    parser.add_argument("--all", action="store_true", help="Shortcut for --ingest + --assess")
    parser.add_argument("--rules", action="store_true", help="List recent LESSONS.md rule additions")
    parser.add_argument("--sessions", action="store_true", help="Show recent sessions with key numbers")
    parser.add_argument("--security", action="store_true", help="Show recent reverts and Trust Gate overrides")
    parser.add_argument("--cost", action="store_true", help="Show cost / efficiency snapshot")
    parser.add_argument("--project", type=str, default=None,
                        help="Scope --assess to a single project (must match a name in projects.json). When omitted, all registered projects are assessed.")
    args = parser.parse_args()

    ran_something = False

    if args.ingest or args.all:
        ran_something = True
        n_sessions = ingest_sessions()
        n_commits = ingest_commits()
        print(f"ingested: {n_sessions} new sessions, commits table refreshed ({n_commits} rows touched)")

    if args.stats:
        ran_something = True
        conn = db_connect()
        total = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
        commits = conn.execute("SELECT COUNT(*) AS n FROM commits").fetchone()["n"]
        conn.close()
        print(f"sessions in db: {total}")
        print(f"commits in db:  {commits}")
        print("metric snapshot:")
        for metric, vals in compute_metric_values().items():
            print(f"  {metric}: {json.dumps(vals, default=float)}")

    if args.assess or args.all:
        ran_something = True
        outcomes = assess_and_alert(scope_project=args.project)
        for o in outcomes:
            project = o.get("project", "")
            tag = f"[{project}] " if project else ""
            print(f"  [{o['action']:7}] {tag}{o['metric']}: {o['reason']}")

    if args.digest:
        ran_something = True
        # Placeholder: daily digest sender (implemented in evolve.py)
        print("digest: use evolve.py --daily for now")

    if args.rules:
        ran_something = True
        print(cli_rules())

    if args.sessions:
        ran_something = True
        print(cli_sessions())

    if args.security:
        ran_something = True
        print(cli_security())

    if args.cost:
        ran_something = True
        print(cli_cost())

    if not ran_something:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())

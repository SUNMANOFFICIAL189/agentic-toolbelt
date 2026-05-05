"""SQLite schema + connection helpers for the API index."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "apis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS apis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    category        TEXT,
    auth            TEXT,
    https           INTEGER,
    cors            TEXT,
    link            TEXT,
    openapi_url     TEXT,
    openapi_version TEXT,
    indexed_at      TEXT NOT NULL,
    UNIQUE(source, name, link)
);

CREATE INDEX IF NOT EXISTS idx_apis_category ON apis(category);
CREATE INDEX IF NOT EXISTS idx_apis_source ON apis(source);
CREATE INDEX IF NOT EXISTS idx_apis_auth ON apis(auth);

CREATE VIRTUAL TABLE IF NOT EXISTS apis_fts USING fts5(
    name,
    description,
    category,
    content='apis',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS apis_ai AFTER INSERT ON apis BEGIN
    INSERT INTO apis_fts(rowid, name, description, category)
    VALUES (new.id, new.name, new.description, new.category);
END;

CREATE TRIGGER IF NOT EXISTS apis_ad AFTER DELETE ON apis BEGIN
    INSERT INTO apis_fts(apis_fts, rowid, name, description, category)
    VALUES ('delete', old.id, old.name, old.description, old.category);
END;

CREATE TRIGGER IF NOT EXISTS apis_au AFTER UPDATE ON apis BEGIN
    INSERT INTO apis_fts(apis_fts, rowid, name, description, category)
    VALUES ('delete', old.id, old.name, old.description, old.category);
    INSERT INTO apis_fts(rowid, name, description, category)
    VALUES (new.id, new.name, new.description, new.category);
END;
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def reset() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    connect().close()

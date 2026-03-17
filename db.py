import os
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(os.environ.get("GREENBELT_DB", Path.home() / ".claude" / "greenbelt.sqlite3"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            used_tokens INTEGER NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_created_at ON usage_events(created_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS planted_trees (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            used_tokens INTEGER NOT NULL,
            num_trees   INTEGER NOT NULL,
            provider    TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)
    conn.close()


def append_usage(*, session_id: str, used_tokens: int, timestamp: datetime) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            "INSERT INTO usage_events (session_id, used_tokens, created_at) VALUES (?, ?, ?)",
            (session_id, used_tokens, timestamp),
        )
    conn.close()


def get_total_trees() -> int:
    conn = _connect()
    row = conn.execute("SELECT COALESCE(SUM(num_trees), 0) FROM planted_trees").fetchone()
    conn.close()
    return row[0]

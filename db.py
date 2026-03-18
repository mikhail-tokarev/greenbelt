import os
import sqlite3
from datetime import datetime
from pathlib import Path

__all__ = [
    "init_db",
    "add_usage",
    "get_total_trees",
    "get_unaccounted_usage",
    "add_trees",
]

DB_PATH = Path(os.environ.get("GREENBELT_DB", Path.home() / ".claude" / "greenbelt.sqlite3"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    if DB_PATH.exists():
        return    # assume it's already initialized

    conn = get_connection()
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


def add_usage(*, session_id: str, used_tokens: int, timestamp: datetime) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO usage_events (session_id, used_tokens, created_at) VALUES (?, ?, ?)",
            (session_id, used_tokens, timestamp),
        )
    conn.close()


def add_trees(*, used_tokens: int, num_trees: int, provider: str, timestamp: datetime) -> None:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO planted_trees (used_tokens, num_trees, provider, created_at) VALUES (?, ?, ?, ?)",
            (used_tokens, num_trees, provider, timestamp),
        )
    conn.close()


def get_unaccounted_usage() -> int:
    conn = get_connection()
    row = conn.execute("""
        SELECT
          COALESCE((SELECT SUM(used_tokens) FROM usage_events), 0)
          - COALESCE((SELECT SUM(used_tokens) FROM planted_trees), 0)
    """).fetchone()
    conn.close()
    return row[0]


def get_total_trees() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COALESCE(SUM(num_trees), 0) FROM planted_trees").fetchone()
    conn.close()
    return row[0]

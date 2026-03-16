#!/usr/bin/env python3

import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from datetime import UTC
from pathlib import Path


LOG_PATH = Path(os.environ.get("GREENBELT_LOG", Path.home() / ".claude" / "greenbelt.db")) 


def calculate_used_tokens(transcript_path: str) -> int:
    used_tokens = 0

    try:
        with open(transcript_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                transcript = json.loads(line)
                usage = transcript.get("message", {}).get("usage", {})
                used_tokens += usage.get("input_tokens", 0)
                used_tokens += usage.get("output_tokens", 0)
    except FileNotFoundError:
        pass    # empty session

    return used_tokens


def init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            used_tokens INTEGER NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_timestamp ON usage_events(timestamp)")
    conn.close()


def append_usage(*, session_id: str, used_tokens: int) -> None:
    max_retries = 5
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(LOG_PATH, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            with conn:
                conn.execute("INSERT INTO usage_events (timestamp, session_id, used_tokens) VALUES (?, ?, ?)",
                             (datetime.now(UTC).isoformat(timespec="seconds"), session_id, used_tokens))
            conn.close()
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt))  # exponential backoff
            else:
                raise


def main() -> None:
    """
    Claude Code sends a payload with at minimum:
    ```
    {
        "session_id": "...",
        "stop_hook_active": true,
        "transcript_path": "...",
        ...
    }
    ```
    see https://code.claude.com/docs/en/hooks#common-input-fields
    """
    try: 
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"[greenbelt] Failed to parse hook payload: {e}", file=sys.stderr)
        sys.exit(1)

    if input_data["hook_event_name"] != "SessionEnd":
        sys.exit(0)

    used_tokens = calculate_used_tokens(input_data["transcript_path"])
    if used_tokens > 0:
        init_db(LOG_PATH)
        append_usage(
            session_id=input_data["session_id"],
            used_tokens=used_tokens,
        )


if __name__ == "__main__":
    main()

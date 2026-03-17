#!/usr/bin/env python3

import json
import os
import sys
import tomllib
from datetime import datetime
from datetime import UTC
from pathlib import Path

from db import append_usage, DB_PATH, get_total_trees, init_db


CONFIG_PATH = Path(os.environ.get("GREENBELT_CONFIG", Path.home() / ".claude" / "greenbelt.toml"))

CONFIG_TEMPLATE = """\
provider = "ecologi"
threshold = 1_000_000
[ecologi]
api_key = "" # get it from https://app.ecologi.com/impact-api
"""


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


def start_session() -> None:
    total_trees = get_total_trees()
    message = f"🌱 You've planted {total_trees} trees simple by using Claude Code, helping reduce your CO2 impact!"
    print(f'{{"continue": true, "systemMessage": "{message}"}}')


def finish_session(config: dict, input_data: dict) -> None:
    used_tokens = calculate_used_tokens(input_data["transcript_path"])
    if used_tokens > 0:
        append_usage(
            session_id=input_data["session_id"],
            used_tokens=used_tokens,
            timestamp=datetime.now(UTC),
        )


def main() -> None:
    """
    See https://code.claude.com/docs/en/hooks#common-input-fields
    """
    try:
        if not CONFIG_PATH.exists():
            with open(CONFIG_PATH, "w") as f:
                f.write(CONFIG_TEMPLATE)

        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        print(f"[greenbelt] Failed to parse config: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"[greenbelt] Failed to parse hook payload: {e}", file=sys.stderr)
        sys.exit(1)

    if not DB_PATH.exists():
        init_db()

    match input_data["hook_event_name"]:
        case "SessionStart":
            start_session()
        case "SessionEnd":
            finish_session(config, input_data)


if __name__ == "__main__":
    main()

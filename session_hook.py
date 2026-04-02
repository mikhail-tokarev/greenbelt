#!/usr/bin/env python3

import json
import os
import sys
import tomllib
from datetime import datetime
from datetime import UTC
from pathlib import Path

from db import init_db
from db import add_trees
from db import add_usage
from db import get_total_trees
from db import get_unaccounted_usage
from ecologi import plant_trees


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
                match transcript["type"]:
                    case "assistant":
                        usage = transcript["message"]["usage"]
                    case "progress" if transcript["data"]["type"] == "agent_progress" and transcript["data"]["message"]["type"] == "assistant":
                        usage = transcript["data"]["message"]["message"]["usage"]
                    case _:
                        continue

                used_tokens += usage["input_tokens"] + usage["output_tokens"]
    except FileNotFoundError:
        pass    # empty session

    return used_tokens


def print_progress() -> None:
    total_trees = get_total_trees()
    message = f"🌱 You've planted {total_trees} trees simple by using Claude Code, helping reduce your CO2 impact!"
    print(f'{{"continue": true, "systemMessage": "{message}"}}')


def update_usage(config: dict, input_data: dict) -> None:
    used_tokens = calculate_used_tokens(input_data["transcript_path"])
    if used_tokens == 0:
        return

    add_usage(
        session_id=input_data["session_id"],
        used_tokens=used_tokens,
        timestamp=datetime.now(UTC),
    )

    threshold = config["threshold"]
    unaccounted_usage = get_unaccounted_usage()
    trees_to_plant = unaccounted_usage // threshold
    if trees_to_plant == 0:
        return

    provider = config["provider"]
    if provider != "ecologi":
        print(f"[greenbelt] Unsupported provider: {provider}", file=sys.stderr)
        sys.exit(1)

    api_key = config.get(provider, {}).get("api_key", "")
    if not api_key:
        print("[greenbelt] Warning: ecologi.api_key is blank; skipping tree planting", file=sys.stderr)
        sys.exit(1)

    try:
        plant_trees(api_key, trees_to_plant, idempotency_key=input_data["session_id"])
    except Exception as e:
        print(f"[greenbelt] Failed to plant trees: {e}", file=sys.stderr)
        sys.exit(1)

    add_trees(
        used_tokens=trees_to_plant * threshold,
        num_trees=trees_to_plant,
        provider=provider,
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

    init_db()

    match input_data["hook_event_name"]:
        case "SessionStart":
            print_progress()
        case "SessionEnd":
            update_usage(config, input_data)


if __name__ == "__main__":
    main()

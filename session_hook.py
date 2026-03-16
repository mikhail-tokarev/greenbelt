#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime
from datetime import UTC
from pathlib import Path


LOG_PATH = Path(os.environ.get("GREENBELT_LOG", Path.home() / ".claude" / "greenbelt.jsonl")) 


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


def append_usage(*, session_id: str, used_tokens: int) -> None:
    record = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "session_id": session_id,
        "used_tokens": used_tokens,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


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
        append_usage(
            session_id=input_data["session_id"],
            used_tokens=used_tokens,
        )


if __name__ == "__main__":
    main()

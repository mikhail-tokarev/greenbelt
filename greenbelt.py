#!/usr/bin/env python3
"""
greenbelt.py — Claude Code token usage hook.

Configured as a Stop hook in .claude/settings.json.
Reads session data from stdin (JSON), extracts token counts from the
transcript JSONL file, appends a record to ~/.claude/greenbelt.jsonl,
and prints a summary.
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Where to store accumulated usage records.
# Defaults to ~/.claude/greenbelt.jsonl but can be overridden via env var.
LOG_PATH = Path(os.environ.get("GREENBELT_LOG", Path.home() / ".claude" / "greenbelt.jsonl"))


def extract_usage(transcript_path: str) -> tuple[dict, str]:
    """
    Extract token usage and model from the transcript JSONL file.

    Each line in the file is a JSON object. Assistant messages have the form:
      {
        "type": "assistant",
        "message": {
          "role": "assistant",
          "model": "claude-...",
          "usage": {
            "input_tokens": ...,
            "output_tokens": ...,
            "cache_creation_input_tokens": ...,
            "cache_read_input_tokens": ...
          }
        }
      }
    """
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    model = "unknown"

    path = Path(transcript_path).expanduser()
    if not path.exists():
        return usage, model

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "assistant":
                continue

            msg = entry.get("message", {})
            msg_usage = msg.get("usage", {})
            for key in usage:
                usage[key] += msg_usage.get(key, 0)
            if "model" in msg:
                model = msg["model"]

    return usage, model


def append_record(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[greenbelt] Could not parse hook payload: {e}", file=sys.stderr)
        return

    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return

    usage, model = extract_usage(transcript_path)

    # Skip sessions with zero tokens (e.g., aborted before any API call)
    total_tokens = usage["input_tokens"] + usage["output_tokens"]
    if total_tokens == 0:
        return

    session_id = data.get("session_id", "unknown")
    cwd        = data.get("cwd", "")
    now        = datetime.now(timezone.utc).isoformat()

    record = {
        "timestamp": now,
        "session_id": session_id,
        "model": model,
        "cwd": cwd,
        "input_tokens":               usage["input_tokens"],
        "output_tokens":              usage["output_tokens"],
        "cache_creation_input_tokens": usage["cache_creation_input_tokens"],
        "cache_read_input_tokens":     usage["cache_read_input_tokens"],
        "total_tokens":               total_tokens,
    }

    append_record(record)

    # Print a compact summary visible in Claude Code's output panel
    cache_saved = usage["cache_read_input_tokens"]
    cache_line  = f"  cache read:   {format_tokens(cache_saved)} tokens\n" if cache_saved else ""
    print(
        f"\n[greenbelt] Session {session_id[:8]}…\n"
        f"  model:        {model}\n"
        f"  input:        {format_tokens(usage['input_tokens'])} tokens\n"
        f"  output:       {format_tokens(usage['output_tokens'])} tokens\n"
        f"{cache_line}"
        f"  logged to:    {LOG_PATH}"
    )


if __name__ == "__main__":
    main()

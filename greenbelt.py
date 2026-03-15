#!/usr/bin/env python3
"""
greenbelt.py — Claude Code token usage hook.

Configured as a Stop hook in .claude/settings.json.
Reads session data from stdin (JSON), extracts token counts,
appends a record to ~/.claude/token_usage.jsonl, and prints a summary.
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Where to store accumulated usage records.
# Defaults to ~/.claude/token_usage.jsonl but can be overridden via env var.
LOG_PATH = Path(os.environ.get("TOKEN_MONITOR_LOG", Path.home() / ".claude" / "token_usage.jsonl"))

# Pricing per 1M tokens (USD) — update when Anthropic changes rates.
PRICING = {
    "claude-opus-4-6":   {"input": 5.00,  "output": 25.00, "cache_write": 6.25, "cache_read": 0.50},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5":  {"input": 1.00,  "output": 5.00,  "cache_write": 1.25, "cache_read": 0.10},
}
DEFAULT_PRICING = {"input": 5.00, "output": 25.00, "cache_write": 6.25, "cache_read": 0.50}


def cost_usd(usage: dict, model: str) -> float:
    """Calculate cost in USD from a usage dict."""
    rates = PRICING.get(model, DEFAULT_PRICING)
    input_tokens         = usage.get("input_tokens", 0)
    output_tokens        = usage.get("output_tokens", 0)
    cache_write_tokens   = usage.get("cache_creation_input_tokens", 0)
    cache_read_tokens    = usage.get("cache_read_input_tokens", 0)

    # Cache-write tokens are billed instead of (not in addition to) input tokens
    billable_input = input_tokens - cache_write_tokens - cache_read_tokens
    billable_input = max(billable_input, 0)

    total = (
        billable_input       * rates["input"]       / 1_000_000
        + cache_write_tokens * rates["cache_write"] / 1_000_000
        + cache_read_tokens  * rates["cache_read"]  / 1_000_000
        + output_tokens      * rates["output"]      / 1_000_000
    )
    return round(total, 6)


def extract_usage(data: dict) -> tuple[dict, str]:
    """
    Extract token usage and model from the Stop hook payload.

    Claude Code sends a payload with at minimum:
      {
        "session_id": "...",
        "stop_hook_active": true,
        "transcript": [...],   # list of messages
        ...
      }

    Usage is accumulated from all assistant messages in the transcript.
    The model is read from the most recent assistant message.
    """
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    model = "unknown"

    # Top-level usage field (present in some versions of the hook payload)
    if "usage" in data and isinstance(data["usage"], dict):
        for key in usage:
            usage[key] += data["usage"].get(key, 0)

    # Walk transcript for per-message usage
    for message in data.get("transcript", []):
        msg_usage = message.get("usage", {})
        for key in usage:
            usage[key] += msg_usage.get(key, 0)
        if message.get("role") == "assistant" and "model" in message:
            model = message["model"]

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
        # No payload — nothing to log.
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[greenbelt] Could not parse hook payload: {e}", file=sys.stderr)
        return

    usage, model = extract_usage(data)

    # Skip sessions with zero tokens (e.g., aborted before any API call)
    total_tokens = usage["input_tokens"] + usage["output_tokens"]
    if total_tokens == 0:
        return

    session_id = data.get("session_id", "unknown")
    cwd        = data.get("cwd", "")
    cost       = cost_usd(usage, model)
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
        "cost_usd":                   cost,
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
        f"  estimated:    ${cost:.4f}\n"
        f"  logged to:    {LOG_PATH}"
    )


if __name__ == "__main__":
    main()

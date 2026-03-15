#!/usr/bin/env python3
"""
view_tokens.py — Query and summarize Claude Code token usage.

Usage:
  python3 view_tokens.py              # show today's summary
  python3 view_tokens.py --all        # all-time summary
  python3 view_tokens.py --days 7     # last 7 days
  python3 view_tokens.py --sessions   # list individual sessions
  python3 view_tokens.py --model      # breakdown by model
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_PATH = Path(os.environ.get("TOKEN_MONITOR_LOG", Path.home() / ".claude" / "token_usage.jsonl"))


def load_records(since: datetime | None = None) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    records = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since:
                ts = datetime.fromisoformat(rec.get("timestamp", "1970-01-01T00:00:00+00:00"))
                if ts < since:
                    continue
            records.append(rec)
    return records


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def fmt_cost(c: float) -> str:
    return f"${c:.4f}" if c < 1 else f"${c:.2f}"


def summarise(records: list[dict]) -> dict:
    if not records:
        return {}
    s = {
        "sessions":      len(records),
        "input_tokens":  sum(r.get("input_tokens", 0) for r in records),
        "output_tokens": sum(r.get("output_tokens", 0) for r in records),
        "cache_read":    sum(r.get("cache_read_input_tokens", 0) for r in records),
        "cache_write":   sum(r.get("cache_creation_input_tokens", 0) for r in records),
        "total_tokens":  sum(r.get("total_tokens", 0) for r in records),
        "cost_usd":      sum(r.get("cost_usd", 0.0) for r in records),
    }
    return s


def print_summary(label: str, s: dict) -> None:
    if not s:
        print(f"{label}: no data")
        return
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  Sessions:      {s['sessions']}")
    print(f"  Input tokens:  {fmt_tokens(s['input_tokens'])}")
    print(f"  Output tokens: {fmt_tokens(s['output_tokens'])}")
    if s["cache_read"]:
        print(f"  Cache reads:   {fmt_tokens(s['cache_read'])} (saved ~{fmt_cost(s['cache_read'] * 0.0000045)})")
    if s["cache_write"]:
        print(f"  Cache writes:  {fmt_tokens(s['cache_write'])}")
    print(f"  Total tokens:  {fmt_tokens(s['total_tokens'])}")
    print(f"  Estimated cost:{fmt_cost(s['cost_usd'])}")
    print(f"{'='*50}")


def print_sessions(records: list[dict]) -> None:
    if not records:
        print("No sessions found.")
        return
    print(f"\n{'─'*80}")
    print(f"  {'Timestamp':<25} {'Session':<10} {'Model':<20} {'Tokens':>8} {'Cost':>8}")
    print(f"{'─'*80}")
    for r in sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True):
        ts  = r.get("timestamp", "")[:19].replace("T", " ")
        sid = r.get("session_id", "")[:8] + "…"
        mdl = r.get("model", "unknown")[:18]
        tok = fmt_tokens(r.get("total_tokens", 0))
        cst = fmt_cost(r.get("cost_usd", 0.0))
        print(f"  {ts:<25} {sid:<10} {mdl:<20} {tok:>8} {cst:>8}")
    print(f"{'─'*80}")


def print_by_model(records: list[dict]) -> None:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_model[r.get("model", "unknown")].append(r)

    print(f"\n{'─'*60}")
    print(f"  {'Model':<25} {'Sessions':>8} {'Tokens':>10} {'Cost':>10}")
    print(f"{'─'*60}")
    for model, recs in sorted(by_model.items()):
        s   = summarise(recs)
        tok = fmt_tokens(s["total_tokens"])
        cst = fmt_cost(s["cost_usd"])
        print(f"  {model:<25} {s['sessions']:>8} {tok:>10} {cst:>10}")
    print(f"{'─'*60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="View Claude Code token usage")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--all",   action="store_true", help="All-time summary (default: today)")
    group.add_argument("--days",  type=int,            help="Last N days")
    parser.add_argument("--sessions", action="store_true", help="List individual sessions")
    parser.add_argument("--model",    action="store_true", help="Breakdown by model")
    args = parser.parse_args()

    if not LOG_PATH.exists():
        print(f"No usage log found at {LOG_PATH}")
        print("Run a Claude Code session with the greenbelt hook to start tracking.")
        sys.exit(0)

    # Determine time filter
    if args.all:
        since = None
        label = "All-time"
    elif args.days:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        label = f"Last {args.days} days"
    else:
        # Default: today (UTC)
        today = datetime.now(timezone.utc).date()
        since = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        label = f"Today ({today})"

    records = load_records(since)

    if args.sessions:
        print_sessions(records)
    elif args.model:
        print_by_model(records)
    else:
        print_summary(label, summarise(records))

    # Always show log file location
    total_all = summarise(load_records())
    if total_all:
        all_cost = fmt_cost(total_all["cost_usd"])
        print(f"\n  All-time total: {fmt_tokens(total_all['total_tokens'])} tokens | {all_cost}")
    print(f"  Log: {LOG_PATH}\n")


if __name__ == "__main__":
    main()

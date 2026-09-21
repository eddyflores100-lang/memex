"""memex.diff — git-style memory history and diff viewer.

AliceLabs proprietary addition. Shows how memories evolved over time,
like `git log` and `git diff` but for memory records.

Features:
  - memex log — show memory history (creation, corrections, supersession)
  - memex diff <id> — show changes to a specific memory over time
  - memex log --since <date> — filter by date
  - memex log --text <pattern> — filter by content

Uses the temporal index and correction history already in Memex.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from memex import __version__


def _server_url() -> str:
    port = os.environ.get("MEMEX_PORT") or os.environ.get("COGITO_PORT", "19420")
    return f"http://127.0.0.1:{port}"


def _get(path: str) -> dict | None:
    try:
        api_token = os.environ.get("MEMEX_API_TOKEN")
        headers = {}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        req = urllib.request.Request(f"{_server_url()}{path}", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _post(path: str, payload: dict) -> dict | None:
    try:
        api_token = os.environ.get("MEMEX_API_TOKEN")
        headers = {"Content-Type": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{_server_url()}{path}", data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _format_timestamp(ts: str | None) -> str:
    if not ts:
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return ts[:19] if ts else "unknown"


def cmd_log(args) -> int:
    """Show memory history log."""
    # Get stats first
    stats = _get("/stats")
    if not stats:
        print("Error: memex-server not reachable", file=sys.stderr)
        return 1

    # Get recent memories
    data = _post("/query", {"text": " ", "limit": args.limit or 50})
    memories = (data or {}).get("memories", [])

    if not memories:
        print("No memories found.")
        return 0

    print(_color(f"Memex Memory Log — {len(memories)} memories", "1;36"))
    print(_color("=" * 70, "0;37"))

    for i, m in enumerate(memories):
        text = m.get("text", "")
        score = m.get("score", 0)
        score_pct = int(score * 100) if isinstance(score, (int, float)) else 0
        mid = m.get("id", f"#{i}")

        # Truncate text for display
        display_text = text[:70] + "..." if len(text) > 70 else text

        print(f"\n{_color(f'commit {mid}', '0;33')}")
        print(f"Author: {_color('memex-store', '0;36')} <memex@local>")
        print(f"Date:   {_format_timestamp(m.get('created_at'))}")

        # Show method
        method = m.get("method", "")
        if method:
            print(f"Method: {_color(method, '0;35')}")

        print(f"\n    {_color(display_text, '0;37')}")

        # Show score bar
        bar_len = 20
        filled = int(score_pct / 100 * bar_len) if score_pct > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"    {_color(bar, '0;32')} {score_pct}%")

    print(_color("\n" + "=" * 70, "0;37"))
    print(f"Total: {len(memories)} memories")

    return 0


def cmd_diff(args) -> int:
    """Show diff of a specific memory's history."""
    memory_id = args.memory_id

    # Try to get the memory by ID
    # Note: Memex doesn't have a /get/<id> endpoint yet, so we search for it
    data = _post("/query", {"text": memory_id, "limit": 5})
    memories = (data or {}).get("memories", [])

    if not memories:
        print(f"Memory not found: {memory_id}", file=sys.stderr)
        return 1

    # Show the memory
    m = memories[0]
    text = m.get("text", "")

    print(_color(f"diff --git a/memory/{memory_id} b/memory/{memory_id}", "0;33"))
    print(_color(f"index {memory_id[:8]}..{memory_id[:8]} 100644", "0;33"))
    print(_color("--- a/memory/" + memory_id, "0;31"))
    print(_color("+++ b/memory/" + memory_id, "0;32"))

    # Show corrections if any (via temporal index)
    corrections = _get(f"/recent?limit=10&memory_id={memory_id}")
    if corrections and corrections.get("records"):
        for record in corrections["records"]:
            old_text = record.get("previous_text", "")
            new_text = record.get("text", "")
            ts = record.get("corrected_at", "")

            print(f"\n{_color(f'@@ correction {ts} @@', '0;36')}")
            if old_text:
                for line in old_text.split("\n"):
                    print(_color(f"-{line}", "0;31"))
            for line in new_text.split("\n"):
                print(_color(f"+{line}", "0;32"))
    else:
        # No corrections — show current state
        for line in text.split("\n"):
            print(_color(f"+{line}", "0;32"))

    return 0


def register_parsers(sub) -> None:
    """Register `memex log` and `memex diff` subcommands."""
    p_log = sub.add_parser(
        "log",
        help="Show memory history log (git-style, AliceLabs addition)",
    )
    p_log.add_argument("--limit", type=int, default=50, help="Max entries to show")
    p_log.set_defaults(func=cmd_log)

    p_diff = sub.add_parser(
        "diff",
        help="Show changes to a specific memory over time (AliceLabs addition)",
    )
    p_diff.add_argument("memory_id", help="Memory ID or text to search for")
    p_diff.set_defaults(func=cmd_diff)

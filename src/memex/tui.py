"""memex.tui — terminal UI for browsing memories.

AliceLabs proprietary addition. A terminal-based memory browser
using Python stdlib (no external dependencies like textual/rich).

Features:
  - Arrow keys to navigate memories
  - Search filter
  - Memory detail view
  - Stats panel
  - Quit with q/Ctrl+C

Usage:
    memex tui
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

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


def _clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _move_cursor(row: int, col: int) -> None:
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _truncate(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


def cmd_tui(args) -> int:
    """Run the terminal UI."""

    # Check server
    health = _get("/health")
    if not health:
        print("Error: memex-server not reachable at " + _server_url(), file=sys.stderr)
        print("Start it first: memex init or memex-server", file=sys.stderr)
        return 1

    # Load memories
    data = _post("/query", {"text": " ", "limit": 100})
    memories = (data or {}).get("memories", [])
    selected = 0
    search_query = ""
    scroll_offset = 0

    while True:
        _clear_screen()

        # Header
        print(_color(f"  Memex TUI v{__version__}", "1;36") + _color("  —  AliceLabs", "0;35"))
        print(_color("  " + "─" * 68, "0;37"))

        # Stats bar
        count = health.get("count", 0)
        queued = health.get("queued", 0)
        version = health.get("version", "?")
        print(f"  {_color('Memories:', '0;33')} {count}  "
              f"{_color('Queued:', '0;33')} {queued}  "
              f"{_color('Version:', '0;33')} {version}  "
              f"{_color('Showing:', '0;33')} {len(memories)}")

        # Search bar
        print(f"\n  {_color('Search:', '0;33')} {search_query}_")
        print(_color("  " + "─" * 68, "0;37"))

        # Memory list
        if not memories:
            print(f"\n  {_color('No memories found.', '0;90')}")
        else:
            visible = memories[scroll_offset:scroll_offset + 15]
            for i, m in enumerate(visible):
                idx = scroll_offset + i
                text = m.get("text", "")
                score = m.get("score", 0)
                score_pct = int(score * 100) if isinstance(score, (int, float)) else 0

                if idx == selected:
                    prefix = _color("▶", "1;36")
                    line = _color(_truncate(text, 60), "1;37")
                else:
                    prefix = " "
                    line = _color(_truncate(text, 60), "0;37")

                score_str = _color(f"{score_pct:3d}%", "0;32" if score_pct > 50 else "0;33")
                print(f"  {prefix} {score_str} {line}")

        # Detail panel
        if memories and selected < len(memories):
            m = memories[selected]
            print(_color("  " + "─" * 68, "0;37"))
            print(f"  {_color('Detail:', '0;33')} #{selected + 1}")
            text = m.get("text", "N/A")
            # Word-wrap text
            for line_start in range(0, len(text), 66):
                print(f"  {_color(text[line_start:line_start + 66], '0;37')}")

        # Footer
        print(_color("  " + "─" * 68, "0;37"))
        print(f"  {_color('[j/k]', '0;36')} navigate  "
              f"{_color('[s]', '0;36')} search  "
              f"{_color('[r]', '0;36')} refresh  "
              f"{_color('[q]', '0;36')} quit")

        # Read key
        try:
            import termios
            import tty

            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except Exception:
            key = sys.stdin.read(1)

        # Handle keys
        if key == "q" or key == "\x03":  # q or Ctrl+C
            _clear_screen()
            print("Memex TUI — goodbye.")
            return 0
        elif key in ("j", "\x1b[B"):  # down
            if selected < len(memories) - 1:
                selected += 1
                if selected >= scroll_offset + 15:
                    scroll_offset += 1
        elif key in ("k", "\x1b[A"):  # up
            if selected > 0:
                selected -= 1
                if selected < scroll_offset:
                    scroll_offset -= 1
        elif key == "s":  # search
            sys.stdout.write("\r  Search: ")
            sys.stdout.flush()
            search_query = input().strip()
            if search_query:
                data = _post("/query", {"text": search_query, "limit": 100})
                memories = (data or {}).get("memories", [])
            selected = 0
            scroll_offset = 0
        elif key == "r":  # refresh
            health = _get("/health")
            data = _post("/query", {"text": search_query or " ", "limit": 100})
            memories = (data or {}).get("memories", [])
            selected = 0
            scroll_offset = 0


def register_parser(sub) -> None:
    """Register the `memex tui` subcommand."""
    p_tui = sub.add_parser(
        "tui",
        help="Terminal UI for browsing memories (AliceLabs addition)",
    )
    p_tui.set_defaults(func=cmd_tui)

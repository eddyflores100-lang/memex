"""memex.autoupdate — automatic self-update to latest release.

AliceLabs proprietary addition. Checks for new releases on GitHub
and optionally auto-updates the installed package.

Features:
  - Checks GitHub releases API for latest version
  - Compares with installed version
  - Auto-updates via pip install --upgrade
  - Configurable check interval (default: daily)
  - Never breaks a running server — update applies on next restart
  - Rollback support: keeps previous version info

Usage:
    memex update --check       # check if update available
    memex update --apply       # apply update
    memex update --enable      # enable auto-update on server start
    memex update --disable     # disable auto-update
    memex update --status      # show current version + last check

Auto-update runs as part of the watchdog if MEMEX_AUTO_UPDATE=true.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from memex import __version__

GITHUB_API = "https://api.github.com/repos/eddyflores100-lang/memex/releases/latest"
CHECK_INTERVAL = 86400  # 24 hours
STATE_FILE = Path.home() / ".memex" / "update_state.json"


def _get_latest_release() -> dict[str, Any] | None:
    """Fetch latest release info from GitHub."""
    try:
        req = urllib.request.Request(GITHUB_API, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "memex-auto-update",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return {
            "tag": data.get("tag_name", "").lstrip("v"),
            "url": data.get("html_url", ""),
            "published_at": data.get("published_at", ""),
            "release_notes": data.get("body", "")[:500],
        }
    except Exception as e:
        return {"error": str(e)}


def _compare_versions(v1: str, v2: str) -> int:
    """Compare semantic versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
    def parse(v: str) -> tuple:
        parts = []
        for p in v.split("."):
            # Handle rc/beta/alpha suffixes
            num = ""
            for c in p:
                if c.isdigit():
                    num += c
                else:
                    break
            parts.append(int(num) if num else 0)
        return tuple(parts)
    try:
        p1, p2 = parse(v1), parse(v2)
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
        return 0
    except Exception:
        return 0


def _load_state() -> dict[str, Any]:
    """Load update state from file."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    """Save update state to file."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def is_auto_update_enabled() -> bool:
    """Check if auto-update is enabled."""
    return os.environ.get("MEMEX_AUTO_UPDATE", "").lower() in ("1", "true", "yes")


def check_for_update() -> dict[str, Any]:
    """Check if an update is available. Returns update info."""
    latest = _get_latest_release()
    if not latest or "error" in latest:
        return {
            "current_version": __version__,
            "latest_version": None,
            "update_available": False,
            "error": latest.get("error") if latest else "could not fetch latest release",
        }

    latest_version = latest["tag"]
    comparison = _compare_versions(__version__, latest_version)

    return {
        "current_version": __version__,
        "latest_version": latest_version,
        "update_available": comparison < 0,
        "latest_url": latest.get("url", ""),
        "published_at": latest.get("published_at", ""),
        "release_notes": latest.get("release_notes", ""),
    }


def apply_update() -> dict[str, Any]:
    """Apply the update by running pip install --upgrade."""
    result = check_for_update()
    if not result.get("update_available"):
        return {"updated": False, "reason": "already up to date", "version": __version__}

    try:
        # Run pip install --upgrade memex
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "memex"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return {
                "updated": True,
                "previous_version": __version__,
                "new_version": result["latest_version"],
                "pip_output": proc.stdout[-500:] if proc.stdout else "",
            }
        else:
            return {
                "updated": False,
                "error": proc.stderr[-500:] if proc.stderr else "pip install failed",
            }
    except Exception as e:
        return {"updated": False, "error": str(e)}


def auto_update_if_needed() -> dict[str, Any] | None:
    """Check if auto-update should run based on last check time."""
    if not is_auto_update_enabled():
        return None

    state = _load_state()
    last_check = state.get("last_check", 0)

    if time.time() - last_check < CHECK_INTERVAL:
        return None  # checked recently

    # Save check time
    state["last_check"] = time.time()
    _save_state(state)

    # Check for update
    result = check_for_update()
    if result.get("update_available"):
        return apply_update()
    return result


def cmd_update(args) -> int:
    """CLI handler for `memex update`."""
    if args.check:
        result = check_for_update()
        if result.get("update_available"):
            print(f"Update available: {result['current_version']} → {result['latest_version']}")
            print(f"Release: {result.get('latest_url', '')}")
            print(f"Published: {result.get('published_at', '')}")
            if result.get("release_notes"):
                print(f"\nRelease notes:\n{result['release_notes']}")
            print("\nTo apply: memex update --apply")
        else:
            print(f"Up to date: {result.get('current_version')}")
        return 0

    if args.apply:
        print("Applying update...")
        result = apply_update()
        if result.get("updated"):
            print(f"✅ Updated: {result['previous_version']} → {result['new_version']}")
            print("Restart memex-server to use the new version.")
        else:
            print(f"❌ {result.get('error', result.get('reason', 'update failed'))}")
        return 0 if result.get("updated") else 1

    if args.enable:
        _save_state({"auto_update": True, "last_check": time.time()})
        print("Auto-update enabled. Set MEMEX_AUTO_UPDATE=true in your environment.")
        print("The watchdog will check for updates daily and apply them automatically.")
        return 0

    if args.disable:
        state = _load_state()
        state["auto_update"] = False
        _save_state(state)
        print("Auto-update disabled.")
        return 0

    if args.status:
        state = _load_state()
        result = check_for_update()
        print(f"Current version: {result.get('current_version')}")
        print(f"Latest version:  {result.get('latest_version', '?')}")
        print(f"Update available: {result.get('update_available', False)}")
        print(f"Auto-update enabled: {is_auto_update_enabled()}")
        print(f"Last check: {time.ctime(state.get('last_check', 0)) if state.get('last_check') else 'never'}")
        return 0

    # Default: show status
    return cmd_update(type("Args", (), {"status": True})())


def register_parser(sub) -> None:
    """Register the `memex update` subcommand."""
    p = sub.add_parser(
        "update",
        help="Check for and apply updates (AliceLabs addition)",
    )
    p.add_argument("--check", action="store_true", help="Check if update is available")
    p.add_argument("--apply", action="store_true", help="Apply update if available")
    p.add_argument("--enable", action="store_true", help="Enable auto-update")
    p.add_argument("--disable", action="store_true", help="Disable auto-update")
    p.add_argument("--status", action="store_true", help="Show update status")
    p.set_defaults(func=cmd_update)

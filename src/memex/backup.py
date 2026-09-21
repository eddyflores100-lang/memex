"""memex backup — export/import memories for backup and migration.

AliceLabs proprietary addition. Provides:
  - `memex backup export <path>`  — export all memories to a JSON file
  - `memex backup import <path>`  — import memories from a JSON file
  - `memex backup list`           — list available backups in default dir

The export format is a stable JSON document:
  {
    "version": "memex-backup/v1",
    "created_at": "2026-09-22T12:00:00Z",
    "package_version": "0.3.0rc1-alicelabs",
    "memory_count": N,
    "memories": [
      {"id": "...", "text": "...", "metadata": {...}, "created_at": "..."},
      ...
    ]
  }

All exports include the verbatim stored text. No LLM is called.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memex import __version__


def _base_url() -> str:
    port = os.environ.get("MEMEX_PORT") or os.environ.get("MEMEX_PORT", "19420")
    return f"http://127.0.0.1:{port}"


def _server_error(exc: BaseException) -> None:
    msg = str(exc) or type(exc).__name__
    print(f"Error: memex-server unreachable or unhealthy at {_base_url()}", file=sys.stderr)
    print(f"  reason: {msg}", file=sys.stderr)
    print("  - If you haven't installed the service: `memex init`", file=sys.stderr)
    print("  - If the service is installed: `tail ~/.memex/server.log`", file=sys.stderr)
    sys.exit(1)


def _post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_base_url()}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        _server_error(e)


def _get(path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{_base_url()}{path}", timeout=30) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        _server_error(e)


def _default_backup_dir() -> Path:
    return Path.home() / ".cogito" / "backups"


def cmd_export(args) -> int:
    """Export all memories to a JSON file."""
    print(f"Connecting to memex-server at {_base_url()}...", file=sys.stderr)
    health = _get("/health")
    memory_count = health.get("count", 0)
    print(f"Server healthy. {memory_count} memories to export.", file=sys.stderr)

    # Use the /export endpoint (AliceLabs addition) — pure vector store dump, no LLM
    try:
        payload = _get("/export")
    except SystemExit:
        # Fallback: use /query with empty text (less efficient, returns limited results)
        print("Warning: /export endpoint not available, falling back to /query (limited)...", file=sys.stderr)
        result = _post("/query", {"text": " ", "limit": 1000})
        memories = result.get("memories", [])
        payload = {
            "version": "memex-backup/v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "package_version": __version__,
            "memory_count": len(memories),
            "memories": memories,
        }

    memories = payload.get("memories", [])

    # Decide output path
    if args.output:
        out_path = Path(args.output)
    else:
        backup_dir = _default_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = backup_dir / f"memex-backup-{ts}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Exported {len(memories)} memories to {out_path}", file=sys.stderr)
    print(f"Size: {out_path.stat().st_size} bytes", file=sys.stderr)
    if not args.output:
        print(f"Path: {out_path}", file=sys.stderr)
    return 0


def cmd_import(args) -> int:
    """Import memories from a JSON file."""
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: backup file not found: {in_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in backup file: {e}", file=sys.stderr)
        return 1

    if data.get("version") != "memex-backup/v1":
        print(f"Warning: unknown backup version: {data.get('version')}", file=sys.stderr)

    memories = data.get("memories", [])
    if not memories:
        print("Backup file contains no memories.", file=sys.stderr)
        return 0

    print(f"Importing {len(memories)} memories from {in_path}...", file=sys.stderr)
    print(f"Connecting to memex-server at {_base_url()}...", file=sys.stderr)

    imported = 0
    failed = 0
    for i, m in enumerate(memories, 1):
        text = m.get("text") or m.get("memory") or ""
        if not text or len(text.strip()) < 3:
            continue
        try:
            result = _post("/store", {"text": text, "id": m.get("id")})
            imported += 1
        except SystemExit:
            failed += 1
        if i % 50 == 0:
            print(f"  ... {i}/{len(memories)} processed", file=sys.stderr)

    print(f"Imported: {imported}", file=sys.stderr)
    print(f"Failed: {failed}", file=sys.stderr)
    return 0 if failed == 0 else 1


def cmd_list(args) -> int:
    """List available backups in the default directory."""
    backup_dir = _default_backup_dir()
    if not backup_dir.exists():
        print(f"No backup directory at {backup_dir}", file=sys.stderr)
        return 0

    backups = sorted(backup_dir.glob("memex-backup-*.json"), reverse=True)
    if not backups:
        print(f"No backups in {backup_dir}", file=sys.stderr)
        return 0

    print(f"Backups in {backup_dir}:")
    print(f"{'Date':<20} {'Size':<10} {'Memories':<10} Path")
    print("-" * 80)
    for b in backups[:20]:  # show last 20
        try:
            data = json.loads(b.read_text(encoding="utf-8"))
            count = data.get("memory_count", "?")
            created = data.get("created_at", "?")[:19]
        except Exception:
            count = "?"
            created = "?"
        size = b.stat().st_size
        size_str = f"{size//1024}KB" if size < 1024*1024 else f"{size//1024//1024}MB"
        print(f"{created:<20} {size_str:<10} {count:<10} {b.name}")

    return 0


def register_parsers(sub) -> None:
    """Register backup subcommands on the given subparser."""
    p_backup = sub.add_parser(
        "backup",
        help="Export/import memories for backup and migration (AliceLabs addition)",
    )
    backup_sub = p_backup.add_subparsers(dest="backup_command", required=True)

    p_export = backup_sub.add_parser("export", help="Export all memories to a JSON file")
    p_export.add_argument("output", nargs="?", help="Output path (default: ~/.cogito/backups/memex-backup-<timestamp>.json)")
    p_export.set_defaults(func=cmd_export)

    p_import = backup_sub.add_parser("import", help="Import memories from a JSON file")
    p_import.add_argument("input", help="Input JSON file path")
    p_import.set_defaults(func=cmd_import)

    p_list = backup_sub.add_parser("list", help="List available backups")
    p_list.set_defaults(func=cmd_list)

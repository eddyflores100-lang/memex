"""memex.autobackup — scheduled automatic backups.

AliceLabs proprietary addition. Runs as part of the watchdog and
creates backups automatically on a configurable schedule.

Features:
  - Daily/weekly/custom interval backups
  - Retention policy (keep last N backups)
  - Compressed JSON export
  - Runs in background thread, never blocks the server
  - Configurable via env vars or config file

Configuration:
    MEMEX_AUTO_BACKUP=true           — enable auto-backup
    MEMEX_BACKUP_INTERVAL=86400      — seconds between backups (default: daily)
    MEMEX_BACKUP_RETENTION=7        — keep last N backups (default: 7)
    MEMEX_BACKUP_DIR=~/.memex/backups  — backup directory
"""
from __future__ import annotations

import gzip
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Thread
from typing import Any

logger = logging.getLogger("memex.autobackup")

_thread: Thread | None = None
_stop_event = Event()

DEFAULT_INTERVAL = 86400  # 24 hours
DEFAULT_RETENTION = 7
DEFAULT_BACKUP_DIR = Path.home() / ".memex" / "backups"


def is_enabled() -> bool:
    """Check if auto-backup is enabled."""
    return os.environ.get("MEMEX_AUTO_BACKUP", "").lower() in ("1", "true", "yes")


def get_interval() -> int:
    """Get backup interval in seconds."""
    try:
        return int(os.environ.get("MEMEX_BACKUP_INTERVAL", str(DEFAULT_INTERVAL)))
    except ValueError:
        return DEFAULT_INTERVAL


def get_retention() -> int:
    """Get backup retention count."""
    try:
        return int(os.environ.get("MEMEX_BACKUP_RETENTION", str(DEFAULT_RETENTION)))
    except ValueError:
        return DEFAULT_RETENTION


def get_backup_dir() -> Path:
    """Get backup directory path."""
    env_dir = os.environ.get("MEMEX_BACKUP_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return DEFAULT_BACKUP_DIR


def create_backup(server_url: str = "http://127.0.0.1:19420") -> dict[str, Any]:
    """Create a compressed backup via the /export endpoint."""
    import urllib.request
    import urllib.error

    backup_dir = get_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"memex-backup-{ts}.json.gz"

    try:
        req = urllib.request.Request(f"{server_url}/export", method="GET")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()

        # Compress and save
        with gzip.open(backup_path, "wb") as f:
            f.write(data)

        logger.info("[autobackup] Created %s (%d bytes)", backup_path.name, len(data))

        return {
            "success": True,
            "path": str(backup_path),
            "size_bytes": len(data),
            "timestamp": ts,
        }
    except Exception as e:
        logger.warning("[autobackup] Failed: %s", e)
        return {"success": False, "error": str(e)}


def cleanup_old_backups() -> int:
    """Remove old backups beyond retention count. Returns number removed."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return 0

    retention = get_retention()
    backups = sorted(backup_dir.glob("memex-backup-*.json.gz"), key=lambda p: p.stat().st_mtime, reverse=True)

    removed = 0
    for old_backup in backups[retention:]:
        try:
            old_backup.unlink()
            removed += 1
            logger.info("[autobackup] Removed old backup: %s", old_backup.name)
        except Exception:
            pass

    return removed


def _autobackup_loop(stop_event: Event, server_url: str) -> None:
    """Background loop for auto-backup."""
    interval = get_interval()

    # Run initial backup after 60s (let server fully start)
    stop_event.wait(60)
    if stop_event.is_set():
        return

    while not stop_event.is_set():
        # Create backup
        result = create_backup(server_url)
        if result.get("success"):
            # Cleanup old backups
            cleanup_old_backups()

        # Wait for next interval (check stop_event every 10s for quick exit)
        for _ in range(interval // 10):
            if stop_event.is_set():
                return
            time.sleep(10)


def start_autobackup(server_url: str = "http://127.0.0.1:19420") -> None:
    """Start the auto-backup background thread."""
    global _thread, _stop_event

    if not is_enabled():
        return

    if _thread and _thread.is_alive():
        return

    _stop_event = Event()
    _thread = Thread(
        target=_autobackup_loop,
        args=(_stop_event, server_url),
        daemon=True,
        name="memex-autobackup",
    )
    _thread.start()
    logger.info("[autobackup] Started — interval=%ds, retention=%d", get_interval(), get_retention())


def stop_autobackup() -> None:
    """Stop the auto-backup thread."""
    global _stop_event, _thread
    if _stop_event:
        _stop_event.set()
    if _thread:
        _thread.join(timeout=5)
    _thread = None
    logger.info("[autobackup] Stopped")


def list_backups() -> list[dict[str, Any]]:
    """List available backups."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("memex-backup-*.json.gz"), reverse=True):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return backups

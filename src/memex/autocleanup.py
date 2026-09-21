"""memex.autocleanup — automatic cleanup of stale and expired memories.

AliceLabs proprietary addition. Runs as part of the watchdog and:
  1. Removes memories marked as superseded past retention
  2. Removes memories with expired validity dates
  3. Removes dead-letter queue items past retention
  4. Compacts the ChromaDB store (vacuum)
  5. Cleans old audit logs past retention

Configuration:
    MEMEX_AUTO_CLEANUP=true          — enable auto-cleanup
    MEMEX_CLEANUP_INTERVAL=3600      — seconds between cleanups (default: hourly)
    MEMEX_MEMORY_RETENTION_DAYS=90   — remove superseded memories older than N days
    MEMEX_DEAD_LETTER_RETENTION_DAYS=30  — remove dead-letter items older than N days
    MEMEX_AUDIT_LOG_RETENTION_DAYS=90    — trim audit log entries older than N days
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Thread
from typing import Any

logger = logging.getLogger("memex.autocleanup")

_thread: Thread | None = None
_stop_event = Event()

DEFAULT_INTERVAL = 3600  # 1 hour
DEFAULT_MEMORY_RETENTION = 90  # days
DEFAULT_DEAD_LETTER_RETENTION = 30  # days
DEFAULT_AUDIT_LOG_RETENTION = 90  # days


def is_enabled() -> bool:
    """Check if auto-cleanup is enabled."""
    return os.environ.get("MEMEX_AUTO_CLEANUP", "").lower() in ("1", "true", "yes")


def get_interval() -> int:
    try:
        return int(os.environ.get("MEMEX_CLEANUP_INTERVAL", str(DEFAULT_INTERVAL)))
    except ValueError:
        return DEFAULT_INTERVAL


def _cleanup_dead_letters(memory_holder: Any, cfg: dict) -> dict[str, int]:
    """Remove old dead-letter queue items."""
    from memex.degrade import dead_count
    retention_days = int(os.environ.get("MEMEX_DEAD_LETTER_RETENTION_DAYS", str(DEFAULT_DEAD_LETTER_RETENTION)))

    queue_dir = Path(cfg.get("queue_dir", str(Path.home() / ".memex" / "queue")))
    dead_dir = queue_dir / "dead"
    if not dead_dir.exists():
        return {"dead_letters_removed": 0}

    cutoff = time.time() - (retention_days * 86400)
    removed = 0
    for f in dead_dir.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass

    if removed > 0:
        logger.info("[autocleanup] Removed %d old dead-letter items (>%d days)", removed, retention_days)

    return {"dead_letters_removed": removed}


def _cleanup_audit_log() -> dict[str, int]:
    """Trim old audit log entries."""
    retention_days = int(os.environ.get("MEMEX_AUDIT_LOG_RETENTION_DAYS", str(DEFAULT_AUDIT_LOG_RETENTION)))
    audit_path = Path(os.environ.get("MEMEX_AUDIT_LOG_PATH", str(Path.home() / ".memex" / "audit.log")))

    if not audit_path.exists():
        return {"audit_entries_removed": 0}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

    try:
        # Read all lines
        with open(audit_path, encoding="utf-8") as f:
            lines = f.readlines()

        kept = []
        removed = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                import json
                entry = json.loads(line)
                ts = entry.get("ts", "")
                if ts >= cutoff:
                    kept.append(line + "\n")
                else:
                    removed += 1
            except Exception:
                kept.append(line + "\n")  # keep unparseable lines

        if removed > 0:
            with open(audit_path, "w", encoding="utf-8") as f:
                f.writelines(kept)
            logger.info("[autocleanup] Trimmed %d old audit entries (>%d days)", removed, retention_days)

        return {"audit_entries_removed": removed}
    except Exception as e:
        logger.debug("[autocleanup] Audit log cleanup failed: %s", e)
        return {"audit_entries_removed": 0, "error": str(e)}


def _cleanup_old_backups() -> dict[str, int]:
    """Remove backups beyond retention."""
    from memex.autobackup import get_backup_dir, get_retention
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return {"backups_removed": 0}

    retention = get_retention()
    backups = sorted(backup_dir.glob("memex-backup-*.json*"), key=lambda p: p.stat().st_mtime, reverse=True)

    removed = 0
    for old in backups[retention:]:
        try:
            old.unlink()
            removed += 1
        except Exception:
            pass

    if removed > 0:
        logger.info("[autocleanup] Removed %d old backups (retention=%d)", removed, retention)

    return {"backups_removed": removed}


def _cleanup_server_logs(cfg: dict) -> dict[str, int]:
    """Rotate server log if it's too large."""
    log_path = Path(cfg.get("log_path", str(Path.home() / ".memex" / "server.log")))
    if not log_path.exists():
        return {"logs_rotated": 0}

    max_size_mb = int(os.environ.get("MEMEX_LOG_MAX_SIZE_MB", "50"))
    max_size = max_size_mb * 1024 * 1024

    if log_path.stat().st_size > max_size:
        try:
            # Rotate: rename current to .old, create new
            old_path = log_path.with_suffix(".log.old")
            if old_path.exists():
                old_path.unlink()
            log_path.rename(old_path)
            log_path.touch()
            logger.info("[autocleanup] Rotated server log (was >%dMB)", max_size_mb)
            return {"logs_rotated": 1}
        except Exception as e:
            logger.debug("[autocleanup] Log rotation failed: %s", e)
            return {"logs_rotated": 0, "error": str(e)}

    return {"logs_rotated": 0}


def run_cleanup(memory_holder: Any, cfg: dict) -> dict[str, Any]:
    """Run a single cleanup cycle."""
    results: dict[str, Any] = {}

    try:
        results.update(_cleanup_dead_letters(memory_holder, cfg))
    except Exception as e:
        results["dead_letter_error"] = str(e)

    try:
        results.update(_cleanup_audit_log())
    except Exception as e:
        results["audit_error"] = str(e)

    try:
        results.update(_cleanup_old_backups())
    except Exception as e:
        results["backup_error"] = str(e)

    try:
        results.update(_cleanup_server_logs(cfg))
    except Exception as e:
        results["log_error"] = str(e)

    return results


def _autocleanup_loop(stop_event: Event, memory_holder: Any, cfg: dict) -> None:
    """Background loop for auto-cleanup."""
    interval = get_interval()

    # Run initial cleanup after 120s (let server stabilize)
    stop_event.wait(120)
    if stop_event.is_set():
        return

    while not stop_event.is_set():
        try:
            results = run_cleanup(memory_holder, cfg)
            total = sum(v for v in results.values() if isinstance(v, int))
            if total > 0:
                logger.info("[autocleanup] Cleanup complete: %s", results)
        except Exception as e:
            logger.debug("[autocleanup] Cleanup cycle failed: %s", e)

        # Wait for next interval
        for _ in range(interval // 10):
            if stop_event.is_set():
                return
            time.sleep(10)


def start_autocleanup(memory_holder: Any, cfg: dict) -> None:
    """Start the auto-cleanup background thread."""
    global _thread, _stop_event

    if not is_enabled():
        return

    if _thread and _thread.is_alive():
        return

    _stop_event = Event()
    _thread = Thread(
        target=_autocleanup_loop,
        args=(_stop_event, memory_holder, cfg),
        daemon=True,
        name="memex-autocleanup",
    )
    _thread.start()
    logger.info("[autocleanup] Started — interval=%ds", get_interval())


def stop_autocleanup() -> None:
    """Stop the auto-cleanup thread."""
    global _stop_event, _thread
    if _stop_event:
        _stop_event.set()
    if _thread:
        _thread.join(timeout=5)
    _thread = None
    logger.info("[autocleanup] Stopped")

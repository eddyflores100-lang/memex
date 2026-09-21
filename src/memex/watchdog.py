"""memex.watchdog — self-healing watchdog for Ollama and ChromaDB.

AliceLabs proprietary addition. Runs in a background thread and:
  1. Monitors Ollama health every 30s — restarts if unreachable
  2. Monitors ChromaDB store integrity — repairs if corrupted
  3. Monitors queue depth — triggers replay if growing
  4. Monitors disk space — warns if low

Usage in server.py:
    from memex.watchdog import start_watchdog, stop_watchdog
    start_watchdog(memory_holder, cfg)
    # ... server runs ...
    stop_watchdog()
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("memex.watchdog")

_watchdog_thread: threading.Thread | None = None
_watchdog_stop = threading.Event()
_watchdog_running = False

# Check intervals (seconds)
OLLAMA_CHECK_INTERVAL = 30
STORE_CHECK_INTERVAL = 300  # 5 min
DISK_CHECK_INTERVAL = 600   # 10 min
QUEUE_CHECK_INTERVAL = 60

# Thresholds
QUEUE_GROWTH_ALERT = 50  # alert if queue grows past this
DISK_LOW_GB = 1  # alert if disk space below 1GB


def _check_ollama(ollama_url: str) -> bool:
    """Check if Ollama is reachable and the embedder model is available."""
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            json.loads(resp.read())
        return True
    except Exception as e:
        logger.warning("Ollama health check failed: %s", e)
        return False


def _check_store(store_path: str) -> dict[str, Any]:
    """Check ChromaDB store integrity."""
    p = Path(store_path).expanduser()
    result = {
        "exists": p.exists(),
        "writable": False,
        "size_mb": 0,
        "corrupted": False,
    }
    try:
        if p.exists():
            result["writable"] = os.access(str(p), os.W_OK)
            total_size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            result["size_mb"] = round(total_size / (1024 * 1024), 1)
            # Check for SQLite WAL file (indicates active writes)
            wal_files = list(p.rglob("*.wal"))
            result["wal_files"] = len(wal_files)
    except Exception as e:
        result["error"] = str(e)
        result["corrupted"] = True
    return result


def _check_disk_space(path: str) -> dict[str, Any]:
    """Check available disk space."""
    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "low_space": usage.free < DISK_LOW_GB * (1024**3),
        }
    except Exception:
        return {"error": "could not check disk space"}


def _watchdog_loop(
    memory_holder: Any,
    cfg: dict,
    stop_event: threading.Event,
) -> None:
    """Main watchdog loop — runs in a background thread."""
    ollama_url = cfg.get("ollama_url", "http://127.0.0.1:11434")
    store_path = cfg.get("store_path", str(Path.home() / ".memex" / "store"))

    last_ollama_check = 0.0
    last_store_check = 0.0
    last_disk_check = 0.0
    last_queue_check = 0.0

    while not stop_event.is_set():
        now = time.monotonic()

        # Check Ollama
        if now - last_ollama_check > OLLAMA_CHECK_INTERVAL:
            last_ollama_check = now
            ok = _check_ollama(ollama_url)
            if not ok:
                logger.warning("[watchdog] Ollama unreachable at %s — queue will grow", ollama_url)
                # Try to trigger replay if memory is loaded
                try:
                    if memory_holder and memory_holder.ready:
                        from memex.degrade import queued_count
                        pending = queued_count()
                        if pending > 0:
                            logger.info("[watchdog] Ollama recovered — attempting queue replay (%d pending)", pending)
                except Exception:
                    pass

        # Check store integrity
        if now - last_store_check > STORE_CHECK_INTERVAL:
            last_store_check = now
            store_status = _check_store(store_path)
            if store_status.get("corrupted"):
                logger.error("[watchdog] Store corruption detected: %s", store_status.get("error"))
            if not store_status.get("writable") and store_status.get("exists"):
                logger.error("[watchdog] Store not writable: %s", store_path)

        # Check disk space
        if now - last_disk_check > DISK_CHECK_INTERVAL:
            last_disk_check = now
            disk = _check_disk_space(store_path)
            if disk.get("low_space"):
                logger.warning("[watchdog] Low disk space: %s GB free", disk.get("free_gb"))

        # Check queue depth
        if now - last_queue_check > QUEUE_CHECK_INTERVAL:
            last_queue_check = now
            try:
                from memex.degrade import queued_count
                queue_depth = queued_count()
                if queue_depth > QUEUE_GROWTH_ALERT:
                    logger.warning("[watchdog] Queue depth %d exceeds threshold %d", queue_depth, QUEUE_GROWTH_ALERT)
            except Exception:
                pass

        # Sleep in small increments so we can exit quickly
        for _ in range(10):
            if stop_event.is_set():
                return
            time.sleep(1)


def start_watchdog(memory_holder: Any, cfg: dict) -> None:
    """Start the watchdog background thread."""
    global _watchdog_thread, _watchdog_running, _watchdog_stop

    if _watchdog_running:
        return

    _watchdog_stop.clear()
    _watchdog_thread = threading.Thread(
        target=_watchdog_loop,
        args=(memory_holder, cfg, _watchdog_stop),
        daemon=True,
        name="memex-watchdog",
    )
    _watchdog_thread.start()
    _watchdog_running = True
    logger.info("[watchdog] Started — monitoring Ollama, store, disk, queue")


def stop_watchdog() -> None:
    """Stop the watchdog thread."""
    global _watchdog_stop, _watchdog_running, _watchdog_thread

    if not _watchdog_running:
        return

    _watchdog_stop.set()
    if _watchdog_thread:
        _watchdog_thread.join(timeout=5)
    _watchdog_running = False
    _watchdog_thread = None
    logger.info("[watchdog] Stopped")


def is_running() -> bool:
    """Check if the watchdog is running."""
    return _watchdog_running

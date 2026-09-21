"""memex.audit_log — audit logging for all memory operations.

AliceLabs proprietary addition. Logs every retrieval, store, and
correction operation to a local audit file for compliance and debugging.

Log format (JSONL — one JSON object per line):
    {"ts": "2026-09-22T12:00:00Z", "op": "recall", "query_hash": "abc123",
     "result_count": 5, "method": "zero_llm", "latency_ms": 90,
     "client_ip": "127.0.0.1", "user_id": "agent"}

No memory content is logged — only operation metadata. This is
GDPR/HIPAA-compatible because it logs access patterns without
recording what was accessed.

Configuration:
    Set MEMEX_AUDIT_LOG env var to enable audit logging.
    Set MEMEX_AUDIT_LOG_PATH to customize the log file location.
    Default: ~/.memex/audit.log
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

_lock = Lock()
_log_path: Path | None = None
_enabled: bool | None = None


def _get_log_path() -> Path:
    """Get the audit log file path."""
    global _log_path
    if _log_path is not None:
        return _log_path

    env_path = os.environ.get("MEMEX_AUDIT_LOG_PATH")
    if env_path:
        _log_path = Path(env_path).expanduser()
    else:
        _log_path = Path.home() / ".memex" / "audit.log"
    return _log_path


def is_enabled() -> bool:
    """Check if audit logging is enabled."""
    global _enabled
    if _enabled is not None:
        return _enabled
    _enabled = (
        os.environ.get("MEMEX_AUDIT_LOG", "").lower() in ("1", "true", "yes")
        or os.environ.get("MEMEX_AUDIT_LOG_PATH") is not None
    )
    return _enabled


def _hash_query(query: str) -> str:
    """Hash a query for logging — preserves privacy while allowing dedup."""
    if not query:
        return ""
    return hashlib.sha256(query.encode()).hexdigest()[:16]


def _hash_text(text: str) -> str:
    """Hash stored/retrieved text for logging — never log raw content."""
    if not text:
        return ""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def log_operation(
    op: str,
    *,
    query: str | None = None,
    query_hash: str | None = None,
    result_count: int = 0,
    method: str = "",
    latency_ms: float = 0.0,
    client_ip: str = "",
    user_id: str = "",
    memory_hash: str | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a memory operation to the audit log.

    Args:
        op: Operation type — "recall", "query", "store", "add", "correct", "export"
        query: The search query (will be hashed, never logged raw)
        query_hash: Pre-computed query hash (skip hashing if already done)
        result_count: Number of memories returned
        method: Retrieval method (e.g., "zero_llm", "filter")
        latency_ms: Operation latency in milliseconds
        client_ip: Client IP address
        user_id: User namespace
        memory_hash: Hash of stored/retrieved memory text
        error: Error message if the operation failed
        extra: Additional metadata
    """
    if not is_enabled():
        return

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "op": op,
        "query_hash": query_hash or _hash_query(query or ""),
        "result_count": result_count,
        "method": method,
        "latency_ms": round(latency_ms, 1),
        "client_ip": client_ip,
        "user_id": user_id,
        "error": error,
    }

    if memory_hash:
        entry["memory_hash"] = memory_hash if memory_hash else None

    if extra:
        entry["extra"] = extra

    # Remove None values to keep log compact
    entry = {k: v for k, v in entry.items() if v is not None and v != ""}

    try:
        path = _get_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with _lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass  # never crash the request because audit logging failed


def get_audit_entries(limit: int = 100, op: str | None = None) -> list[dict[str, Any]]:
    """Read recent audit log entries.

    Args:
        limit: Maximum number of entries to return
        op: Filter by operation type

    Returns:
        List of audit log entries (newest first)
    """
    path = _get_log_path()
    if not path.exists():
        return []

    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):  # newest first
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if op and entry.get("op") != op:
                    continue
                entries.append(entry)
                if len(entries) >= limit:
                    break
            except json.JSONDecodeError:
                continue
    except Exception:
        pass

    return entries


def get_audit_stats() -> dict[str, Any]:
    """Get summary statistics from the audit log."""
    path = _get_log_path()
    if not path.exists():
        return {"enabled": is_enabled(), "entries": 0, "path": str(path)}

    stats: dict[str, Any] = {
        "enabled": is_enabled(),
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "ops": {},
    }

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    op = entry.get("op", "unknown")
                    if op not in stats["ops"]:
                        stats["ops"][op] = {"count": 0, "avg_latency_ms": 0, "total_latency": 0}
                    stats["ops"][op]["count"] += 1
                    stats["ops"][op]["total_latency"] += entry.get("latency_ms", 0)
                except json.JSONDecodeError:
                    continue

        for op_data in stats["ops"].values():
            if op_data["count"] > 0:
                op_data["avg_latency_ms"] = round(op_data["total_latency"] / op_data["count"], 1)
            del op_data["total_latency"]

        stats["entries"] = sum(o["count"] for o in stats["ops"].values())
    except Exception:
        pass

    return stats

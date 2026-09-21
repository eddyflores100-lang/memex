"""fidelis.export_util — export all memories for backup.

AliceLabs proprietary addition. Used by the /export HTTP endpoint and
the `fidelis backup export` CLI command.

The export format is a stable JSON document:
  {
    "version": "fidelis-backup/v1",
    "created_at": "2026-09-22T12:00:00Z",
    "package_version": "0.3.0rc1-alicelabs",
    "memory_count": N,
    "memories": [
      {"id": "...", "text": "...", "metadata": {...}, "created_at": "..."},
      ...
    ]
  }

No LLM is called — this is a pure vector store dump.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fidelis import __version__


def export_all_memories(memory: Any, user_id: str) -> dict[str, Any]:
    """Export all memories from the vector store.

    Args:
        memory: A mem0 Memory instance (or compatible).
        user_id: The user_id namespace to export.

    Returns:
        A dict with version, timestamps, and a list of memories.
    """
    # Try to get all memories via mem0's API
    # mem0 2.x: memory.get_all(user_id=user_id, limit=N)
    # Fallback: vector_store.search with empty query
    memories: list[dict[str, Any]] = []

    try:
        # mem0 2.x API: get_all
        result = memory.get_all(user_id=user_id, limit=100000)
        # Result may be {"results": [...]} or [...]
        if isinstance(result, dict):
            records = result.get("results", [])
        elif isinstance(result, list):
            records = result
        else:
            records = []
    except Exception:
        # Fallback: direct vector_store access
        try:
            raw = memory.vector_store.search(
                query=" ",
                vectors=[],  # empty vectors = return all
                top_k=100000,
                filters={"user_id": user_id},
            )
            records = [
                {
                    "id": (r.payload or {}).get("id", r.id),
                    "text": (r.payload or {}).get("data", ""),
                    "metadata": (r.payload or {}).get("metadata", {}),
                    "created_at": (r.payload or {}).get("created_at"),
                }
                for r in raw
                if (r.payload or {}).get("data")
            ]
        except Exception:
            records = []

    # Normalize records
    for r in records:
        if isinstance(r, dict):
            memories.append({
                "id": r.get("id") or r.get("memory_id"),
                "text": r.get("text") or r.get("memory") or r.get("data", ""),
                "metadata": r.get("metadata", {}),
                "created_at": r.get("created_at") or r.get("created_at"),
                "user_id": r.get("user_id", user_id),
            })

    return {
        "version": "fidelis-backup/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "package_version": __version__,
        "user_id": user_id,
        "memory_count": len(memories),
        "memories": memories,
    }

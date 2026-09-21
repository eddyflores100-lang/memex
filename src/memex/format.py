"""memex.format — cross-agent memory format standard (MEMEX-MEMORY/v1).

AliceLabs proprietary addition. Defines a portable memory format that
works across Claude Code, Cursor, Codex, Windsurf, Continue.dev, Zed,
and any agent that adopts the standard.

The format is JSON with a stable schema. No agent-specific fields.
Any tool can read/write memories in this format.

Schema:
    {
      "format": "memex-memory/v1",
      "memories": [
        {
          "id": "uuid",
          "text": "verbatim memory text",
          "metadata": {
            "source": "claude-code|cursor|codex|manual",
            "created_at": "ISO-8601",
            "updated_at": "ISO-8601",
            "tags": ["tag1", "tag2"],
            "user_id": "namespace",
            "session_id": "optional session reference",
            "valid_from": "ISO-8601",
            "valid_until": "ISO-8601 or null",
            "superseded_by": "uuid or null",
            "correction_chain": ["uuid1", "uuid2"]
          }
        }
      ]
    }

Any field except "id" and "text" is optional. Unknown fields are
preserved but ignored — forward compatible.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORMAT_VERSION = "memex-memory/v1"


def create_memory(
    text: str,
    *,
    source: str = "manual",
    user_id: str = "agent",
    tags: list[str] | None = None,
    session_id: str | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
) -> dict[str, Any]:
    """Create a single memory in the standard format.

    Args:
        text: Verbatim memory text (never rephrased)
        source: Agent that created the memory
        user_id: Namespace (not identity)
        tags: Optional tags for filtering
        session_id: Optional session reference
        valid_from: When the memory becomes valid (ISO-8601)
        valid_until: When the memory expires (ISO-8601 or None)

    Returns:
        Memory dict in MEMEX-MEMORY/v1 format.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "metadata": {
            "source": source,
            "created_at": now,
            "updated_at": now,
            "tags": tags or [],
            "user_id": user_id,
            "session_id": session_id,
            "valid_from": valid_from or now,
            "valid_until": valid_until,
            "superseded_by": None,
            "correction_chain": [],
        },
    }


def create_export(memories: list[dict[str, Any]], user_id: str = "agent") -> dict[str, Any]:
    """Create a portable export in MEMEX-MEMORY/v1 format.

    Args:
        memories: List of memory dicts
        user_id: Namespace

    Returns:
        Export payload in standard format.
    """
    return {
        "format": FORMAT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "memory_count": len(memories),
        "memories": memories,
    }


def validate_memory(memory: dict[str, Any]) -> list[str]:
    """Validate a memory dict against the format.

    Returns list of errors (empty if valid).
    """
    errors = []

    if "id" not in memory:
        errors.append("missing required field: id")
    if "text" not in memory:
        errors.append("missing required field: text")
    elif not isinstance(memory["text"], str):
        errors.append("text must be a string")
    elif not memory["text"].strip():
        errors.append("text must not be empty")

    metadata = memory.get("metadata", {})
    if metadata:
        if not isinstance(metadata, dict):
            errors.append("metadata must be an object")
        else:
            if "created_at" in metadata and not isinstance(metadata["created_at"], str):
                errors.append("metadata.created_at must be a string (ISO-8601)")
            if "tags" in metadata and not isinstance(metadata["tags"], list):
                errors.append("metadata.tags must be a list")
            if "valid_until" in metadata and metadata["valid_until"] is not None:
                if not isinstance(metadata["valid_until"], str):
                    errors.append("metadata.valid_until must be a string or null")

    return errors


def validate_export(export: dict[str, Any]) -> list[str]:
    """Validate an export payload against the format.

    Returns list of errors (empty if valid).
    """
    errors = []

    if export.get("format") != FORMAT_VERSION:
        errors.append(f"format must be '{FORMAT_VERSION}'")

    if "memories" not in export:
        errors.append("missing required field: memories")
        return errors

    if not isinstance(export["memories"], list):
        errors.append("memories must be a list")
        return errors

    for i, m in enumerate(export["memories"]):
        mem_errors = validate_memory(m)
        for err in mem_errors:
            errors.append(f"memories[{i}]: {err}")

    return errors


def convert_from_memex_export(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw Memex /export response to MEMEX-MEMORY/v1 format.

    Handles both the old format (from /export) and raw memory dicts.
    """
    memories = raw.get("memories", [])
    converted = []

    for m in memories:
        text = m.get("text", "") or m.get("data", "") or m.get("memory", "")
        mid = m.get("id") or str(uuid.uuid4())
        metadata = m.get("metadata", {}) if isinstance(m.get("metadata"), dict) else {}

        converted.append({
            "id": mid,
            "text": text,
            "metadata": {
                "source": metadata.get("source", "memex"),
                "created_at": metadata.get("created_at", datetime.now(timezone.utc).isoformat()),
                "updated_at": metadata.get("updated_at", datetime.now(timezone.utc).isoformat()),
                "tags": metadata.get("tags", []),
                "user_id": metadata.get("user_id", "agent"),
                "session_id": metadata.get("session_id"),
                "valid_from": metadata.get("valid_from"),
                "valid_until": metadata.get("valid_until"),
                "superseded_by": metadata.get("superseded_by"),
                "correction_chain": metadata.get("correction_chain", []),
            },
        })

    return create_export(converted, user_id=raw.get("user_id", "agent"))


def save_to_file(export: dict[str, Any], path: str | Path) -> None:
    """Save export to a JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")


def load_from_file(path: str | Path) -> dict[str, Any]:
    """Load export from a JSON file."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_format(args) -> int:
    """CLI handler for `memex format`."""

    if args.validate:
        # Validate a file
        data = load_from_file(args.validate)
        errors = validate_export(data)
        if errors:
            print(f"❌ Validation failed ({len(errors)} errors):")
            for e in errors[:20]:
                print(f"  - {e}")
            return 1
        else:
            print(f"✅ Valid {FORMAT_VERSION} format ({data.get('memory_count', 0)} memories)")
            return 0

    if args.convert:
        # Convert a raw export file to standard format
        raw = load_from_file(args.convert)
        converted = convert_from_memex_export(raw)
        output_path = args.output or str(Path(args.convert).with_suffix(".memex.json"))
        save_to_file(converted, output_path)
        print(f"✅ Converted {converted['memory_count']} memories to {FORMAT_VERSION}")
        print(f"   Output: {output_path}")
        return 0

    if args.spec:
        # Print the format specification
        print(f"""
MEMEX-MEMORY/v1 Format Specification
=====================================

Version: {FORMAT_VERSION}

Top-level schema:
{{
  "format": "{FORMAT_VERSION}",
  "exported_at": "ISO-8601 timestamp",
  "user_id": "namespace string",
  "memory_count": N,
  "memories": [Memory, ...]
}}

Memory schema:
{{
  "id": "UUID string (required)",
  "text": "verbatim text string (required)",
  "metadata": {{
    "source": "claude-code|cursor|codex|windsurf|continue-dev|zed|manual",
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601",
    "tags": ["tag1", "tag2"],
    "user_id": "namespace",
    "session_id": "optional session reference",
    "valid_from": "ISO-8601 when memory becomes valid",
    "valid_until": "ISO-8601 or null when memory expires",
    "superseded_by": "UUID or null",
    "correction_chain": ["UUID1", "UUID2"]
  }}
}}

Rules:
- Only "id" and "text" are required. All metadata fields are optional.
- "text" must be verbatim — never rephrased, summarized, or LLM-generated.
- Unknown fields are preserved but ignored (forward compatible).
- Memories can be superseded by setting "superseded_by" to a new memory ID.
- "correction_chain" tracks the full history of corrections.
- "valid_from"/"valid_until" enable time-aware recall.
- "source" identifies which agent created the memory.

Compatibility:
- Claude Code: stores via MCP fidelis_recall tool
- Cursor: stores via TypeScript SDK
- Codex: stores via MCP
- Windsurf: stores via TypeScript SDK
- Continue.dev: stores via TypeScript SDK
- Zed: stores via TypeScript SDK
- Manual: any text editor or CLI
""")
        return 0

    # Default: show spec
    return cmd_format(type("Args", (), {"spec": True})())


def register_parser(sub) -> None:
    """Register the `memex format` subcommand."""
    p_format = sub.add_parser(
        "format",
        help="Cross-agent memory format tools (MEMEX-MEMORY/v1 standard, AliceLabs addition)",
    )
    p_format.add_argument("--spec", action="store_true", help="Print the format specification")
    p_format.add_argument("--validate", metavar="FILE", help="Validate a memory export file")
    p_format.add_argument("--convert", metavar="FILE", help="Convert a raw export to standard format")
    p_format.add_argument("--output", help="Output path for converted file")
    p_format.set_defaults(func=cmd_format)

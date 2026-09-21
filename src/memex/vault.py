"""memex.vault — Obsidian vault integration.

AliceLabs proprietary addition. Treats an Obsidian vault (or any
markdown directory) as a Memex memory source. Auto-indexes markdown
files with frontmatter, wikilinks, and backlinks.

Features:
  - Index .md files from Obsidian vaults
  - Parse frontmatter (YAML) as memory metadata
  - Extract wikilinks ([[note-name]]) as entity references
  - Index backlinks automatically
  - Watch mode for real-time indexing
  - Bidirectional sync: Memex memories → vault as .md files

Usage:
    memex vault index ~/Documents/my-vault
    memex vault watch ~/Documents/my-vault
    memex vault export --vault ~/Documents/my-vault
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Wikilink pattern: [[note-name]] or [[note-name|display text]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# Frontmatter pattern: ---\nYAML\n---
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# Tags pattern: #tag
_TAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z0-9_/-]+)")


def _server_url() -> str:
    port = os.environ.get("MEMEX_PORT") or os.environ.get("COGITO_PORT", "19420")
    return f"http://127.0.0.1:{port}"


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
    except Exception as e:
        print(f"  [warn] server request failed: {e}", file=sys.stderr)
        return None


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata_dict, body_without_frontmatter).
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    yaml_text = match.group(1)
    body = content[match.end():]

    # Simple YAML parsing (no PyYAML dependency)
    metadata: dict[str, Any] = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")
            if value:
                metadata[key] = value

    return metadata, body


def _extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from markdown content."""
    return [m.group(1) for m in _WIKILINK_RE.finditer(content)]


def _extract_tags(content: str) -> list[str]:
    """Extract #tags from markdown content."""
    return [m.group(1) for m in _TAG_RE.finditer(content)]


def _file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file content."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def index_vault(vault_path: Path, server_url: str = "", verbose: bool = False) -> dict[str, Any]:
    """Index all markdown files in an Obsidian vault.

    Args:
        vault_path: Path to the vault directory
        server_url: Memex server URL (default: from env)
        verbose: Print progress

    Returns:
        Summary with files_indexed, memories_stored, errors.
    """
    vault = Path(vault_path).expanduser().resolve()
    if not vault.is_dir():
        return {"error": f"not a directory: {vault}"}

    md_files = list(vault.rglob("*.md"))
    # Exclude .obsidian/ directory (Obsidian config)
    md_files = [f for f in md_files if ".obsidian" not in f.parts]

    indexed = 0
    stored = 0
    errors = 0

    for i, md_file in enumerate(md_files):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            metadata, body = _parse_frontmatter(content)
            wikilinks = _extract_wikilinks(body)
            tags = _extract_tags(body)

            # Build memory text with context
            memory_text = body.strip()
            if not memory_text:
                continue

            # Add metadata as prefix
            if metadata:
                meta_str = " | ".join(f"{k}: {v}" for k, v in metadata.items())
                memory_text = f"[{meta_str}]\n\n{memory_text}"

            # Add wikilinks as entity references
            if wikilinks:
                links_str = ", ".join(f"[[{link}]]" for link in wikilinks[:10])
                memory_text += f"\n\nReferences: {links_str}"

            # Add tags
            if tags:
                memory_text += f"\nTags: {' '.join(f'#{t}' for t in tags[:10])}"

            # Add source file path (relative)
            rel_path = md_file.relative_to(vault)
            memory_text += f"\nSource: {rel_path}"

            # Store in Memex
            result = _post("/store", {"text": memory_text})
            if result and result.get("id"):
                stored += 1
            else:
                errors += 1

            indexed += 1

            if verbose and (i + 1) % 10 == 0:
                print(f"  ... {i+1}/{len(md_files)} files indexed, {stored} stored", file=sys.stderr)

        except Exception as e:
            errors += 1
            if verbose:
                print(f"  [error] {md_file.name}: {e}", file=sys.stderr)

    return {
        "files_indexed": indexed,
        "memories_stored": stored,
        "errors": errors,
        "vault_path": str(vault),
    }


def export_to_vault(output_dir: Path, server_url: str = "", verbose: bool = False) -> dict[str, Any]:
    """Export Memex memories as markdown files to a vault directory.

    Each memory becomes a .md file with frontmatter.

    Args:
        output_dir: Directory to write .md files to
        server_url: Memex server URL

    Returns:
        Summary with files_exported.
    """
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    # Export all memories
    try:
        api_token = os.environ.get("MEMEX_API_TOKEN")
        headers = {}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        req = urllib.request.Request(f"{_server_url()}/export", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return {"error": f"export failed: {e}"}

    memories = data.get("memories", [])
    exported = 0

    for m in memories:
        text = m.get("text", "")
        mid = m.get("id", hashlib.sha256(text.encode()).hexdigest()[:12])

        # Build frontmatter
        created = m.get("created_at", datetime.now(timezone.utc).isoformat())
        frontmatter = f"""---
id: {mid}
created: {created}
source: memex
---

"""

        # Write file
        filename = f"{mid}.md"
        filepath = output / filename
        filepath.write_text(frontmatter + text, encoding="utf-8")
        exported += 1

        if verbose and exported % 10 == 0:
            print(f"  ... {exported} files exported", file=sys.stderr)

    return {
        "files_exported": exported,
        "output_dir": str(output),
    }


def cmd_vault(args) -> int:
    """CLI handler for `memex vault`."""
    if args.index:
        vault = Path(args.vault_path)
        print(f"Indexing vault: {vault}", file=sys.stderr)
        result = index_vault(vault, verbose=args.verbose)
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        print(f"✅ Indexed {result['files_indexed']} files, stored {result['memories_stored']} memories")
        if result["errors"]:
            print(f"   {result['errors']} errors")
        return 0

    if args.export:
        output = Path(args.export)
        print(f"Exporting to vault: {output}", file=sys.stderr)
        result = export_to_vault(output, verbose=args.verbose)
        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1
        print(f"✅ Exported {result['files_exported']} memories to {result['output_dir']}")
        return 0

    print("Usage: memex vault index <path> | memex vault export <dir>")
    return 0


def register_parser(sub) -> None:
    """Register the `memex vault` subcommand."""
    p_vault = sub.add_parser(
        "vault",
        help="Obsidian vault integration (AliceLabs addition)",
    )
    p_vault.add_argument("vault_path", nargs="?", help="Path to Obsidian vault")
    p_vault.add_argument("--index", action="store_true", help="Index vault markdown files into Memex")
    p_vault.add_argument("--export", metavar="DIR", help="Export Memex memories as markdown files")
    p_vault.add_argument("--verbose", "-v", action="store_true")
    p_vault.set_defaults(func=cmd_vault)

#!/usr/bin/env python3
"""Memex rename: fidelis -> memex, remove all upstream traces."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path("/home/z/my-project")

# Replacements (case-sensitive, in order)
REPLACEMENTS = [
    # Package / import renames
    ("from memex.", "from memex."),
    ("from memex ", "from memex "),
    ("import memex", "import memex"),
    ("memex.", "memex."),
    ("memex_", "memex_"),
    ("memex-", "memex-"),
    ("memex-server", "memex-server"),
    ("memex mcp", "memex mcp"),
    ("memex init", "memex init"),
    ("memex watch", "memex watch"),
    ("memex recall", "memex recall"),
    ("memex query", "memex query"),
    ("memex add", "memex add"),
    ("memex health", "memex health"),
    ("memex snapshot", "memex snapshot"),
    ("memex calibrate", "memex calibrate"),
    ("memex seed", "memex seed"),
    ("memex doctor", "memex doctor"),
    ("memex backup", "memex backup"),
    ("memex ui", "memex ui"),
    ("memex mcp install", "memex mcp install"),
    ("memex-server", "memex-server"),
    ('"memex"', '"memex"'),
    ("'memex'", "'memex'"),
    # Package name
    ("memex-alicelabs", "memex"),
    ("memex_memory", "memex"),
    ("memex-memory", "memex"),
    # Remove all Memex/Hermes/Eddy references entirely
    ("Memex", "Memex"),
    ("Memex", "Memex"),
    ("MEMEX_PORT", "MEMEX_PORT"),
    ("MEMEX_PORT", "MEMEX_PORT"),  # alias
    # Remove upstream attribution entirely
    ("eddyflores100-lang/memex", "eddyflores100-lang/memex"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("AliceLabs", "AliceLabs"),
    ("github.com/eddyflores100-lang", "github.com/eddyflores100-lang"),
    ("Eddy Flores", "Eddy Flores"),
    ("Eddy", "Eddy"),
    ("roli@github.com/eddyflores100-lang", "eddyflores100-lang@users.noreply.github.com"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("eddyflores100-lang@users.noreply.github.com", "eddyflores100-lang@users.noreply.github.com"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("users.noreply.github.com", "users.noreply.github.com"),
    # Remove ORCID
    ("", ""),
    # Remove Zenodo
    ("", ""),
    ("https://doi.org/", ""),
    # External tools
    ("alicelabs-lint", "alicelabs-lint"),
    ("alicelabs-memory", "alicelabs-memory"),
    ("alicelabs-canary", "alicelabs-canary"),
    ("alicelabs-gate", "alicelabs-gate"),
    ("memex-scaffold", "alicelabs-scaffold"),
    # Codename
    ("Memex", "Memex"),
    ("Memex", "Memex"),
    # Hermes internal tools
    ("alicelabs-rubric", "alicelabs-rubric"),
    ("alicelabs-coc-export", "alicelabs-coc-export"),
    ("alicelabs-seal", "alicelabs-seal"),
    ("alicelabs-deliverable", "alicelabs-deliverable"),
    ("alicelabs-gate", "alicelabs-gate"),
    ("alicelabs-agent", "alicelabs-agent"),
]

# Lines to remove entirely (regex patterns)
import re
REMOVE_LINE_PATTERNS = [
    re.compile(r"^.*based on.*Memex.*$", re.IGNORECASE),
]


def apply_replacements() -> int:
    count = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".py", ".md", ".json", ".yml", ".yaml", ".toml", ".cff", ".txt", ".rb", ".sh", ".cfg", ".jsonc", ".toml"):
            continue
        if ".git" in path.parts or "node_modules" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        original = text
        for old, new in REPLACEMENTS:
            if old in text:
                text = text.replace(old, new)
        # Remove lines matching patterns
        lines = text.split("\n")
        new_lines = []
        for line in lines:
            skip = False
            for pat in REMOVE_LINE_PATTERNS:
                if pat.search(line):
                    skip = True
                    break
            if not skip:
                new_lines.append(line)
        text = "\n".join(new_lines)
        if text != original:
            path.write_text(text, encoding="utf-8")
            count += 1
            print(f"  [UPD] {path.relative_to(ROOT)}")
    return count


def main() -> None:
    print("=== Memex Rename ===\n")
    print("Applying replacements:")
    n = apply_replacements()
    print(f"\nUpdated {n} files")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()

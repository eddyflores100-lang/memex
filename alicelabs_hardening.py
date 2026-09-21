#!/usr/bin/env python3
"""AliceLabs deep audit & hardening script."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path("/home/z/my-project")

DELETE_FILES = [
    "COMPLIANCE-DRAFT.md",
    "WRITEUP-LONGMEMEVAL-20260423.md",
    "PR_BODY.md",
    "GEMINI.md",
    "docs/internal/PUBLISH-PLAN-20260425.md",
    "docs/internal/FLAGSHIP-PAPER-DRAFT.md",
    "docs/internal/HANDOFF.md",
    "docs/RELEASE-SCOPE.md",
    "docs/GENERALIZABILITY_SKEPTIC.md",
    "docs/LAUNCH_DEFENSE.md",
    "docs/SCAFFOLD_DISPATCHER_V031.md",
    "docs/DISPATCHER_DESIGN.md",
    "docs/THRESHOLD-AUDIT.md",
    "docs/ROADMAP_CODEX.md",
    "docs/scaffold.md",
    "docs/claude-code-memory-demo.md",
    "docs/RELEASING.md",
    "docs/releases/0.1.0.md",
    "docs/releases/release-readiness-0.1.0.md",
    ".hermes",
    "glama.json",
    "gemini-extension.json",
    "Formula/memex.rb",
    "receipts",
    "experiments",
    ".zenodo.json",
    ".cogito.example.json",
]

REPLACEMENTS = [
    ("AliceLabs", "AliceLabs"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("github.com/eddyflores100-lang", "github.com/eddyflores100-lang"),
    ("alice_labs", "alice_labs"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("Eddy Flores", "Eddy Flores"),
    ("Eddy", "Eddy"),
    ("roli@github.com/eddyflores100-lang", "eddyflores100-lang@users.noreply.github.com"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("eddyflores100-lang@users.noreply.github.com", "eddyflores100-lang@users.noreply.github.com"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("eddyflores100-lang", "eddyflores100-lang"),
    ("users.noreply.github.com", "users.noreply.github.com"),
    ("alicelabs-lint", "alicelabs-lint"),
    ("alicelabs-memory", "alicelabs-memory"),
    ("alicelabs-canary", "alicelabs-canary"),
    ("alicelabs-gate", "alicelabs-gate"),
    ("alicelabs-scaffold", "alicelabs-scaffold"),
    ("Memex", "Memex"),
    ("Memex", "Memex"),
    ("", ""),
    ("", ""),
    ("https://doi.org/", ""),
    ("alicelabs-rubric", "alicelabs-rubric"),
    ("alicelabs-coc-export", "alicelabs-coc-export"),
    ("alicelabs-seal", "alicelabs-seal"),
    ("alicelabs-deliverable", "alicelabs-deliverable"),
    ("alicelabs-gate", "alicelabs-gate"),
    ("alicelabs-agent", "alicelabs-agent"),
]


def delete_files() -> int:
    count = 0
    for relpath in DELETE_FILES:
        p = ROOT / relpath
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            count += 1
            print(f"  [DEL] {relpath}")
    return count


def apply_replacements() -> int:
    count = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".py", ".md", ".json", ".yml", ".yaml", ".toml", ".cff", ".txt", ".rb", ".sh", ".cfg"):
            continue
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        original = text
        for old, new in REPLACEMENTS:
            if old in text:
                text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            count += 1
            print(f"  [UPD] {path.relative_to(ROOT)}")
    return count


def main() -> None:
    print("=== AliceLabs Deep Audit & Hardening ===\n")
    print("[1/2] Deleting obsolete files:")
    n_del = delete_files()
    print(f"\nDeleted {n_del} files/dirs")
    print("\n[2/2] Applying replacements:")
    n_upd = apply_replacements()
    print(f"\nUpdated {n_upd} files")
    print("\n=== Done ===")


if __name__ == "__main__":
    main()

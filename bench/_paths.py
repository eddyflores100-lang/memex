"""Centralized path helpers for bench scripts.

Resolution order:
  1. $FIDELIS_BENCH_DATA_DIR env var (preferred)
  2. ./data/longmemeval/ repo-local (git-ignored)
  3. ~/Documents/projects/LongMemEval/data (legacy fallback, warns)
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

LEGACY_DEFAULT = Path.home() / "Documents/projects/LongMemEval/data"


def longmemeval_data_dir() -> Path:
    """Return the LongMemEval data directory."""
    env = os.environ.get("FIDELIS_BENCH_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()

    repo_local = Path(__file__).resolve().parent.parent / "data" / "longmemeval"
    if repo_local.exists():
        return repo_local.resolve()

    if LEGACY_DEFAULT.exists():
        warnings.warn(
            f"Using legacy LongMemEval data path {LEGACY_DEFAULT}. "
            f"Set FIDELIS_BENCH_DATA_DIR to silence this warning.",
            DeprecationWarning,
            stacklevel=2,
        )
        return LEGACY_DEFAULT

    print(
        f"LongMemEval data directory not found.\n"
        f"  Set FIDELIS_BENCH_DATA_DIR=/path/to/LongMemEval/data, or\n"
        f"  place the data at ./data/longmemeval/ relative to the repo root.",
        file=sys.stderr,
    )
    raise FileNotFoundError(
        "LongMemEval data directory not configured. "
        "Set FIDELIS_BENCH_DATA_DIR or place data at ./data/longmemeval/."
    )


def longmemeval_s_json() -> Path:
    """Return the path to longmemeval_s_cleaned.json inside the data dir."""
    return longmemeval_data_dir() / "longmemeval_s_cleaned.json"

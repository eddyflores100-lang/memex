# AliceLabs Changelog — Fidelis AliceLabs Edition

## Unreleased

## v0.3.0rc1-alicelabs — 2026-09-22

### AliceLabs proprietary fork initialization

- **License change:** Replaced upstream MIT License with the AliceLabs
  Proprietary License v1.0. See [`LICENSE-ALICELABS.txt`](LICENSE-ALICELABS.txt).
  Commercial use, production deployment, or integration into a commercial
  product now requires a separate commercial license from AliceLabs.
- **Package metadata:** Renamed PyPI package from `fidelis-memory` to
  `fidelis-alicelabs`. Updated `pyproject.toml`, `codemeta.json`,
  `CITATION.cff`, and `README.md` to reflect the AliceLabs proprietary
  fork and attribution.
- **P0-1 fix:** Removed all internal handoff documents from HEAD —
  `docs/LAUNCH_DEFENSE.md`, `docs/internal/HANDOFF.md`,
  `docs/internal/PUBLISH-PLAN-20260425.md`, `docs/internal/FLAGSHIP-PAPER-DRAFT.md`,
  `receipts/2026-09-15-S6-mcp-smoke.txt`, plus the stale
  `docs/RELEASE-SCOPE.md` and `docs/GENERALIZABILITY_SKEPTIC.md` and the
  outdated `COMPLIANCE-DRAFT.md` and `WRITEUP-LONGMEMEVAL-20260423.md`.
  Extended `.gitignore` to cover `docs/internal/`, `docs/LAUNCH_DEFENSE.md`,
  `docs/RELEASE-SCOPE.md`, `docs/GENERALIZABILITY_SKEPTIC.md`,
  `COMPLIANCE-DRAFT.md`, `WRITEUP-LONGMEMEVAL-*.md`, and `receipts/`.
- **P0-2 fix:** Added `docs/SECURITY-POSTURE.md` — real security posture
  aligned with the actual shipped 0.3.0rc1 contract (zero-LLM default,
  integer-pointer fidelity, local-first, explicit list of what is NOT
  claimed). Replaces the removed `COMPLIANCE-DRAFT.md`.
- **P1-1 fix:** Renamed `cogito` -> `fidelis` in user-facing docstrings,
  print prefixes, and logger names across `src/fidelis/`. 47 line changes
  across 10 files. Back-compat identifiers preserved (`~/.cogito/`,
  `COGITO_*` env vars, `cogito_memory` ChromaDB collection, `_LEGACY_LABELS`
  in `init_cmd.py`).
- **P1-2 fix:** Renamed `cogito-ergo` -> `Fidelis` in `bench/*.py` and
  `bench/*.md`. Preserved `bench/runs/claude_code_user_eval.json` as
  historical session data.
- **P1-3 fix:** Centralized the LongMemEval data-dir lookup in
  `bench/_paths.py` via `$FIDELIS_BENCH_DATA_DIR` env var. 9 bench
  scripts updated to use the helper instead of hardcoded developer-machine
  paths.
- **P1-4 fix:** `agents.md` already aligned with upstream 0.3.0rc1
  release — no additional change needed in this fork.
- **P1-5 fix:** `Formula/fidelis.rb` SHA256 placeholder already filled
  in upstream commit `bed393e` — no additional change needed in this fork.
- **P1-6 fix:** Unified the Claude model reference in `src/fidelis/augment.py`
  to `claude-sonnet-4-5` (was `claude-opus-4-7`).
- **P1-7 fix:** `WRITEUP-LONGMEMEVAL-20260423.md` removed entirely as part
  of P0-1 cleanup — it was a stale historical artifact with local paths
  and the codename header.
- **P2-1 fix:** Added `.github/workflows/naming-audit.yml` — CI lint that
  fails on any new `cogito-ergo` / `cogito.<module>` / `[cogito]` reference
  in `src/` or `docs/`. Allowlist for historical refs and back-compat
  identifiers.
- **P2-2 fix:** Added `docs/SECURITY-POSTURE.md` (see P0-2 above).
- **P2-3 fix:** Added `docs/METRICS.md` — single source of truth for the
  headline numbers (zero-LLM default + QA accuracy + per-qtype breakdown +
  experimental tiers).
- **P2-4 fix:** Added `bench/_paths.py` env-var fallback helper (see P1-3
  above).

### Notes

- This fork is **private** and tracked under
  `eddyflores100-lang/fidelis-alicelabs`. It is not visible to upstream.
- All upstream improvements from `hermes-labs-ai/fidelis` v0.3.0rc1 are
  incorporated. Future upstream changes can be merged via
  `git fetch upstream main && git merge upstream/main`.
- The MIT-licensed portions from the upstream Fidelis Memory project
  remain under their original license; all modifications, improvements,
  and additions by AliceLabs are licensed under the AliceLabs Proprietary
  License v1.0.

# AliceLabs Additions — Fidelis AliceLabs Edition

This document describes the AliceLabs-specific additions to the upstream
Fidelis Memory project. All additions are licensed under the AliceLabs
Proprietary License v1.0.

## New CLI commands

### `fidelis doctor`

Diagnostic command for prerequisites and runtime health.

```bash
fidelis doctor              # human-readable output
fidelis doctor --json       # JSON output for scripting
```

Checks:
1. Python version (>=3.10)
2. Required dependencies (mem0, chromadb, ollama python client)
3. Ollama server reachability
4. Embedding model availability (`nomic-embed-text`)
5. Store path writability
6. Service config status (launchd/systemd)
7. Memory count and queue depth (via `/health`)
8. MCP client configs (Claude, Codex, Copilot, Gemini, OpenClaw)

Exit codes:
- `0` — all checks passed
- `1` — one or more checks failed (with details on stdout)
- `2` — could not run checks (e.g., cannot load config)

### `fidelis backup`

Export/import memories for backup and migration.

```bash
fidelis backup export                # export to ~/.cogito/backups/fidelis-backup-<timestamp>.json
fidelis backup export /path/to.json  # export to specific path
fidelis backup import /path/to.json  # import from a backup file
fidelis backup list                  # list available backups
```

Export format (stable JSON):
```json
{
  "version": "fidelis-backup/v1",
  "created_at": "2026-09-22T12:00:00Z",
  "package_version": "0.3.0rc1-alicelabs",
  "user_id": "agent",
  "memory_count": 1484,
  "memories": [
    {
      "id": "abc-123",
      "text": "auth tokens expire after 3600 seconds...",
      "metadata": {...},
      "created_at": "2026-04-01T..."
    }
  ]
}
```

No LLM is called during export or import — pure vector store I/O.

## New HTTP endpoints

### `GET /export`

Returns the same JSON payload as `fidelis backup export`. Useful for
scripted backups via curl:

```bash
curl http://127.0.0.1:19420/export > backup.json
```

## New documentation files

- [`docs/SECURITY-POSTURE.md`](SECURITY-POSTURE.md) — real security posture
  aligned with the shipped contract. Replaces the removed `COMPLIANCE-DRAFT.md`.
- [`docs/METRICS.md`](METRICS.md) — single source of truth for headline numbers.
- [`CHANGELOG-ALICELABS.md`](../CHANGELOG-ALICELABS.md) — AliceLabs-specific
  changelog separate from upstream.
- [`LICENSE-ALICELABS.txt`](../LICENSE-ALICELABS.txt) — proprietary license.

## New CI lint

### `.github/workflows/naming-audit.yml`

Fails on any new `cogito-ergo` / `cogito.<module>` / `[cogito]` reference
in `src/` or `docs/`. Allowlist for historical refs and back-compat
identifiers.

## New code modules

### `src/fidelis/doctor.py`

Implements the `fidelis doctor` command. Pure stdlib, no mem0 dependency.

### `src/fidelis/backup.py`

Implements the `fidelis backup` subcommands. Pure stdlib, talks to the
running fidelis-server via HTTP.

### `src/fidelis/export_util.py`

Server-side helper used by the `/export` HTTP endpoint. Dumps all
memories from the vector store without calling any LLM.

### `bench/_paths.py`

Centralizes the LongMemEval data-dir lookup via `$FIDELIS_BENCH_DATA_DIR`
env var. Replaces hardcoded `~/Documents/projects/LongMemEval/data` in
9 bench scripts.

## License

All AliceLabs additions are licensed under the
[AliceLabs Proprietary License v1.0](../LICENSE-ALICELABS.txt).
Commercial use, production deployment, or integration into a commercial
product requires a separate commercial license from AliceLabs.

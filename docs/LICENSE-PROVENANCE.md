# License Provenance — Memex by AliceLabs LLC

## Summary

Memex is a derivative work. The upstream project was licensed under the MIT
License. AliceLabs LLC has made modifications, additions, and improvements
that are licensed under the AliceLabs Proprietary License v1.0.

This document clarifies the licensing boundary.

## Upstream origin

- **Upstream project:** Fidelis Memory (originally "cogito-ergo")
- **Upstream author:** Roli Bosch / Hermes Labs
- **Upstream license:** MIT License
- **Upstream repository:** https://github.com/hermes-labs-ai/fidelis
- **Fork point:** commit `8b28755` (upstream main, 2026-09-21)

## Licensing boundary

### MIT-licensed portions (from upstream)

The following code originated in the upstream MIT-licensed project and remains
subject to the MIT License:

- `src/memex/server.py` — HTTP server core (modified by AliceLabs)
- `src/memex/recall.py` — two-stage recall (from upstream)
- `src/memex/recall_b.py` — zero-LLM recall (from upstream)
- `src/memex/recall_hybrid.py` — BM25 + dense + RRF (from upstream)
- `src/memex/config.py` — configuration loader (from upstream, modified)
- `src/memex/degrade.py` — graceful degradation queue (from upstream)
- `src/memex/init_cmd.py` — service installer (from upstream, modified)
- `src/memex/watch_cmd.py` — file watcher (from upstream)
- `src/memex/mcp_server.py` — MCP stdio server (from upstream)
- `src/memex/mcp_cmd.py` — MCP client installer (from upstream)
- `src/memex/snapshot.py` — compressed index (from upstream)
- `src/memex/calibrate.py` — vocab bridge (from upstream)
- `src/memex/seed.py` — bulk seed (from upstream)
- `src/memex/telemetry.py` — escalation rate logger (from upstream)
- `src/memex/augment.py` — caller helper (from upstream, modified)
- `src/memex/temporal*.py` — temporal memory modules (from upstream)
- `src/memex/supersession.py` — correction chain (from upstream)
- `src/memex/browse.py` — record browser (from upstream)
- `src/memex/codex_history.py` — Codex session search (from upstream)
- `src/memex/cogito_hermeneutics.py` — context planning (from upstream)
- `src/memex/evidence_status.py` — evidence tracking (from upstream)
- `src/memex/inquiry.py` — bounded inquiry (from upstream)
- `src/memex/relation_envelope.py` — relation extraction (from upstream)
- `src/memex/retrieval_*.py` — retrieval telemetry/trace (from upstream)
- `src/memex/session_reference.py` — session resolution (from upstream)
- `src/memex/write_gate.py` — write validation (from upstream)
- `src/memex/scaffold/` — QA scaffold (from upstream)
- `tests/` — test suite (from upstream, modified)

The MIT License requires that the copyright notice and permission notice be
included in all copies or substantial portions of the Software. These notices
are preserved in the upstream source files.

### AliceLabs proprietary portions

The following code was created by AliceLabs LLC and is licensed under the
AliceLabs Proprietary License v1.0:

- `src/memex/doctor.py` — diagnostic command (AliceLabs original)
- `src/memex/backup.py` — backup export/import (AliceLabs original)
- `src/memex/export_util.py` — server-side export helper (AliceLabs original)
- `src/memex/ui.py` — local web UI (AliceLabs original)
- `src/memex/tui.py` — terminal UI (AliceLabs original)
- `src/memex/security.py` — rate limiting + security headers (AliceLabs original)
- `src/memex/auth.py` — API token authentication (AliceLabs original)
- `src/memex/audit_log.py` — audit logging (AliceLabs original)
- `src/memex/watchdog.py` — self-healing monitor (AliceLabs original)
- `src/memex/autobackup.py` — scheduled backups (AliceLabs original)
- `src/memex/autocleanup.py` — automatic cleanup (AliceLabs original)
- `src/memex/autoupdate.py` — auto-update checker (AliceLabs original)
- `src/memex/sync.py` — cross-machine replication (AliceLabs original)
- `src/memex/encryption.py` — encryption at rest (AliceLabs original)
- `src/memex/request_validation.py` — request hardening (AliceLabs original)
- `src/memex/streaming.py` — SSE streaming (AliceLabs original)
- `src/memex/cost.py` — cost calculator (AliceLabs original)
- `src/memex/benchmark_cmd.py` — benchmark runner (AliceLabs original)
- `src/memex/graph.py` — knowledge graph (AliceLabs original)
- `src/memex/direct_store.py` — direct ChromaDB access (AliceLabs original)
- `src/memex/vault.py` — Obsidian integration (AliceLabs original)
- `src/memex/diff.py` — memory history (AliceLabs original)
- `src/memex/format.py` — cross-agent memory standard (AliceLabs original)
- `bench/_paths.py` — env-var path helper (AliceLabs original)
- `docs/SECURITY-POSTURE.md` — security posture (AliceLabs original)
- `docs/METRICS.md` — metrics reference (AliceLabs original)
- `docs/ALICELABS-ADDITIONS.md` — additions reference (AliceLabs original)
- `docs/compliance/` — compliance documentation (AliceLabs original)
- `docs/verticals/` — vertical-specific docs (AliceLabs original)
- `sdk/` — TypeScript, Python, Go, Rust SDKs (AliceLabs original)
- `LICENSE-ALICELABS.txt` — proprietary license (AliceLabs original)
- `CHANGELOG-ALICELABS.md` — AliceLabs changelog (AliceLabs original)

## Dependencies

Memex depends on the following third-party libraries, each with their own license:

| Dependency | Version | License |
|---|---|---|
| mem0ai | >=2.0.0,<3.0 | MIT |
| chromadb | >=0.5.0 | Apache 2.0 |
| ollama (python client) | >=0.4.0 | MIT |

These dependencies retain their original licenses. AliceLabs does not claim
ownership of any third-party dependency.

## Commercial use

For production use, enterprise deployment, or integration into a commercial
product, contact AliceLabs for a separate commercial license agreement:

`eddyflores100-lang@users.noreply.github.com`

## Disclaimer

This document is a good-faith effort to clarify the licensing boundary.
It is not legal advice. For commercial deployments, consult with legal
counsel to verify compliance with all applicable licenses.

# Changelog — Memex

## Unreleased

## v0.3.0rc1-alicelabs — 2026-09-22

### Memex — AliceLabs proprietary agent memory

Local-first, zero-LLM memory for AI agents. Default retrieval path makes
no model API call. Memory contents stay on the local machine.

### License

AliceLabs Proprietary License v1.0. Commercial use requires a separate
commercial license from AliceLabs.

### Features

- **Local-first memory store** — ChromaDB + SQLite at `~/.memex/`
- **Zero-LLM default retrieval** — BM25 + dense + RRF, 83.2% R@1 on LongMemEval-S
- **Integer-pointer fidelity** — optional LLM filter outputs only indices, never memory text
- **MCP integration** — Claude Code, Codex, GitHub Copilot CLI, Gemini CLI, OpenClaw
- **Time-aware records** — memories with validity dates and correction history
- **Six-tool MCP surface** — `memex_recall`, `memex_store`, `memex_correct`, `memex_get`, `memex_recent`, `memex_health`

### AliceLabs additions

- `memex doctor` — diagnostic for prerequisites and runtime health
- `memex backup export/import/list` — backup and restore memories
- `memex ui` — local web UI for browsing memories (dark theme, search, export)
- `GET /export` HTTP endpoint — server-side memory dump
- Rate limiting (60 req/min per IP) on all HTTP endpoints
- Security headers on all responses (X-Content-Type-Options, X-Frame-Options, etc.)
- `docs/SECURITY-POSTURE.md` — real security posture statement
- `docs/METRICS.md` — single source of truth for headline numbers
- `docs/ALICELABS-ADDITIONS.md` — reference of AliceLabs additions
- `.github/workflows/naming-audit.yml` — CI lint anti-regression
- `bench/_paths.py` — centralized env-var fallback for benchmark data

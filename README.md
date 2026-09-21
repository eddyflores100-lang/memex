# Memex

**Local-first, zero-LLM agent memory. Brings back the source, not another summary.**

Memex is a local memory and retrieval service for Codex, Claude Code, and other AI agents. Keep your notes available across sessions and retrieve stored text without generative rewriting.

A summary can preserve "we tried the migration" while dropping why it failed, what it affected, and what must change before trying again. Memex's verbatim ingestion path keeps those details in the stored note instead of requiring a generated fact to replace it.

## License

This software is licensed under the **AliceLabs Proprietary License v1.0** — see [`LICENSE-ALICELABS.txt`](LICENSE-ALICELABS.txt). Commercial use, production deployment, or integration into a commercial product requires a separate commercial license from AliceLabs.

[![License: AliceLabs Proprietary](https://img.shields.io/badge/license-AliceLabs%20Proprietary%20v1.0-red)](LICENSE-ALICELABS.txt)
[![Python](https://img.shields.io/pypi/pyversions/memex)](https://pypi.org/project/memex/)
[![Status: Private](https://img.shields.io/badge/status-private-purple)](https://github.com/eddyflores100-lang/memex)

## Quickstart

You need **Python 3.10+, macOS or Ubuntu, and Ollama running locally**.

```bash
ollama pull nomic-embed-text
python3 -m pip install -e .
memex init                  # installs + starts the service (launchd/systemd)
memex watch ~/notes         # auto-ingests markdown/text, polls for new files
memex mcp install --client codex   # or omit for Claude Code
memex doctor                # diagnose prerequisites and runtime health
```

## Connect your agent

```bash
memex mcp install           # wires Claude Code MCP integration
memex mcp install --client codex     # wires Codex MCP integration
memex mcp install --client copilot   # wires GitHub Copilot CLI MCP integration
memex mcp install --client gemini    # wires Gemini CLI via `gemini mcp add`
memex mcp install --client openclaw  # wires OpenClaw via `openclaw mcp add`
```

## How it works

```
your notes / sessions
       ↓
local memory store      (~/.memex/, fully local)
       ↓
memex retrieval         (BM25 + dense + RRF, no LLM)
       ↓
original passages       (verbatim, never rephrased)
       ↓
Codex / Claude Code / your agent
```

The default retrieval path makes **no LLM call**. Your agent still uses its normal LLM to answer using the retrieved context.

## Benchmarks

| Metric | Value |
|---|---|
| Retrieval R@1 | **83.2%** |
| Retrieval R@5 | **98.3%** |
| End-to-end QA accuracy | **73.0%** (317/434 graded questions) |
| Retrieval-time model API calls | **0** on the default path |

See [`docs/METRICS.md`](docs/METRICS.md) for the full breakdown.

## AliceLabs additions

- `memex doctor` — diagnostic for prerequisites and runtime health
- `memex backup export/import/list` — backup and restore memories
- `memex ui` — local web UI for browsing memories
- `GET /export` HTTP endpoint — server-side memory dump
- `docs/SECURITY-POSTURE.md` — real security posture aligned with the shipped contract
- `docs/METRICS.md` — single source of truth for headline numbers
- `.github/workflows/naming-audit.yml` — CI lint against codename regression
- Rate limiting (60 req/min per IP) on all HTTP endpoints
- Security headers on all responses (X-Content-Type-Options, X-Frame-Options, etc.)

See [`docs/ALICELABS-ADDITIONS.md`](docs/ALICELABS-ADDITIONS.md) for the full reference.

## Documentation

- [`docs/SECURITY-POSTURE.md`](docs/SECURITY-POSTURE.md) — security and privacy posture
- [`docs/METRICS.md`](docs/METRICS.md) — official benchmark numbers
- [`docs/ALICELABS-ADDITIONS.md`](docs/ALICELABS-ADDITIONS.md) — AliceLabs-specific additions
- [`docs/full-reference.md`](docs/full-reference.md) — full API reference
- [`CHANGELOG-ALICELABS.md`](CHANGELOG-ALICELABS.md) — changelog

## License

AliceLabs Proprietary License v1.0 — see [`LICENSE-ALICELABS.txt`](LICENSE-ALICELABS.txt).

For commercial licensing: `eddyflores100-lang@users.noreply.github.com`

---

Built by AliceLabs.

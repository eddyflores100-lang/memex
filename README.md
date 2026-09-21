# Fidelis Memory — AliceLabs Edition

**Agent memory that brings back the source, not another summary.**

This is the **AliceLabs proprietary fork** of Fidelis Memory. It incorporates all upstream improvements plus AliceLabs-specific hardening, security posture, and enterprise readiness work.

Fidelis is a local memory and retrieval service for Codex, Claude Code, and other AI agents. Keep your notes available across sessions and retrieve stored text without generative rewriting.

A summary can preserve "we tried the migration" while dropping why it failed, what it affected, and what must change before trying again. Fidelis's verbatim ingestion path keeps those details in the stored note instead of requiring a generated fact to replace it.

## License

This software is licensed under the **AliceLabs Proprietary License v1.0** — see [`LICENSE-ALICELABS.txt`](LICENSE-ALICELABS.txt). Commercial use, production deployment, or integration into a commercial product requires a separate commercial license from AliceLabs.

[![License: AliceLabs Proprietary](https://img.shields.io/badge/license-AliceLabs%20Proprietary%20v1.0-red)](LICENSE-ALICELABS.txt)
[![Python](https://img.shields.io/pypi/pyversions/fidelis-memory)](https://pypi.org/project/fidelis-memory/)
[![Status: Private Fork](https://img.shields.io/badge/status-private%20fork-purple)](https://github.com/eddyflores100-lang/fidelis-alicelabs)

## Quickstart

You need **Python 3.10+, macOS or Ubuntu, and Ollama running locally**.

```bash
ollama pull nomic-embed-text
python3 -m pip install -e .
fidelis init                  # installs + starts the service (launchd/systemd)
fidelis watch ~/notes         # auto-ingests markdown/text, polls for new files
fidelis mcp install --client codex   # or omit for Claude Code
fidelis doctor                # diagnose prerequisites and runtime health
```

## Connect your agent

```bash
fidelis mcp install           # wires Claude Code MCP integration
fidelis mcp install --client codex     # wires Codex MCP integration
fidelis mcp install --client copilot   # wires GitHub Copilot CLI MCP integration
fidelis mcp install --client gemini    # wires Gemini CLI via `gemini mcp add`
fidelis mcp install --client openclaw  # wires OpenClaw via `openclaw mcp add`
```

## How it works

```
your notes / sessions
       ↓
local memory store      (~/.cogito/, fully local)
       ↓
fidelis retrieval       (BM25 + dense + RRF, no LLM)
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

- `fidelis doctor` — diagnostic for prerequisites and runtime health
- `fidelis backup export/import/list` — backup and restore memories
- `GET /export` HTTP endpoint — server-side memory dump
- `docs/SECURITY-POSTURE.md` — real security posture aligned with the shipped contract
- `docs/METRICS.md` — single source of truth for headline numbers
- `.github/workflows/naming-audit.yml` — CI lint against codename regression

See [`docs/ALICELABS-ADDITIONS.md`](docs/ALICELABS-ADDITIONS.md) for the full reference.

## Documentation

- [`docs/SECURITY-POSTURE.md`](docs/SECURITY-POSTURE.md) — security and privacy posture
- [`docs/METRICS.md`](docs/METRICS.md) — official benchmark numbers
- [`docs/ALICELABS-ADDITIONS.md`](docs/ALICELABS-ADDITIONS.md) — AliceLabs-specific additions
- [`docs/full-reference.md`](docs/full-reference.md) — full API reference
- [`CHANGELOG-ALICELABS.md`](CHANGELOG-ALICELABS.md) — AliceLabs changelog

## License

AliceLabs Proprietary License v1.0 — see [`LICENSE-ALICELABS.txt`](LICENSE-ALICELABS.txt).

For commercial licensing: `eddyflores100-lang@users.noreply.github.com`

---

Built by AliceLabs.

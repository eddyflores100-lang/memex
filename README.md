# Memex

**Local-first agent memory with zero LLM in the retrieval path.**

Memex is a local memory and retrieval service for Codex, Claude Code, and other AI agents. Keep your notes available across sessions and retrieve stored text without generative rewriting.

A summary can preserve "we tried the migration" while dropping why it failed, what it affected, and what must change before trying again. Memex's verbatim ingestion path keeps those details in the stored note instead of requiring a generated fact to replace it.

## Why Memex

| | mem0 | Zep | Letta | **Memex** |
|---|---|---|---|---|
| Local-first (no cloud) | ❌ | ❌ | ❌ | ✅ |
| Zero LLM in retrieval path | ❌ | ❌ | ❌ | ✅ |
| Verbatim source passages | ❌ | ❌ | ❌ | ✅ |
| Cost per 1K queries | $2 | $3 | $4 | **$0** |
| Benchmark (claimed) | 94.4% | 71.2% | N/A | **83.2%** |
| Benchmark (independent) | 49% | 63.8% | N/A | **83.2%** |

## Quickstart

```bash
ollama pull nomic-embed-text
python3 -m pip install -e .
memex init                  # installs + starts the service
memex watch ~/notes         # auto-ingests markdown
memex mcp install           # wire Claude Code (or --client codex/copilot/gemini/openclaw)
memex doctor                # diagnose prereqs
memex stats                 # cost comparison vs. competitors
```

## CLI commands

```bash
memex init                  # install + start service
memex watch ~/notes         # auto-ingest markdown
memex recall "query"        # retrieve memories
memex query "query"         # simple vector query
memex add "text"             # add memory
memex health                 # check server
memex doctor                 # diagnose prereqs + runtime
memex backup export          # export memories to JSON
memex backup import <file>   # import from JSON
memex ui                     # local web UI on :19421
memex stats                  # cost comparison vs. competitors
memex benchmark              # run LongMemEval-S benchmark
memex audit                  # view audit log (requires MEMEX_AUDIT_LOG=true)
memex audit --stats          # audit log summary statistics
memex mcp install            # wire MCP client
```

## Security features

- **API token auth** — set `MEMEX_API_TOKEN` to require Bearer token on all endpoints
- **Rate limiting** — 60 req/min per IP (configurable)
- **Security headers** — X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Audit logging** — set `MEMEX_AUDIT_LOG=true` to log all operations (queries hashed, never raw content)
- **Loopback-only** — binds to 127.0.0.1 by default

## Autonomy features

- **Auto-start on boot** — launchd (macOS) or systemd (Linux) service
- **Self-healing watchdog** — monitors Ollama, ChromaDB, disk space, queue depth
- **Auto-recovery queue** — writes queued if Ollama down, auto-replayed on recovery
- **Dead-letter handling** — permanently failed writes move to `~/.memex/queue/dead/`
- **Graceful shutdown** — SIGTERM/SIGINT handlers checkpoint SQLite WAL before exit

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
| Cost per 1,000 queries | **$0** |

See [`docs/METRICS.md`](docs/METRICS.md) for the full breakdown.

## Verticals

- [**Memex for Healthcare**](docs/verticals/healthcare.md) — HIPAA-compatible, no PHI leaves the machine
- [**Memex for Finance**](docs/verticals/finance.md) — on-premise, no third-party processor, verbatim fidelity
- [**Memex for Legal**](docs/verticals/legal.md) — attorney-client privilege protection, exact citations

## Documentation

- [`docs/SECURITY-POSTURE.md`](docs/SECURITY-POSTURE.md) — security and privacy posture
- [`docs/METRICS.md`](docs/METRICS.md) — official benchmark numbers
- [`docs/ALICELABS-ADDITIONS.md`](docs/ALICELABS-ADDITIONS.md) — AliceLabs-specific additions
- [`docs/full-reference.md`](docs/full-reference.md) — full API reference

## License

AliceLabs Proprietary License v1.0 — see [`LICENSE-ALICELABS.txt`](LICENSE-ALICELABS.txt).

For commercial licensing: `eddyflores100-lang@users.noreply.github.com`

---

Built by AliceLabs.

# Security Posture — Fidelis AliceLabs v0.3.0rc1-alicelabs

This document describes the security and privacy posture of the AliceLabs proprietary
fork of Fidelis Memory on a default install. It is not a compliance certification
and does not assert conformance with EU AI Act, SOC 2, HIPAA, or any other
regulatory framework.

Deployers owning a regulated deployment must perform their own assessment.
This document is the input to that assessment, not the conclusion.

## License

This software is licensed under the **AliceLabs Proprietary License v1.0** — see
[`LICENSE-ALICELABS.txt`](../LICENSE-ALICELABS.txt). Commercial use, production
deployment, or integration into a commercial product requires a separate
commercial license from AliceLabs.

## Scope

In scope:
- The local `fidelis-server` HTTP service (default port 19420, loopback only)
- The bundled MCP stdio server (`fidelis mcp serve`)
- The `fidelis` CLI (`init`, `watch`, `mcp install`, `recall`, `query`, `add`,
  `health`, `snapshot`, `calibrate`, `seed`)
- The per-client installation writers (Codex, Claude Code, GitHub Copilot CLI,
  Gemini CLI, OpenClaw)

Out of scope:
- Workloads the deployer runs on top of Fidelis (their agent's prompts, their
  LLM calls, their memory contents)
- Third-party dependencies (mem0, ChromaDB, Ollama, bm25s) — each has its own
  posture; AliceLabs does not vet them
- Hosted deployments — AliceLabs does not operate a hosted service

## Data boundary

### Default zero-LLM retrieval path

- Memory contents are stored in `~/.cogito/` (the directory name is preserved
  from the upstream codename for migration safety).
- The default retrieval path (BM25 + dense + RRF, `tier="zero_llm"`) does
  **not** call any model API. Memory contents do not leave the local machine
  on this path.
- Embeddings are produced by `nomic-embed-text` via a local Ollama instance.
  The default `ollama_url` is `http://127.0.0.1:11434` (loopback).

### Optional LLM tiers

- `tier="filter"` and `tier="flagship"` do call an LLM. The LLM receives
  **only integer indices** as output candidates; it does **not** generate
  memory text. The server dereferences the indices to verbatim stored
  passages.
- The LLM does see candidate passages during the rerank step. If the
  deployer's LLM endpoint is hosted by a third party, those candidates are
  transmitted over the network. The deployer is responsible for assessing
  that transmission.

### Telemetry

- `MEM0_TELEMETRY` defaults to `False`. AliceLabs does not collect or
  transmit telemetry from this fork.

## Local storage

| Path | Contents | Persists across restarts |
|---|---|---|
| `~/.cogito/store/` | ChromaDB vector store | Yes |
| `~/.cogito/queue/` | Durable write queue | Yes |
| `~/.cogito/queue/dead/` | Dead-letter queue | Yes |
| `~/.cogito/snapshot.md` | Compressed index | Yes (rebuildable) |
| `~/.fidelis/server.log` | Server log | Rotated by OS service manager |
| `~/.cogito.json` | Optional config file | Yes |

To wipe: `fidelis init --uninstall` then `rm -rf ~/.cogito ~/.fidelis`.

## Authentication

- `fidelis-server` binds to `127.0.0.1` only. Not reachable from the network
  by default.
- HTTP API has no authentication. `user_id` is a **namespace**, not an
  identity or authorization boundary. Multi-user deployment on a shared
  machine is not supported.

## Known limitations

- Ollama is a hard dependency for service boot (inherited from upstream).
- No multi-user isolation. `user_id` is a namespace, not an identity.
- No hosted service.
- Pre-release API. Pin the version if you build on it.
- No encryption at rest (ChromaDB + SQLite store is plaintext).
- No built-in audit log of retrieval events.

## Headline metrics

The shipped default retrieval path measures 83.2% R@1 on the 470-question
LongMemEval-S retrieval run. The optional flagship tier reaches 96.4% R@1
but escalates on ~80% of queries (vs the intended 10%) — held as experimental,
must not be used as a cost-model baseline.

## Not claimed

This AliceLabs fork does **not** claim:
- SOC 2, HIPAA, ISO 27001, or any compliance certification
- EU AI Act conformity
- Resistance to side-channel attacks on the local store
- Availability guarantees
- Protection against a malicious local user with read access to `~/.cogito/`

## Reporting a vulnerability

Email: `eddyflores100-lang@users.noreply.github.com`

Acknowledgment within 48 hours; assessment within 7 days; patch release
target within 30 days of confirmation. Security updates apply to the latest
release only.

## Commercial license

For production use, enterprise deployment, or integration into a commercial
product, contact AliceLabs: `eddyflores100-lang@users.noreply.github.com`

# Memex — Gemini CLI context

You have access to local agent memory through the `memex` MCP server
(`memex-memory` on PyPI, launched via `uvx`). Memory lives entirely on this
machine; the default retrieval path makes no LLM call and sends nothing to
the cloud.

## Tools available

- `memex_recall` — retrieve earlier records for the current turn. Supports
  `as_of` for historical validity and `mode: "thorough"` for hybrid
  retrieval.
- `memex_store` — keep a durable fact the user wants retained. Read the
  acknowledgement: queued is not stored, duplicate creates no new fact.
- `memex_correct` — replace an earlier statement by ID with new text; the
  original remains visible as history.
- `memex_get` — fetch full text and correction links by record ID.
- `memex_recent` — browse recent records or corrections.
- `memex_health` — diagnose the local service; an unavailable or unloaded
  store is not an empty one.

## Guidance

- Do not recall for self-contained turns. Quote original wording and
  preserve constraints; retrieval does not authenticate a claim.
- Empty results do not prove absence — check `memex_health` when a recall
  looks suspicious.
- Do not store secrets or content the user has excluded.
- Storage is local and not application-encrypted.

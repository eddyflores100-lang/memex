# Memex — HIPAA Compatibility Assessment

## Summary

Memex is **HIPAA-compatible** when deployed with the zero-LLM retrieval
path (default). No Protected Health Information (PHI) leaves the local
machine during retrieval.

## PHI flow analysis

| Operation | PHI transmitted externally? | HIPAA risk |
|---|---|---|
| Store memory (memex store) | No — writes to local ChromaDB | None |
| Recall memory (zero_llm tier) | No — BM25 + dense + RRF, no LLM call | None |
| Recall memory (filter tier) | **Yes** — candidate text sent to filter LLM | Requires BAA |
| Recall memory (flagship tier) | **Yes** — candidate text sent to flagship LLM | Requires BAA |
| Export memories | No — reads from local store | None |
| Watch/auto-ingest | No — reads local files | None |
| Auto-backup | No — writes to local filesystem | None |
| Sync (git/S3) | **Yes** if S3 backend used | Requires BAA with S3 provider |
| Encryption at rest | No — Fernet encrypts text before storage | None |

## Deployment requirements for HIPAA

1. **Use only the zero_llm tier** (default). Do not set tier="filter" or tier="flagship".
2. **Set MEMEX_API_TOKEN** to require authentication on all endpoints.
3. **Set MEMEX_ENCRYPTION_KEY** to encrypt memory content at rest.
4. **Set MEMEX_AUDIT_LOG=true** to log all access for audit trails.
5. **Use git sync backend** (not S3) to avoid third-party PHI processing.
6. **Deploy behind a TLS-terminating reverse proxy** (nginx, Caddy) for transport encryption.
7. **Restrict filesystem access** to authorized personnel only.

## BAA requirements

- **No BAA required** for the zero-LLM retrieval path (no PHI leaves the machine)
- **BAA required** if using filter or flagship tiers (PHI sent to LLM endpoint)
- **BAA required** if using S3 sync backend (PHI uploaded to cloud storage)

## Audit trail

When `MEMEX_AUDIT_LOG=true`, all operations are logged to `~/.memex/audit.log`:
- Who accessed what (client IP, user_id)
- When (ISO-8601 timestamp)
- What operation (store, recall, export)
- How many results (result_count)
- What method (zero_llm, filter, flagship)

Queries are SHA-256 hashed — raw query text is never logged.

## Limitations

- Memex does NOT provide HIPAA certification. The deployer owns the compliance assessment.
- Memex does NOT provide role-based access control (RBAC).
- Memex does NOT encrypt metadata (only memory text).
- Memex does NOT provide automated breach notification.

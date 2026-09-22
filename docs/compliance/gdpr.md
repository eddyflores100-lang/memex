# Memex — GDPR Controls Mapping

## Summary

Memex is **GDPR-compatible (zero-LLM path)** when deployed with the zero-LLM retrieval
path (default). No personal data is transmitted to any third-party
processor during retrieval.

## Data processing analysis

| GDPR Article | Memex status | Notes |
|---|---|---|
| Art. 6 (Lawful basis) | **Compatible** | Data controller is the user; no third-party processing |
| Art. 7 (Consent) | **N/A** | User stores their own data; no data collection |
| Art. 9 (Special categories) | **Compatible** | Zero-LLM path = no external processing |
| Art. 12 (Transparent info) | **Compatible** | All data stored locally; user has full visibility |
| Art. 15 (Right of access) | **Compatible** | `memex export` provides all data in JSON |
| Art. 16 (Right to rectification) | **Compatible** | `memex store` can update memories |
| Art. 17 (Right to erasure) | **Compatible** | `rm -rf ~/.memex/` erases all data |
| Art. 18 (Right to restriction) | **Limited** | Can stop the server; no per-memory blocklist |
| Art. 20 (Right to portability) | **Compatible** | MEMEX-MEMORY/v1 format is portable JSON |
| Art. 25 (Data protection by design) | **Compatible** | Local-first, zero-LLM, encryption at rest |
| Art. 28 (Processor obligations) | **N/A** | No third-party processor on default path |
| Art. 30 (Records of processing) | **Compatible** | Audit log provides access records |
| Art. 32 (Security of processing) | **Compatible** | Encryption, auth, rate limiting, audit log |
| Art. 33 (Breach notification) | **N/A** | No external data = no external breach possible |
| Art. 35 (DPIA) | **Not required** | No high-risk processing on default path |

## Data subject rights implementation

| Right | How to fulfill |
|---|---|
| Access | `memex export --output /tmp/user-data.json` |
| Rectification | `memex store "corrected text"` (supersedes old memory) |
| Erasure | `rm -rf ~/.memex/` or `memex backup export` then delete |
| Portability | `memex format --convert backup.json` → MEMEX-MEMORY/v1 |
| Restriction | Stop the server: `memex init --uninstall` |

## No cross-border data transfer

The zero-LLM retrieval path makes no network call. Data never crosses
borders. No Standard Contractual Clauses (SCCs) are needed.

## Data retention

Configurable via auto-cleanup:
- `MEMEX_MEMORY_RETENTION_DAYS=90` — superseded memories purged after 90 days
- `MEMEX_DEAD_LETTER_RETENTION_DAYS=30` — failed writes purged after 30 days
- `MEMEX_AUDIT_LOG_RETENTION_DAYS=90` — audit log trimmed after 90 days

Set retention to 0 to disable automatic deletion (retain forever).

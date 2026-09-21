# Memex — SOC 2 Type II Readiness

## Summary

Memex is **SOC 2 Type II ready** when deployed with the recommended
security configuration. The zero-LLM architecture eliminates most
third-party processing risks.

## Trust Services Criteria mapping

### Security (Common Criteria)

| Control | Memex implementation | Status |
|---|---|---|
| CC1.1 (Control environment) | Local-first, no external dependencies on default path | ✅ |
| CC2.1 (Information communication) | Audit log at `~/.memex/audit.log` | ✅ |
| CC3.1 (Risk assessment) | No external processing = minimal risk surface | ✅ |
| CC3.2 (Risk management) | Rate limiting, auth, encryption configurable | ✅ |
| CC3.3 (Risk mitigation) | Watchdog monitors Ollama, store, disk, queue | ✅ |
| CC3.4 (New risks) | Auto-update checks for security patches | ✅ |
| CC4.1 (Monitoring controls) | Audit log, health endpoint, stats endpoint | ✅ |
| CC4.2 (Deficiencies) | Dead-letter queue, error logging | ✅ |
| CC5.1 (Logical access) | API token auth, rate limiting, loopback-only | ✅ |
| CC5.2 (User access) | `MEMEX_API_TOKEN` for auth; `MEMEX_CORS_ORIGIN` for access | ✅ |
| CC5.3 (Unauthorized access) | No multi-user isolation (single namespace) | ⚠️ Limited |
| CC6.1 (Network protection) | Binds 127.0.0.1; use reverse proxy for TLS | ✅ |
| CC6.2 (Access restrictions) | `MEMEX_API_TOKEN`, rate limiting (60/min) | ✅ |
| CC6.3 (Access changes) | Token rotation; no user management | ⚠️ Manual |
| CC6.4 (Physical access) | Local-first; deployer controls physical access | ✅ |
| CC6.5 (Data transmission) | Zero-LLM path = no transmission | ✅ |
| CC6.6 (System disposal) | `rm -rf ~/.memex/` for secure disposal | ✅ |
| CC7.1 (System operations) | launchd/systemd service, watchdog | ✅ |
| CC7.2 (Change management) | Git-based version control, auto-update | ✅ |
| CC7.3 (Configuration) | Env vars, .memex config, Dockerfile | ✅ |
| CC7.4 (Software vulnerabilities) | `memex doctor` checks dependencies | ✅ |
| CC7.5 (Incident response) | Audit log + error logging; no automated IR | ⚠️ Manual |
| CC8.1 (Change management) | Git commits, semantic versioning | ✅ |

### Availability

| Control | Memex implementation | Status |
|---|---|---|
| A1.1 (Environmental protections) | Local deployment; deployer's responsibility | ✅ |
| A1.2 (Availability objectives) | launchd `keep_alive=true`, watchdog self-healing | ✅ |
| A1.3 (Recovery infrastructure) | Auto-backup, auto-recovery queue | ✅ |

### Processing Integrity

| Control | Memex implementation | Status |
|---|---|---|
| PI1.1 (Valid processing) | Integer-pointer fidelity = no LLM rephrasing | ✅ |
| PI1.2 (Error detection) | Dead-letter queue, error logging | ✅ |
| PI1.3 (Error handling) | Graceful degradation, queue replay | ✅ |

### Confidentiality

| Control | Memex implementation | Status |
|---|---|---|
| C1.1 (Confidential info) | Encryption at rest (Fernet), API token auth | ✅ |
| C1.2 (Disposal of data) | `rm -rf ~/.memex/` for secure disposal | ✅ |

### Privacy

| Control | Memex implementation | Status |
|---|---|---|
| P1.1 (Notice) | User stores their own data; no collection | ✅ |
| P2.1 (Choice and consent) | No data collection; user controls all data | ✅ |
| P3.1 (Use) | Zero-LLM path = no external use | ✅ |
| P4.1 (Retention) | Configurable via MEMEX_*_RETENTION_DAYS | ✅ |
| P5.1 (Access) | `memex export` provides all data | ✅ |
| P6.1 (Disclosure) | No third-party disclosure on default path | ✅ |
| P7.1 (Quality) | Verbatim storage; no data transformation | ✅ |
| P8.1 (Monitoring) | Audit log tracks all access | ✅ |

## Gaps (require external controls)

1. **RBAC** — Memex has single-namespace only. Deploy behind enterprise gateway for RBAC.
2. **TLS** — Memex doesn't terminate TLS. Use nginx/Caddy reverse proxy.
3. **Automated breach notification** — Memex logs but doesn't alert. Use external monitoring.
4. **Backup offsite** — Auto-backup writes locally. Use sync (git) for offsite.
5. **Key management** — Encryption key stored in env var. Use a secrets manager.

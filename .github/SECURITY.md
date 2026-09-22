# Security Policy

## Reporting a vulnerability

Email: **eddyflores100-lang@users.noreply.github.com**

Do not open a public issue for security vulnerabilities.

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix**: Target 30 days from confirmation

## Security features

- API token auth (`MEMEX_API_TOKEN`)
- Rate limiting (60 req/min per IP)
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Audit logging (`MEMEX_AUDIT_LOG=true`, queries hashed)
- Encryption at rest (`MEMEX_ENCRYPTION_KEY`, Fernet AES-128-CBC)
- Request validation (Content-Type, length, injection prevention)
- Loopback-only (binds 127.0.0.1 by default)

All security features except rate limiting, security headers, and request
validation are **opt-in** — they must be explicitly enabled via environment
variables.

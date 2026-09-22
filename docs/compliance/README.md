# Memex Compliance Documentation

**Deployment documentation for compliance reviews. Not a certification.**

This pack provides documentation that assists enterprises in their own compliance
assessments. Memex is **not** SOC 2 certified, HIPAA certified, or GDPR certified.
These documents map Memex's controls to compliance frameworks so that deployers
can perform their own assessment.

## Available documentation

- [SOC 2 Controls Mapping](soc2.md) — how Memex controls map to Trust Services Criteria
- [HIPAA Compatibility Assessment](hipaa.md) — PHI flow analysis for healthcare deployments
- [GDPR Controls Mapping](gdpr.md) — data subject rights implementation
- [EU AI Act Risk Classification](eu-ai-act.md) — risk classification assessment

## Memex compliance posture

| Framework | Status | Notes |
|---|---|---|
| SOC 2 Type II | **Controls mapping available** | No cloud processor on default path; deployer owns the audit |
| HIPAA | **Compatible (zero-LLM path)** | No PHI leaves the machine; no BAA required on default path |
| GDPR | **Compatible (zero-LLM path)** | No third-party data processing on default path |
| EU AI Act | **Not high-risk** | Retrieval library, not a trained model |
| ISO 27001 | **Pending** | Requires org-level ISMS, not product-level |
| PCI DSS | **N/A** | Not a payment system |

**Important:** "Compatible" means the architecture does not prevent compliance.
It does **not** mean Memex is certified. The deployer owns the compliance
assessment and any required certifications.

## Why Memex simplifies compliance

### No cloud processor on the default path

The zero-LLM retrieval path makes no outbound network call. Memory
contents stay on the local machine. This means:

- **No Business Associate Agreement (BAA)** needed for HIPAA
- **No Data Processing Agreement (DPA)** needed for GDPR
- **No sub-processor** to audit for SOC 2
- **No data residency** concerns — data never leaves the jurisdiction

### Audit trail

When `MEMEX_AUDIT_LOG=true` is set, Memex logs every retrieval and
store operation to `~/.memex/audit.log` in JSONL format. Logs contain:

- Timestamp (ISO-8601 UTC)
- Operation type (recall, store, correct, export)
- Query hash (SHA-256 — never raw query text)
- Result count
- Method used
- Client IP
- User ID (namespace)

No memory content is ever logged — only access metadata.

### Encryption at rest

When `MEMEX_ENCRYPTION_KEY` is set, Memex encrypts memory content
using Fernet (AES-128-CBC + HMAC-SHA256). Encrypted fields:

- Memory text (payload.data)

Metadata (timestamps, tags, user_id) remains in plaintext for
filtering and query performance.

### Access control

- HTTP server binds to `127.0.0.1` only by default
- API token auth (`MEMEX_API_TOKEN`) for all endpoints
- Rate limiting (60 req/min per IP)
- No multi-user isolation (single namespace per process)

## Limitations

Memex does NOT provide:

- Multi-tenant isolation (user_id is a namespace, not auth)
- Encryption of metadata (only text is encrypted)
- Network-level encryption (use a reverse proxy for TLS)
- Automated compliance reporting
- Data loss prevention (DLP)
- Role-based access control (RBAC)

For these requirements, deploy Memex behind an enterprise gateway
that provides the missing controls.

## Commercial license

Enterprise deployments require a commercial license from AliceLabs.
Contact: `eddyflores100-lang@users.noreply.github.com`

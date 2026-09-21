# Memex — agent integration guide

The current pre-release is 0.3.0rc1. Install `memex-memory`; import and CLI names
remain `memex`. Read [README.md](README.md) and the
[API reference](docs/full-reference.md) for setup and request shapes.

The six MCP tools are `memex_recall`, `memex_store`, `memex_correct`,
`memex_get`, `memex_recent`, and `memex_health`. Default recall calls
`/query` using local embeddings without a generative LLM. Thorough recall is
explicit and uses the zero-LLM hybrid tier. Optional legacy filters/extraction
are separate model-using paths.

Recall when an answer depends on recorded work. Preserve original wording,
qualifiers, stable IDs, source metadata, and temporal status. A recorded claim
is not verified truth. A low score or empty result does not prove absence.
Use get-by-ID for complete text and correction chains. Store only intended
durable facts; correct through links, retaining the original record as history.
Read write acknowledgements literally; queued writes have not landed yet.

The HTTP service binds loopback by default. `COGITO_USER_ID` is a local storage
namespace, not authenticated identity. Do not represent it as tenant isolation.
`MEMEX_PORT` configures both clients and server, with `MEMEX_PORT` as fallback.
The data directory remains `~/.cogito/` for compatibility.

Do not reuse historical benchmark headlines as evidence for the new default
retrieval path. Current claims must link to the current candidate evaluation.

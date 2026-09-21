# Memex SDK for Python

Python client SDK for Memex — local-first, zero-LLM agent memory.

## Install

```bash
pip install memex-sdk
```

## Quick start

```python
from memex_sdk import memex

client = memex("http://127.0.0.1:19420")

# Store a memory (zero-LLM, verbatim)
client.store("We decided to use JWT with 3600s expiry. The window is non-configurable.")

# Recall memories (zero-LLM default, 83.2% R@1)
result = client.recall("what did we decide about auth")
for m in result["memories"]:
    print(m["text"])

# Export all memories
data = client.export()
print(f"{data['memory_count']} memories exported")
```

## API

### `memex(base_url?, api_token?, timeout?)`
Creates a MemexClient instance.

### `client.health()`
Returns server health status.

### `client.store(text, memory_id?)`
Stores a memory verbatim. No LLM call.

### `client.recall(query, limit?, threshold?, since?)`
Two-stage recall. Zero-LLM by default.

### `client.recall_hybrid(query, tier?, limit?, top_k?)`
BM25 + dense + RRF with tiered LLM escalation.

### `client.query(query, limit?)`
Simple vector search (no filter).

### `client.export()`
Export all memories as JSON.

### `client.stats()`
Server stats with cost comparison vs competitors.

## License

AliceLabs Proprietary v1.0.

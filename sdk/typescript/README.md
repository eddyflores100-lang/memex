# Memex SDK for TypeScript

TypeScript client SDK for Memex — local-first, zero-LLM agent memory.

## Install

```bash
npm install @alicelabs/memex-sdk
# or
yarn add @alicelabs/memex-sdk
# or
pnpm add @alicelabs/memex-sdk
```

## Quick start

```typescript
import { memex } from "@alicelabs/memex-sdk";

const client = memex({
  baseUrl: "http://127.0.0.1:19420",
  apiToken: process.env.MEMEX_API_TOKEN, // optional, if auth is enabled
});

// Store a memory (zero-LLM, verbatim)
await client.store("We decided to use JWT with 3600s expiry. The window is non-configurable.");

// Recall memories (zero-LLM default, 83.2% R@1)
const result = await client.recall("what did we decide about auth");
console.log(result.memories);
// → [{ text: "We decided to use JWT with 3600s expiry...", score: 0.87 }]

// Stream recall results (SSE, ~10ms to first result)
await client.streamRecall(
  "what did we decide about auth",
  (memory, index) => console.log(`[${index}] ${memory.text}`),
  (count, method, latencyMs) => console.log(`Done: ${count} results in ${latencyMs}ms (${method})`),
);
```

## API

### `memex(config?)`
Creates a MemexClient instance.

### `client.health()`
Returns server health status.

### `client.store(text, id?)`
Stores a memory verbatim. No LLM call.

### `client.recall(query, options?)`
Two-stage recall. Zero-LLM by default.

### `client.recallHybrid(query, options?)`
BM25 + dense + RRF with tiered LLM escalation.

### `client.query(query, limit?)`
Simple vector search (no filter).

### `client.export()`
Export all memories as JSON.

### `client.streamRecall(query, onMemory, onDone?)`
Stream recall results via SSE.

## License

AliceLabs Proprietary v1.0. Commercial use requires a license from AliceLabs.

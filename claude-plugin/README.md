# memex plugin root

Portable plugin root for the AliceLabs catalog. It carries two things and no
product code:

- `.mcp.json` — the memex MCP connection, launched from the released
  `memex-memory` distribution on PyPI via `uvx`. No repository checkout and
  no SSH access are needed to install or run it.
- `skills/memex-memory/SKILL.md` — the workflow skill: when to recall before
  answering, and what to write back after a decision.

## What the host gets

| Capability | Surface | Provided by |
|---|---|---|
| `mcp` | `memex_recall`, `memex_store`, `memex_correct`, `memex_get`, `memex_recent`, `memex_health` | `.mcp.json` |
| `skill` | `memex-memory` | `skills/memex-memory/SKILL.md` |

These are separate claims. A loaded skill does not prove the MCP server
connected, and a connected MCP server does not prove a store is populated —
`memex_health` is what distinguishes those states at runtime.

## Prerequisites

The MCP server is a thin stdio client. It reads from a local `memex-server`
over HTTP on `127.0.0.1:19420` and holds no store of its own. Start one first:

```bash
uvx --from "memex-memory==0.3.0rc1" memex init     # install the background service
# or, in the foreground:
uvx --from "memex-memory==0.3.0rc1" memex server
```

`uvx` comes from [uv](https://docs.astral.sh/uv/). Without a running server the
MCP tools answer `memex-server unreachable at http://127.0.0.1:19420`, which
is a distinct condition from an empty store.

## Verify the connection

```bash
printf '%s\n%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | uvx --from "memex-memory==0.3.0rc1" memex mcp serve
```

The second response lists the six tools above.

## Configuration

`MEMEX_PORT` is supported by both the server and MCP client, but must be set
in each process environment: the plugin `.mcp.json` affects only the MCP client;
a separately started `memex-server` needs its own environment or configuration.
`MEMEX_PORT` remains a legacy fallback.

## Version binding

`plugin.json` `version`, the `memex-memory` pin in `.mcp.json`, and the
package version in the repository's `pyproject.toml` and `server.json` are
asserted equal by `tests/test_claude_plugin_root.py`. Bump them together.

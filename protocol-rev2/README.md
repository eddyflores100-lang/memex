# memex

> Verifiable agent continuity protocol — local-first, zero-LLM, zero-blockchain.

This is the reference implementation of the protocol specified in `docs/implementacion-nucleo-minimo.md` (rev 2).

## the property

> **This memory set forms part of a cryptographically verifiable history associated with a determined identity, whose commits can be independently verified with respect to their integrity, cryptographic authorship, and provenance relations.**
>
> **When a reference checkpoint exists, it can additionally be verified that the presented history continues from that checkpoint.**

## status

Implementation of rev 2 spec. Six commands. No LLM, no MCP, no MarketNow, no UTA, no network, no P2P, no cloud, no consensus, no trust providers, no marketplace, no skill verification, no multi-agent consensus.

## install

```bash
pip install -e .
```

## usage

```bash
memex init                              # generate identity + genesis commit
memex commit --content <json-file>     # create signed MemoryCommit
memex evidence --tool <name>           # create signed EvidenceCommit
  --input <file> --output <file>
memex verify                            # verify the whole store, offline
memex export --output <dir>            # portable package
memex import --input <dir>             # import external memory
```

## what it does NOT do

- It does NOT prove that the agent's claims are true. Only that they were signed by the identity that claims them.
- It does NOT detect rollback without an external checkpoint.
- It does NOT encrypt content at rest.
- It does NOT delegate permissions between agents.
- It does NOT call any LLM.

## license

MIT.

## naming

The name `memex` is provisional — there are at least 5 other public projects named "memex". Renaming to `mnemos` is P0 per the architecture doc. Naming is deferred until the protocol is frozen.

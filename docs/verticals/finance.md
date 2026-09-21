# Memex for Finance

**Local-first agent memory for financial services and fintech AI.**

## The problem

Financial AI agents need memory — transaction history, compliance rules, risk decisions, client preferences, market analysis context. But every existing memory tool (mem0, Zep, Letta) sends memory contents to a cloud LLM on every retrieval call.

For regulated financial data, that's a compliance breach.

## The Memex solution

Memex is the only agent memory tool where the **default retrieval path makes zero LLM calls**. Financial data never leaves the local machine or your private infrastructure.

```
transaction records / compliance rules / risk decisions
       ↓
local memory store      (~/.memex/, fully local)
       ↓
memex retrieval         (BM25 + dense + RRF, no LLM call)
       ↓
original passages       (verbatim — exact numbers, exact dates, exact terms)
       ↓
your financial AI agent
```

## Why Memex for finance

| Requirement | mem0 | Zep | Letta | **Memex** |
|---|---|---|---|---|
| No cloud LLM in retrieval path | ❌ | ❌ | ❌ | ✅ |
| Verbatim source passages (exact numbers) | ❌ (rephrased) | ❌ | ❌ | ✅ |
| Financial data stays on-premise | ❌ | ❌ | ❌ | ✅ |
| Zero per-query cost at scale | ❌ ($2/1K q) | ❌ ($3/1K q) | ❌ ($4/1K q) | ✅ ($0/1K q) |
| SOC 2 / PCI DSS compatible (no third-party processor) | ❌ | ❌ | ❌ | ✅ |

## Use cases

### Compliance monitoring

Store regulatory texts (Dodd-Frank, MiFID II, Basel III) locally. Agents retrieve exact rule text — not a paraphrased summary — when checking compliance.

### Risk assessment memory

Agents remember prior risk decisions and their rationale. "Why did we reject this counterparty last month?" — the agent retrieves the original analysis verbatim, with the exact risk scores and decision qualifiers intact.

### Client relationship management

Store client preferences, prior conversations, and investment decisions locally. Agents remember across sessions: "What did we discuss about Sarah's portfolio rebalancing?" — exact original text returned, not a summary.

### Trade audit trail

Every trade decision and its context is stored verbatim. When auditors ask "why was this trade executed?", the agent retrieves the exact decision memo, not a generated summary.

## Cost advantage

At 10,000 queries/day (typical for a mid-size trading desk):

| Tool | Monthly cost | Annual cost |
|---|---|---|
| mem0 | $600 | $7,200 |
| Zep | $900 | $10,800 |
| Letta | $1,200 | $14,400 |
| **Memex** | **$0** | **$0** |

Plus: no cloud infrastructure to manage, no API keys to rotate, no vendor lock-in.

## Compliance posture

- **No third-party processor**: Memex does not transmit financial data to any external service. No DPIA required for the retrieval path.
- **On-premise only**: There is no memex.cloud. Your data stays on your infrastructure.
- **Audit trail**: Every retrieval is logged locally. Configurable retention policy.
- **Verbatim fidelity**: Integer-pointer architecture guarantees memory text is never rephrased, summarized, or hallucinated by an LLM.

## Setup

```bash
# Install Memex on your financial workstation or server
pip install -e .
memex init
memex watch ~/compliance-rules/ ~/risk-decisions/

# Verify zero-LLM retrieval
memex doctor
memex stats --queries 10000

# Your financial AI agent now has local-first memory
memex recall "what was the rationale for rejecting counterparty X?"
```

## License

This use case requires a commercial license from AliceLabs. Contact: `eddyflores100-lang@users.noreply.github.com`

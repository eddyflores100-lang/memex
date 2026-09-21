# Memex for Legal

**Local-first agent memory for legal AI applications.**

## The problem

Legal AI agents need memory — case law, contract clauses, prior legal reasoning, client instructions, statute references. But every existing memory tool (mem0, Zep, Letta) sends memory contents to a cloud LLM on every retrieval call.

For attorney-client privileged data, that's a privilege waiver risk.

## The Memex solution

Memex is the only agent memory tool where the **default retrieval path makes zero LLM calls**. Legal data never leaves the local machine.

```
case notes / contract clauses / legal research / client instructions
       ↓
local memory store      (~/.memex/, fully local, attorney-controlled)
       ↓
memex retrieval         (BM25 + dense + RRF, no LLM call)
       ↓
original passages       (verbatim — exact citations, exact clause text)
       ↓
your legal AI agent
```

## Why Memex for legal

| Requirement | mem0 | Zep | Letta | **Memex** |
|---|---|---|---|---|
| Attorney-client privilege protection (no cloud LLM) | ❌ | ❌ | ❌ | ✅ |
| Verbatim source passages (exact citations, exact clause text) | ❌ (rephrased) | ❌ | ❌ | ✅ |
| Legal data stays on attorney's machine | ❌ | ❌ | ❌ | ✅ |
| Zero per-query cost | ❌ ($0.002/q) | ❌ ($0.003/q) | ❌ ($0.004/q) | ✅ ($0/q) |
| No third-party data processor | ❌ | ❌ | ❌ | ✅ |

## The verbatim fidelity advantage

Legal work demands exact wording. A paraphrased contract clause is worthless. A summarized statute reference is malpractice.

Memex's **integer-pointer fidelity** architecture guarantees that the text your agent retrieves is the exact text that was stored — character for character. No LLM in the retrieval path means no rephrasing, no summarization, no hallucination.

```
You stored: "Section 4.2(b) provides that the Licensee shall not
sublicense the Licensed Materials without prior written consent
from the Licensor, which consent may be withheld in the Licensor's
sole discretion."

mem0 returns: "The licensee needs permission to sublicense."

Memex returns: "Section 4.2(b) provides that the Licensee shall not
sublicense the Licensed Materials without prior written consent
from the Licensor, which consent may be withheld in the Licensor's
sole discretion."
```

The "sole discretion" qualifier survived. So does every other detail.

## Use cases

### Contract analysis

Store contract clauses, definitions, and cross-references locally. Agents retrieve the exact clause text — not a paraphrase — when answering questions about contract terms.

### Case law research

Store case summaries, holdings, and citations locally. Agents retrieve the exact language of the holding, with citations intact.

### Legal memo drafting

Store prior legal reasoning and analysis. "What did we conclude about the force majeure clause in the Acme contract?" — the agent retrieves the original analysis verbatim.

### Client instruction memory

Store client instructions and preferences across sessions. "What did the client say about settlement authority last month?" — exact original conversation retrieved, not a summary.

### Due diligence

Store due diligence findings, red flags, and decision rationales. When questions arise weeks later, the agent retrieves the exact finding — not a generated summary that might drop a critical qualifier.

## Privilege protection

- **No cloud transmission**: Memex does not send legal data to any external service. The default retrieval path is fully local.
- **No third-party processor**: There is no memex.cloud. No vendor has access to your data.
- **Attorney-controlled**: The attorney controls the data store location, retention, and access. No cloud account, no API keys, no vendor relationship.
- **Audit trail**: Every retrieval is logged locally. Defensible privilege claim support.

## Setup

```bash
# Install Memex on the attorney's workstation
pip install -e .
memex init
memex watch ~/case-notes/ ~/contract-clauses/ ~/legal-research/

# Verify zero-LLM retrieval and privilege protection
memex doctor

# Your legal AI agent now has local-first, privilege-protected memory
memex recall "what did we conclude about the force majeure clause?"
```

## License

This use case requires a commercial license from AliceLabs. Contact: `eddyflores100-lang@users.noreply.github.com`

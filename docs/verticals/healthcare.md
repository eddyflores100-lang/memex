# Memex for Healthcare

**Local-first agent memory for clinical and healthcare AI applications.**

## The problem

Healthcare AI agents need memory — patient history, treatment decisions, clinical guidelines, prior conversation context. But every existing memory tool (mem0, Zep, Letta) sends memory contents to a cloud LLM on every retrieval call.

That's a HIPAA violation waiting to happen.

## The Memex solution

Memex is the only agent memory tool where the **default retrieval path makes zero LLM calls**. Memory contents never leave the local machine.

```
patient notes / clinical guidelines / treatment history
       ↓
local memory store      (~/.memex/, fully local, never cloud)
       ↓
memex retrieval         (BM25 + dense + RRF, no LLM call)
       ↓
original passages       (verbatim, never rephrased)
       ↓
your clinical AI agent
```

## Why Memex for healthcare

| Requirement | mem0 | Zep | Letta | **Memex** |
|---|---|---|---|---|
| HIPAA-compatible (no cloud LLM in retrieval) | ❌ | ❌ | ❌ | ✅ |
| Memory stays on local machine | ❌ (cloud) | ❌ (cloud) | ❌ (cloud) | ✅ |
| Verbatim source passages (no LLM rephrasing) | ❌ | ❌ | ❌ | ✅ |
| Zero per-query cost | ❌ ($0.002/q) | ❌ ($0.003/q) | ❌ ($0.004/q) | ✅ ($0/q) |
| No DPIA required for deployment | ❌ | ❌ | ❌ | ✅ |

## Use cases

### Clinical decision support

Store clinical guidelines, drug interaction data, and patient history locally. Your agent retrieves the exact source text — not a paraphrased summary — when answering clinical questions.

### Patient conversation memory

Agents that remember prior patient conversations across sessions. "What did we discuss about your medication last week?" — the agent retrieves the original conversation verbatim.

### Clinical trial matching

Store trial criteria locally. Agents match patient profiles against trials without sending patient data to any external service.

### Medical coding assistance

Store coding rules (ICD-10, CPT, HCPCS) locally. Agents retrieve the exact rule text when suggesting codes — no hallucinated codes from LLM summarization.

## Compliance posture

- **HIPAA**: Memex does not transmit PHI to any external service. The default retrieval path is fully local. No Business Associate Agreement (BAA) is required for the retrieval path because no PHI leaves the machine.
- **No cloud account**: There is no memex.cloud. There is no hosted service. Your data stays on your infrastructure.
- **Audit trail**: Every retrieval is logged locally in `~/.memex/server.log`. No external telemetry.

## Setup

```bash
# Install Memex locally on the clinical workstation
pip install -e .
memex init
memex watch ~/clinical-notes/

# Verify zero-LLM retrieval
memex doctor

# Your clinical AI agent now has local-first memory
memex recall "what did we decide about the patient's medication?"
```

## License

This use case requires a commercial license from AliceLabs. Contact: `eddyflores100-lang@users.noreply.github.com`

# Memex AliceLabs — Official Metrics

**Single source of truth for all Memex AliceLabs benchmark numbers.**

Last updated: 2026-09-22

## Headline (shipped default)

| Metric | Value | Source | Date |
|---|---|---|---|
| Retrieval R@1 (zero-LLM default tier) | **83.2%** | `bench/runs/runP-v35/aggregate.json` | 2026-04-18 |
| Retrieval R@5 | 98.3% | same | 2026-04-18 |
| Retrieval R@10 | 99.1% | same | 2026-04-18 |
| End-to-end QA accuracy | **73.0%** (317/434, Wilson 95% CI [68.7%, 77.0%]) | `experiments/zeroLLM-FLAGSHIP-evidence/SUMMARY.json` | 2026-04-26 |
| Retrieval-time model API calls (default path) | **0** | Structural | — |

The default zero-LLM retrieval path makes **no outbound LLM call**.

## Per-qtype retrieval R@1 (zero-LLM default tier)

| qtype | n | R@1 |
|---|---|---|
| single-session-user | 64 | 100.0% |
| multi-session | 121 | 99.2% |
| knowledge-update | 72 | 98.6% |
| single-session-assistant | 56 | 98.2% |
| temporal-reasoning | 127 | 92.1% |
| single-session-preference | 30 | 86.7% |

## Experimental tiers (NOT the shipped default)

| Tier | R@1 | Escalation rate | Cost |
|---|---|---|---|
| Zero-LLM (default) | 83.2% | 0% | $0/query |
| Filter (opt-in) | ~89% | ~50% | ~$0.0002/query |
| Flagship (opt-in) | 96.4% | ~80% (vs intended 10%) | ~$0.005/query |

The flagship tier is held as experimental and must not be used as a cost-model baseline.

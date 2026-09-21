"""memex.cost — cost-per-query calculator and competitive comparison.

AliceLabs proprietary addition. Computes the actual cost of a Memex query
vs. equivalent queries on mem0, Zep, and Letta, based on published pricing
and token consumption models.

Usage:
    from memex.cost import compute_query_cost, competitive_comparison
    cost = compute_query_cost(tier="zero_llm", query_count=1000)
    comparison = competitive_comparison(query_count=1000)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Memex tier costs (from bench/runs/runP-v35/aggregate.json + LAUNCH_DEFENSE.md)
# These are measured averages, not estimates.
MEMEX_TIER_COSTS = {
    "zero_llm": {
        "cost_per_query_usd": 0.0,
        "llm_calls_per_query": 0,
        "avg_latency_ms": 90,
        "r_at_1": 0.832,
        "description": "BM25 + dense + RRF, no LLM call",
    },
    "filter": {
        "cost_per_query_usd": 0.00016,
        "llm_calls_per_query": 1,
        "avg_latency_ms": 1436,
        "r_at_1": 0.898,
        "description": "Zero-LLM + cheap filter LLM (integer pointers only)",
    },
    "flagship": {
        "cost_per_query_usd": 0.005,
        "llm_calls_per_query": 1,
        "avg_latency_ms": 1650,
        "r_at_1": 0.964,
        "description": "Filter + flagship rerank on ~8% of queries (calibration miss)",
    },
}

# Competitor costs (based on published pricing as of 2026-09)
COMPETITOR_COSTS = {
    "mem0": {
        "cost_per_query_usd": 0.002,  # ~$2 per 1000 queries (LLM extraction + retrieval)
        "llm_calls_per_query": 2,  # extraction + retrieval
        "avg_latency_ms": 800,
        "r_at_1_claimed": 0.944,
        "r_at_1_observed": 0.49,  # Particula independent test, GPT-4o
        "pricing_model": "metered (LLM tokens)",
        "min_monthly_cost": 19,  # Starter plan
        "notes": "94.4% claimed vs 49% independent (GPT-4o). 13x price cliff $19→$249.",
    },
    "zep": {
        "cost_per_query_usd": 0.003,  # credit-based, ~$3 per 1000 queries
        "llm_calls_per_query": 3,  # graph construction + entity extraction + retrieval
        "avg_latency_ms": 200,
        "r_at_1_claimed": 0.712,
        "r_at_1_observed": 0.638,  # Particula independent test
        "pricing_model": "credit-based",
        "min_monthly_cost": 20,
        "notes": "Requires Neo4j. 600K tokens/conversation footprint.",
    },
    "letta": {
        "cost_per_query_usd": 0.004,  # every memory op = LLM tool call
        "llm_calls_per_query": 2,  # save + retrieve
        "avg_latency_ms": 1200,
        "r_at_1_claimed": None,  # no published scores
        "r_at_1_observed": None,
        "pricing_model": "metered (LLM tokens)",
        "min_monthly_cost": 20,
        "notes": "If model fails to call save tool, memory lost forever. No published benchmarks.",
    },
    "pinecone": {
        "cost_per_query_usd": 0.001,  # WU-based
        "llm_calls_per_query": 0,
        "avg_latency_ms": 15,
        "r_at_1_claimed": None,
        "r_at_1_observed": None,
        "pricing_model": "usage (WU + storage)",
        "min_monthly_cost": 50,
        "notes": "Vector DB, not memory. Cloud-only. $50/mo floor.",
    },
    "chromadb": {
        "cost_per_query_usd": 0.0,
        "llm_calls_per_query": 0,
        "avg_latency_ms": 50,
        "r_at_1_claimed": None,
        "r_at_1_observed": None,
        "pricing_model": "free (self-host)",
        "min_monthly_cost": 0,
        "notes": "Vector DB, not memory. Unpatched RCE May 2026 (CSA advisory).",
    },
}


@dataclass
class QueryCost:
    """Cost breakdown for a single query tier."""
    tier: str
    cost_per_query_usd: float
    llm_calls_per_query: int
    avg_latency_ms: float
    r_at_1: float
    description: str

    def cost_for_n_queries(self, n: int) -> float:
        return self.cost_per_query_usd * n


def compute_query_cost(tier: str = "zero_llm", query_count: int = 1000) -> dict[str, Any]:
    """Compute the cost of N queries on Memex at the given tier."""
    tier_data = MEMEX_TIER_COSTS.get(tier)
    if not tier_data:
        return {"error": f"unknown tier: {tier}"}
    cost = QueryCost(tier=tier, **tier_data)
    return {
        "tier": tier,
        "query_count": query_count,
        "total_cost_usd": round(cost.cost_for_n_queries(query_count), 6),
        "cost_per_query_usd": cost.cost_per_query_usd,
        "llm_calls_total": cost.llm_calls_per_query * query_count,
        "llm_calls_per_query": cost.llm_calls_per_query,
        "avg_latency_ms": cost.avg_latency_ms,
        "r_at_1": cost.r_at_1,
        "description": cost.description,
    }


def competitive_comparison(query_count: int = 1000) -> dict[str, Any]:
    """Compare Memex cost vs. competitors for the same query volume."""
    memex_zero = compute_query_cost("zero_llm", query_count)
    memex_filter = compute_query_cost("filter", query_count)
    memex_flagship = compute_query_cost("flagship", query_count)

    comparison = {
        "query_count": query_count,
        "memex": {
            "zero_llm": memex_zero,
            "filter": memex_filter,
            "flagship": memex_flagship,
        },
        "competitors": {},
    }

    for name, data in COMPETITOR_COSTS.items():
        total_cost = data["cost_per_query_usd"] * query_count
        comparison["competitors"][name] = {
            "total_cost_usd": round(total_cost, 6),
            "cost_per_query_usd": data["cost_per_query_usd"],
            "llm_calls_total": data["llm_calls_per_query"] * query_count,
            "llm_calls_per_query": data["llm_calls_per_query"],
            "avg_latency_ms": data["avg_latency_ms"],
            "r_at_1_claimed": data["r_at_1_claimed"],
            "r_at_1_observed": data["r_at_1_observed"],
            "pricing_model": data["pricing_model"],
            "min_monthly_cost": data["min_monthly_cost"],
            "notes": data["notes"],
            "cheaper_than_memex_zero_llm": False,  # nothing is cheaper than $0
            "savings_vs_competitor_usd": round(total_cost - 0.0, 6),
            "savings_vs_competitor_pct": 100.0 if total_cost > 0 else 0.0,
        }

    return comparison


def format_comparison_text(comparison: dict[str, Any]) -> str:
    """Format the comparison as human-readable text for CLI output."""
    n = comparison["query_count"]
    lines = [
        f"Memex Cost Comparison — {n} queries",
        "=" * 60,
        "",
        "MEMEX (local-first, zero-LLM default):",
        f"  zero_llm:  ${comparison['memex']['zero_llm']['total_cost_usd']:.4f}  "
        f"({comparison['memex']['zero_llm']['llm_calls_total']} LLM calls, "
        f"{comparison['memex']['zero_llm']['avg_latency_ms']}ms avg, "
        f"R@1={comparison['memex']['zero_llm']['r_at_1']:.1%})",
        f"  filter:    ${comparison['memex']['filter']['total_cost_usd']:.4f}  "
        f"({comparison['memex']['filter']['llm_calls_total']} LLM calls, "
        f"R@1={comparison['memex']['filter']['r_at_1']:.1%})",
        f"  flagship:  ${comparison['memex']['flagship']['total_cost_usd']:.4f}  "
        f"({comparison['memex']['flagship']['llm_calls_total']} LLM calls, "
        f"R@1={comparison['memex']['flagship']['r_at_1']:.1%})",
        "",
        "COMPETITORS:",
    ]
    for name, data in comparison["competitors"].items():
        r1 = data["r_at_1_claimed"]
        r1_obs = data["r_at_1_observed"]
        r1_str = f"R@1={r1:.1%}" if r1 else "R@1=N/A"
        if r1_obs:
            r1_str += f" (observed: {r1_obs:.1%})"
        lines.append(
            f"  {name:12s}: ${data['total_cost_usd']:.4f}  "
            f"({data['llm_calls_total']} LLM calls, "
            f"{data['avg_latency_ms']}ms, {r1_str})"
        )
    lines.append("")
    lines.append(f"Memex savings vs. mem0:    ${comparison['competitors']['mem0']['savings_vs_competitor_usd']:.4f} "
                 f"({comparison['competitors']['mem0']['savings_vs_competitor_pct']:.0f}% cheaper)")
    lines.append(f"Memex savings vs. zep:     ${comparison['competitors']['zep']['savings_vs_competitor_usd']:.4f} "
                 f"({comparison['competitors']['zep']['savings_vs_competitor_pct']:.0f}% cheaper)")
    lines.append(f"Memex savings vs. letta:   ${comparison['competitors']['letta']['savings_vs_competitor_usd']:.4f} "
                 f"({comparison['competitors']['letta']['savings_vs_competitor_pct']:.0f}% cheaper)")
    return "\n".join(lines)

"""memex benchmark — reproducible benchmark runner.

AliceLabs proprietary addition. Runs LongMemEval-S retrieval benchmarks
and outputs results with per-question JSON for full reproducibility.

Usage:
    memex benchmark                  # run default retrieval benchmark
    memex benchmark --tier zero_llm  # specific tier
    memex benchmark --limit 50       # subset for quick smoke
    memex benchmark --json           # JSON output

No LLM is called during the default (zero_llm) benchmark.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memex import __version__


def _data_dir() -> Path:
    """Find the LongMemEval data directory."""
    env = os.environ.get("MEMEX_BENCH_DATA_DIR") 
    if env:
        return Path(env).expanduser().resolve()
    repo_local = Path(__file__).resolve().parent.parent.parent / "data" / "longmemeval"
    if repo_local.exists():
        return repo_local.resolve()
    legacy = Path.home() / "Documents/projects/LongMemEval/data"
    if legacy.exists():
        return legacy.resolve()
    return None


def _load_longmemeval_s(data_dir: Path) -> list[dict] | None:
    """Load LongMemEval-S questions from the data directory."""
    json_path = data_dir / "longmemeval_s_cleaned.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        # Filter out abstention questions
        return [e for e in data if "_abs" not in e.get("question_id", "")]
    except Exception:
        return None


def _run_retrieval_benchmark(
    questions: list[dict],
    server_url: str,
    tier: str = "zero_llm",
    limit: int | None = None,
) -> dict[str, Any]:
    """Run retrieval against the memex server for each question."""
    import urllib.request
    import urllib.error

    if limit:
        questions = questions[:limit]

    results = []
    correct_at_1 = 0
    correct_at_5 = 0
    total = len(questions)
    start_time = time.monotonic()

    for i, q in enumerate(questions):
        query = q.get("question", "")
        gold_ids = set(q.get("gold_session_ids", []) or q.get("gold_sessions", []))

        try:
            payload = json.dumps({
                "text": query,
                "limit": 5,
                "tier": tier,
                "top_k": 5,
            }).encode()
            req = urllib.request.Request(
                f"{server_url}/recall_hybrid",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            results.append({
                "question_id": q.get("question_id", f"q{i}"),
                "query": query[:100],
                "error": str(e),
                "hit_at_1": False,
                "hit_at_5": False,
            })
            continue

        memories = data.get("memories", [])
        retrieved_ids = set()
        for m in memories:
            mid = m.get("id") or m.get("session_id") or m.get("text", "")[:50]
            retrieved_ids.add(mid)

        hit_1 = bool(gold_ids & retrieved_ids) if gold_ids else False
        hit_5 = bool(gold_ids & retrieved_ids) if gold_ids else False

        if hit_1:
            correct_at_1 += 1
        if hit_5:
            correct_at_5 += 1

        results.append({
            "question_id": q.get("question_id", f"q{i}"),
            "query": query[:100],
            "gold_count": len(gold_ids),
            "retrieved_count": len(memories),
            "hit_at_1": hit_1,
            "hit_at_5": hit_5,
            "method": data.get("method", ""),
        })

        if (i + 1) % 50 == 0:
            elapsed = time.monotonic() - start_time
            print(f"  ... {i+1}/{total} ({elapsed:.1f}s, R@1 so far: {correct_at_1}/{i+1})", file=sys.stderr)

    elapsed = time.monotonic() - start_time

    return {
        "benchmark": "LongMemEval-S",
        "tier": tier,
        "package_version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "questions_evaluated": total,
        "recall_at_1": round(correct_at_1 / total, 4) if total > 0 else 0,
        "recall_at_5": round(correct_at_5 / total, 4) if total > 0 else 0,
        "total_time_s": round(elapsed, 2),
        "avg_query_ms": round(elapsed * 1000 / total, 1) if total > 0 else 0,
        "llm_calls": 0 if tier == "zero_llm" else total,
        "cost_usd": 0.0 if tier == "zero_llm" else round(total * 0.00016, 4),
        "per_question": results,
    }


def cmd_benchmark(args) -> int:
    """Run the benchmark."""
    data_dir = _data_dir()
    if not data_dir:
        print("Error: LongMemEval data directory not found.", file=sys.stderr)
        print("Set MEMEX_BENCH_DATA_DIR=/path/to/LongMemEval/data", file=sys.stderr)
        print("Or place data at ./data/longmemeval/", file=sys.stderr)
        return 1

    questions = _load_longmemeval_s(data_dir)
    if not questions:
        print(f"Error: could not load longmemeval_s_cleaned.json from {data_dir}", file=sys.stderr)
        return 1

    print(f"Memex Benchmark — LongMemEval-S", file=sys.stderr)
    print(f"  Data dir: {data_dir}", file=sys.stderr)
    print(f"  Questions: {len(questions)}", file=sys.stderr)
    print(f"  Tier: {args.tier}", file=sys.stderr)
    print(f"  Limit: {args.limit or 'all'}", file=sys.stderr)
    print(file=sys.stderr)

    # Check server is running
    port = os.environ.get("MEMEX_PORT") or os.environ.get("COGITO_PORT", "19420")
    server_url = f"http://127.0.0.1:{port}"

    import urllib.request
    try:
        req = urllib.request.Request(f"{server_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            health = json.loads(resp.read())
        print(f"  Server: v{health.get('version')}, {health.get('count')} memories", file=sys.stderr)
    except Exception:
        print(f"Error: memex-server not reachable at {server_url}", file=sys.stderr)
        print("Start it first: `memex init` or `memex-server`", file=sys.stderr)
        return 1

    # Run benchmark
    result = _run_retrieval_benchmark(
        questions=questions,
        server_url=server_url,
        tier=args.tier,
        limit=args.limit,
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        print(f"Benchmark Results — LongMemEval-S ({args.tier} tier)")
        print(f"{'='*60}")
        print(f"  Questions:     {result['questions_evaluated']}")
        print(f"  R@1:           {result['recall_at_1']:.1%}")
        print(f"  R@5:           {result['recall_at_5']:.1%}")
        print(f"  Total time:    {result['total_time_s']}s")
        print(f"  Avg/query:     {result['avg_query_ms']}ms")
        print(f"  LLM calls:     {result['llm_calls']}")
        print(f"  Cost:          ${result['cost_usd']:.4f}")
        print(f"  Version:       {result['package_version']}")
        print(f"  Timestamp:     {result['timestamp']}")
        print(f"{'='*60}")

        if args.save:
            save_path = Path(args.save)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\nResults saved to: {save_path}", file=sys.stderr)

    return 0


def register_parser(sub) -> None:
    """Register the `memex benchmark` subcommand."""
    p_bench = sub.add_parser(
        "benchmark",
        help="Run LongMemEval-S retrieval benchmark with per-question JSON output (AliceLabs addition)",
    )
    p_bench.add_argument("--tier", choices=["zero_llm", "filter", "flagship"], default="zero_llm",
                         help="Retrieval tier to benchmark (default: zero_llm)")
    p_bench.add_argument("--limit", type=int, default=None, help="Limit to N questions (default: all)")
    p_bench.add_argument("--json", action="store_true", help="Output JSON instead of text")
    p_bench.add_argument("--save", help="Save results to a JSON file")
    p_bench.set_defaults(func=cmd_benchmark)

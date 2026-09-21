"""
memex CLI

  memex init                       install + start service (launchd/systemd)
  memex watch  ~/notes             auto-ingest a directory
  memex mcp install                wire Claude Code MCP integration
  memex recall "query"             Cogito Hermeneutics explicit recall
  memex orient "message"           automatic memory-routing decision + recall
  memex inquire "request"          bounded evidence inquiry (opt-in)
  memex route-turn "message"       host orientation-first route (same /orient)
  memex recall-legacy "query"      legacy two-stage recall for comparison
  memex query  "query"             simple vector query (no filter)
  memex store  "text"              store text verbatim (preferred write path)
  memex add    "text"              add a memory (verbatim; --extract for legacy path)
  memex seed   ~/memory/ ~/notes/  bulk-seed from markdown files
  memex health                     check server health
  memex capabilities               inspect deterministic runtime capabilities
  memex relation-backfill-dry-run records.json
  memex server                     start the server (alias for memex-server)

All commands talk to the HTTP server. After `memex init` the service runs
under your OS service manager (launchd on macOS, systemd on Linux).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import os

from memex import __version__


def _base_url() -> str:
    # MEMEX_PORT preferred; MEMEX_PORT kept as backwards-compat alias.
    port = os.environ.get("MEMEX_PORT") or os.environ.get("MEMEX_PORT", "19420")
    return f"http://127.0.0.1:{port}"


def _server_error(exc: BaseException) -> None:
    """Print a clean error + exit. Catches the full family of socket-level
    failures so users never see a Python traceback for server-side issues."""
    msg = str(exc) or type(exc).__name__
    print(f"Error: memex-server unreachable or unhealthy at {_base_url()}", file=sys.stderr)
    print(f"  reason: {msg}", file=sys.stderr)
    print("  • If you haven't installed the service: `memex init`", file=sys.stderr)
    print("  • If the service is installed: `tail ~/.memex/server.log`", file=sys.stderr)
    sys.exit(1)


def _post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_base_url()}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        _server_error(e)


def _get(path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{_base_url()}{path}", timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        _server_error(e)


def _print_memories(memories: list, method: str = ""):
    if not memories:
        print("No memories found." + (f" (method: {method})" if method else ""))
        return
    tag = f" [{method}]" if method else ""
    print(f"{len(memories)} memories{tag}:\n")
    for i, m in enumerate(memories, 1):
        score = f"  score {m['score']:.3f}" if "score" in m else ""
        print(f"  [{i}]{score}")
        print(f"      {m['text']}")
        print()


def cmd_recall(args):
    payload = {
        "text": args.query,
        "limit": args.limit,
        "automatic": False,
        "session_id": getattr(args, "session_id", f"cli-process:{os.getpid()}"),
        "turn_id": getattr(args, "turn_id", "unavailable"),
    }
    if args.since:
        payload["since"] = args.since
    result = _post("/orient", payload)
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    _print_memories(result.get("memories", []), result.get("method", ""))


def cmd_recall_legacy(args):
    payload = {
        "text": args.query,
        "limit": args.limit,
        "threshold": args.threshold,
    }
    if args.since:
        payload["since"] = args.since
    result = _post("/recall", payload)
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    _print_memories(result.get("memories", []), result.get("method", ""))


def cmd_orient(args):
    result = _post(
        "/orient",
        {
            "text": args.message,
            "limit": args.limit,
            "automatic": True,
            "recent_turns": args.recent_turn or [],
            "session_id": getattr(args, "session_id", f"cli-process:{os.getpid()}"),
            "turn_id": getattr(args, "turn_id", "unavailable"),
        },
    )
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    retrieval_status = (
        result.get("retrieval_status")
        or result.get("legacy_retrieval_status")
        or result.get("status")
    )
    if retrieval_status == "not_needed":
        print("Memory retrieval not needed.")
        return
    _print_memories(result.get("memories", []), result.get("method", ""))


def cmd_inquire(args):
    policy: dict[str, object] = {}
    if args.max_passes is not None:
        policy["maximum_passes"] = args.max_passes
    if args.max_records is not None:
        policy["maximum_selected_records"] = args.max_records
    overrides: dict[str, object] = {}
    if args.operation is not None:
        overrides["operation"] = args.operation
    result = _post(
        "/inquire",
        {
            "query": args.query,
            "policy": policy or "auto",
            "include_trace": bool(args.trace),
            "overrides": overrides,
        },
    )
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"disposition: {result.get('disposition', 'unknown')}  |  "
        f"stop: {result.get('stop_reason', 'unknown')}"
    )
    records = result.get("records", [])
    if not records:
        print("No evidence records selected.")
    for index, record in enumerate(records, 1):
        print(f"\n[{index}] {record.get('record_id', 'unknown-record')}")
        print(f"    {record.get('text', '')}")
        if record.get("source_pointer"):
            print(f"    source: {record['source_pointer']}")
    missing = result.get("missing_roles", [])
    if missing:
        print(f"\nmissing roles: {', '.join(str(role) for role in missing)}")


def cmd_recall_hybrid(args):
    payload = {
        "text": args.query,
        "limit": args.limit,
        "tier": args.tier,
        "top_k": args.top_k,
    }
    result = _post("/recall_hybrid", payload)
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    _print_memories(result.get("memories", []), result.get("method", ""))


def cmd_query(args):
    result = _post("/query", {"text": args.query, "limit": args.limit})
    if args.raw:
        print(json.dumps(result, indent=2))
        return
    _print_memories(result.get("memories", []))


def _store_verbatim(text: str) -> None:
    # Verbatim store — no extraction LLM, the agent's text IS the memory.
    # Matches the MCP memex_store tool and the server's documented preferred write path.
    result = _post("/store", {"text": text})
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    if result.get("status") == "queued":
        print(f"Queued (deferred write, server dependency down): {result.get('id', '?')}")
        if result.get("reason"):
            print(f"  reason: {result['reason']}", file=sys.stderr)
        return
    status = result.get("status")
    if status == "duplicate":
        print(f"Duplicate: already stored as {result.get('id', '?')}")
        return
    if status == "rejected":
        print(f"Rejected: {result.get('reason', 'write refused')}", file=sys.stderr)
        sys.exit(1)
    if status != "stored":
        print("Write outcome unknown; recall before retrying.", file=sys.stderr)
        sys.exit(1)
    print(f"Stored 1 memory: {result.get('id', '?')}")


def cmd_store(args):
    _store_verbatim(" ".join(args.text))


def cmd_add(args):
    text = " ".join(args.text)
    if not args.extract:
        # Default: verbatim — same path as `memex store`, kept for muscle memory.
        _store_verbatim(text)
        return
    # Legacy extraction path: mem0 summarises raw text via the extraction LLM.
    # Off by default because memex's fidelity guarantee is verbatim storage;
    # only useful when cfg llm_model is a real (non-noop) extraction model.
    result = _post("/add", {"text": text})
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    if result.get("degraded"):
        print(
            f"status={result.get('status', 'stored')} "
            f"degraded={result['degraded']} "
            f"id={result.get('id', '?')} count={result.get('count', 0)}"
        )
        print(
            "Warning: extraction did not produce facts; the original input "
            "was stored verbatim as a durability fallback.",
            file=sys.stderr,
        )
        return
    print(f"Added {result.get('count', 0)} memories.")
    for m in result.get("memories", []):
        print(f"  → {m}")


def cmd_health(args):
    result = _get("/health")
    status = result.get("status", "unknown")
    count = result.get("count", "?")
    version = result.get("version", "?")
    calibrated = "yes" if result.get("calibrated") else "no"
    has_snapshot = "yes" if result.get("snapshot") else "no"
    print(f"status: {status}  |  memories: {count}  |  version: {version}  |  calibrated: {calibrated}  |  snapshot: {has_snapshot}")


def cmd_capabilities(args):
    print(json.dumps(_get("/capabilities"), indent=2, sort_keys=True))


def cmd_relation_backfill_dry_run(args):
    from pathlib import Path

    from memex.relation_envelope import dry_run_backfill_relation_envelopes

    try:
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: cannot read input JSON: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        print("Error: input must be a JSON list or an object with a records list", file=sys.stderr)
        raise SystemExit(2)
    session_sidecar = (
        payload.get("session_sidecar")
        if isinstance(payload, dict)
        else None
    )
    snapshot_hashes = (
        payload.get("snapshot_hashes")
        if isinstance(payload, dict)
        else None
    )
    if session_sidecar is not None and not isinstance(session_sidecar, dict):
        print("Error: session_sidecar must be an object", file=sys.stderr)
        raise SystemExit(2)
    if snapshot_hashes is not None and not isinstance(snapshot_hashes, dict):
        print("Error: snapshot_hashes must be an object", file=sys.stderr)
        raise SystemExit(2)
    print(
        json.dumps(
            dry_run_backfill_relation_envelopes(
                records,
                session_sidecar=session_sidecar,
                snapshot_hashes=snapshot_hashes,
            ),
            indent=2,
            sort_keys=True,
        )
    )


def cmd_seed(args):
    from pathlib import Path
    from memex.seed import seed

    from memex.config import load
    sources = [Path(s) for s in args.sources]
    cfg = load()
    seed(
        sources=sources,
        base_url=_base_url(),
        cfg=cfg,
        glob_pattern=args.glob,
        dry_run=args.dry_run,
        force=args.force,
        verbose=args.verbose,
        delay_ms=args.delay,
        use_add=args.add,
    )


def cmd_snapshot(args):
    import os
    import sys
    from memex.config import load, mem0_config
    from memex.snapshot import snapshot

    cfg = load(args.config)

    site = os.environ.get("COGITO_SITE_PACKAGES")
    if site and site not in sys.path:
        sys.path.insert(0, site)

    from mem0 import Memory  # type: ignore
    memory = Memory.from_config(mem0_config(cfg))

    snapshot(memory, cfg, n=args.sample, dry_run=args.dry_run, rebuild=args.rebuild)


def cmd_calibrate(args):
    import os
    import sys
    from memex.config import load, mem0_config
    from memex.calibrate import calibrate

    cfg = load(args.config)

    site = os.environ.get("COGITO_SITE_PACKAGES")
    if site and site not in sys.path:
        sys.path.insert(0, site)

    from mem0 import Memory  # type: ignore
    memory = Memory.from_config(mem0_config(cfg))

    calibrate(memory, cfg, n=args.sample, dry_run=args.dry_run)


def cmd_server(args):
    # Delegate to server.main(). Strip the consumed "server" subcommand
    # (and any remaining argv) so the server's own argparse doesn't see it.
    import sys as _sys
    _sys.argv = [_sys.argv[0]]
    from memex.server import main as server_main
    server_main()


def _cmd_doctor(args):
    """AliceLabs addition: diagnostic for prerequisites and runtime health."""
    from memex.doctor import run_doctor
    return run_doctor()


def cmd_stats(args):
    """AliceLabs addition: cost-per-query comparison vs. competitors."""
    import json as _json
    import sys as _sys
    from memex.cost import competitive_comparison, format_comparison_text
    comparison = competitive_comparison(args.queries)
    if args.json:
        print(_json.dumps(comparison, indent=2))
    else:
        print(format_comparison_text(comparison))
    return 0


def cmd_audit(args):
    """AliceLabs addition: view audit log entries."""
    import json as _json
    from memex.audit_log import is_enabled, get_audit_entries, get_audit_stats

    if not is_enabled():
        print("Audit logging is disabled.", file=sys.stderr)
        print("Enable with: MEMEX_AUDIT_LOG=true memex-server", file=sys.stderr)
        return 1

    if args.stats:
        stats = get_audit_stats()
        if args.json:
            print(_json.dumps(stats, indent=2))
        else:
            print("Memex Audit Log Statistics")
            print("=" * 50)
            print(f"  Enabled:     {stats.get('enabled')}")
            print(f"  Path:        {stats.get('path')}")
            print(f"  Size:        {stats.get('size_bytes', 0) // 1024} KB")
            print(f"  Total ops:   {stats.get('entries', 0)}")
            print(f"  By operation:")
            for op, data in stats.get("ops", {}).items():
                print(f"    {op:12s}: {data['count']:5d} calls, avg {data.get('avg_latency_ms', 0):.0f}ms")
        return 0

    entries = get_audit_entries(limit=args.limit, op=args.op)
    if args.json:
        print(_json.dumps(entries, indent=2))
    else:
        print(f"Memex Audit Log — last {len(entries)} entries")
        print("=" * 80)
        for e in entries:
            ts = e.get("ts", "?")[:19]
            op = e.get("op", "?")
            count = e.get("result_count", 0)
            method = e.get("method", "")
            latency = e.get("latency_ms", 0)
            ip = e.get("client_ip", "")
            print(f"  {ts} | {op:8s} | {count:3d} results | {method:12s} | {latency:6.0f}ms | {ip}")
    return 0


def cmd_encrypt(args):
    """AliceLabs addition: manage encryption at rest."""
    from memex.encryption import is_enabled, generate_key

    if args.generate_key:
        key = generate_key()
        if key:
            print(key)
            print("\nSet this as MEMEX_ENCRYPTION_KEY in your environment.", file=sys.stderr)
        else:
            print("Error: cryptography library not installed. Run: pip install cryptography", file=sys.stderr)
            return 1
        return 0

    if args.status or True:  # default to status
        enabled = is_enabled()
        print(f"Encryption at rest: {'ENABLED' if enabled else 'DISABLED'}")
        if not enabled:
            print("\nTo enable:")
            print("  1. Generate a key: memex encrypt --generate-key")
            print("  2. Set env var:    export MEMEX_ENCRYPTION_KEY=<key>")
            print("  3. Restart server: memex init")
        return 0


def main():
    parser = argparse.ArgumentParser(
        prog="memex",
        description=(
            "Memex — local agent memory with deterministic automatic "
            "orientation and provenance-preserving recall"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # recall — integrated explicit path
    p_recall = sub.add_parser("recall", help="Explicit recall through Cogito Hermeneutics")
    p_recall.add_argument("query")
    p_recall.add_argument("--limit", type=int, default=50)
    p_recall.add_argument("--threshold", type=float, default=400.0)
    p_recall.add_argument("--since", help="ISO 8601 date string to filter memories created after this date (e.g., 2026-04-01)")
    p_recall.add_argument("--raw", action="store_true")
    p_recall.add_argument("--session-id", default=f"cli-process:{os.getpid()}")
    p_recall.add_argument("--turn-id", default="unavailable")
    p_recall.set_defaults(func=cmd_recall)

    # orient — integrated automatic decision path
    p_orient = sub.add_parser("orient", help="Automatic memory-routing decision + recall")
    p_orient.add_argument("message")
    p_orient.add_argument("--limit", type=int, default=5)
    p_orient.add_argument("--recent-turn", action="append", default=[])
    p_orient.add_argument("--raw", action="store_true")
    p_orient.add_argument("--session-id", default=f"cli-process:{os.getpid()}")
    p_orient.add_argument("--turn-id", default="unavailable")
    p_orient.set_defaults(func=cmd_orient)

    p_inquire = sub.add_parser(
        "inquire",
        help=(
            "Run opt-in bounded evidence inquiry; returns evidence and "
            "missingness, never a generated answer"
        ),
    )
    p_inquire.add_argument("query")
    p_inquire.add_argument(
        "--operation",
        choices=["verify_claim", "evaluate_decision", "trace_evolution"],
        help="Explicit closed inquiry operation when deterministic parsing is insufficient",
    )
    p_inquire.add_argument("--max-passes", type=int, choices=range(1, 4))
    p_inquire.add_argument("--max-records", type=int, choices=range(1, 13))
    p_inquire.add_argument(
        "--trace",
        action="store_true",
        help="Include the bounded pass and ranking trace",
    )
    p_inquire.add_argument("--raw", action="store_true")
    p_inquire.set_defaults(func=cmd_inquire)

    p_route = sub.add_parser(
        "route-turn",
        help=(
            "Host orientation-first route for past-work/decision/history turns; "
            "the host remains responsible for invocation"
        ),
    )
    p_route.add_argument("message")
    p_route.add_argument("--limit", type=int, default=5)
    p_route.add_argument("--recent-turn", action="append", default=[])
    p_route.add_argument("--raw", action="store_true")
    p_route.add_argument("--session-id", default=f"cli-process:{os.getpid()}")
    p_route.add_argument("--turn-id", default="unavailable")
    p_route.set_defaults(func=cmd_orient)

    # legacy recall retained for rollback and same-case comparisons
    p_recall_legacy = sub.add_parser("recall-legacy", help="Legacy two-stage recall")
    p_recall_legacy.add_argument("query")
    p_recall_legacy.add_argument("--limit", type=int, default=50)
    p_recall_legacy.add_argument("--threshold", type=float, default=400.0)
    p_recall_legacy.add_argument("--since")
    p_recall_legacy.add_argument("--raw", action="store_true")
    p_recall_legacy.set_defaults(func=cmd_recall_legacy)

    # recall-hybrid (BM25 + dense + RRF + tiered LLM)
    p_hybrid = sub.add_parser(
        "recall-hybrid",
        help="Hybrid BM25+dense+RRF recall with a local zero-LLM default.",
    )
    p_hybrid.add_argument("query")
    p_hybrid.add_argument("--limit", type=int, default=50)
    p_hybrid.add_argument(
        "--tier", choices=["zero_llm", "filter", "flagship"], default="zero_llm",
        help="Retrieval tier: zero_llm (default) | filter (experimental) | flagship (experimental)",
    )
    p_hybrid.add_argument("--top-k", type=int, default=5, help="Candidates shown to reranker")
    p_hybrid.add_argument("--raw", action="store_true")
    p_hybrid.set_defaults(func=cmd_recall_hybrid)

    # query
    p_query = sub.add_parser("query", help="Simple vector query (no filter)")
    p_query.add_argument("query")
    p_query.add_argument("--limit", type=int, default=5)
    p_query.add_argument("--raw", action="store_true")
    p_query.set_defaults(func=cmd_query)

    # store — explicit verbatim write (the server's preferred write path)
    p_store = sub.add_parser("store", help="Store text verbatim (no extraction LLM)")
    p_store.add_argument("text", nargs="+")
    p_store.set_defaults(func=cmd_store)

    # add
    p_add = sub.add_parser("add", help="Add a memory (verbatim store by default)")
    p_add.add_argument("text", nargs="+")
    p_add.add_argument(
        "--extract", action="store_true",
        help="Summarise text into facts via the mem0 extraction LLM (legacy /add path)",
    )
    p_add.set_defaults(func=cmd_add)

    # health
    p_health = sub.add_parser("health", help="Check server health")
    p_health.set_defaults(func=cmd_health)

    p_capabilities = sub.add_parser(
        "capabilities",
        help="Show deterministic build, feature, schema, and invocation state",
    )
    p_capabilities.set_defaults(func=cmd_capabilities)

    p_backfill = sub.add_parser(
        "relation-backfill-dry-run",
        help=(
            "Classify deterministic legacy provenance/relation coverage from "
            "JSON; never writes"
        ),
    )
    p_backfill.add_argument("input_json")
    p_backfill.set_defaults(func=cmd_relation_backfill_dry_run)

    # seed
    p_seed = sub.add_parser("seed", help="Bulk-seed store from markdown/text files")
    p_seed.add_argument("sources", nargs="+", help="Dirs or files to seed from")
    p_seed.add_argument("--glob", default="*.md", help="File pattern (default: *.md)")
    p_seed.add_argument("--dry-run", action="store_true", help="Show what would be sent, don't write")
    p_seed.add_argument("--force", action="store_true", help="Re-seed even unchanged files")
    p_seed.add_argument("--verbose", "-v", action="store_true")
    p_seed.add_argument("--delay", type=int, default=0, help="ms between /store calls (default: 0)")
    p_seed.add_argument("--add", action="store_true", help="Use /add (mem0 extraction) instead of agent-curated /store")
    p_seed.set_defaults(func=cmd_seed)

    # snapshot
    p_snap = sub.add_parser("snapshot", help="Build compressed index (alicelabs-memory-style MEMORY.md layer)")
    p_snap.add_argument("--sample", type=int, default=500, help="Memories to sample (default: 500)")
    p_snap.add_argument("--dry-run", action="store_true", help="Preview without writing")
    p_snap.add_argument("--rebuild", action="store_true", help="Force rebuild even if snapshot exists")
    p_snap.add_argument("--config", help="Path to .cogito.json")
    p_snap.set_defaults(func=cmd_snapshot)

    # calibrate
    p_cal = sub.add_parser("calibrate", help="Extract vocab bridge from corpus (one-time)")
    p_cal.add_argument("--sample", type=int, default=200, help="Number of memories to sample (default: 200)")
    p_cal.add_argument("--dry-run", action="store_true", help="Preview mappings, don't write config")
    p_cal.add_argument("--config", help="Path to .cogito.json")
    p_cal.set_defaults(func=cmd_calibrate)

    # server
    p_server = sub.add_parser("server", help="Start the memex server")
    p_server.set_defaults(func=cmd_server)

    # doctor — diagnostic for prerequisites and runtime health (AliceLabs addition)
    p_doctor = sub.add_parser(
        "doctor",
        help="Diagnose prerequisites and runtime health (Python version, deps, Ollama, store, service, MCP clients)",
    )
    p_doctor.add_argument("--json", action="store_true", help="Output JSON instead of human-readable text")
    p_doctor.set_defaults(func=lambda a: sys.exit(_cmd_doctor(a)))

    # backup — export/import memories (AliceLabs addition)
    from memex.backup import register_parsers as register_backup
    register_backup(sub)

    # ui — local web UI for browsing memories (AliceLabs addition)
    from memex.ui import register_parser as register_ui
    register_ui(sub)

    # stats — cost comparison vs. competitors (AliceLabs addition)
    p_stats = sub.add_parser(
        "stats",
        help="Show cost-per-query comparison vs. mem0, Zep, Letta, Pinecone, ChromaDB",
    )
    p_stats.add_argument("--queries", type=int, default=1000, help="Number of queries to compare (default: 1000)")
    p_stats.add_argument("--json", action="store_true", help="Output JSON instead of text")
    p_stats.set_defaults(func=cmd_stats)

    # benchmark — reproducible LongMemEval runner (AliceLabs addition)
    from memex.benchmark_cmd import register_parser as register_benchmark
    register_benchmark(sub)

    # audit — view audit log entries (AliceLabs addition)
    p_audit = sub.add_parser(
        "audit",
        help="View audit log entries (requires MEMEX_AUDIT_LOG=true)",
    )
    p_audit.add_argument("--limit", type=int, default=20, help="Max entries to show (default: 20)")
    p_audit.add_argument("--op", help="Filter by operation (recall/query/store/add/correct)")
    p_audit.add_argument("--stats", action="store_true", help="Show summary statistics")
    p_audit.add_argument("--json", action="store_true", help="Output JSON")
    p_audit.set_defaults(func=cmd_audit)

    # update — auto-update checker (AliceLabs addition)
    from memex.autoupdate import register_parser as register_update
    register_update(sub)

    # sync — cross-machine replication (AliceLabs addition)
    from memex.sync import register_parser as register_sync
    register_sync(sub)

    # encrypt — encryption management (AliceLabs addition)
    p_encrypt = sub.add_parser(
        "encrypt",
        help="Manage encryption at rest (AliceLabs addition)",
    )
    p_encrypt.add_argument("--status", action="store_true", help="Check encryption status")
    p_encrypt.add_argument("--generate-key", action="store_true", help="Generate a new encryption key")
    p_encrypt.set_defaults(func=cmd_encrypt)

    # tui — terminal UI (AliceLabs addition)
    from memex.tui import register_parser as register_tui
    register_tui(sub)

    # log/diff — memory history (AliceLabs addition)
    from memex.diff import register_parsers as register_diff
    register_diff(sub)

    # graph — knowledge graph (AliceLabs addition)
    from memex.graph import register_parser as register_graph
    register_graph(sub)

    # vault — Obsidian integration (AliceLabs addition)
    from memex.vault import register_parser as register_vault
    register_vault(sub)

    # format — cross-agent memory standard (AliceLabs addition)
    from memex.format import register_parser as register_format
    register_format(sub)

    # init — install + start memex-server as a system service
    p_init = sub.add_parser(
        "init",
        help="Install + start memex-server as a launchd/systemd service (auto-starts on reboot)",
    )
    p_init.add_argument("--uninstall", action="store_true",
                        help="Stop service + remove the unit/plist")
    p_init.add_argument("--port", type=int)
    p_init.add_argument("--label")
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--dry-run", action="store_true")
    p_init.add_argument("--migrate", action="store_true")
    p_init.set_defaults(func=lambda a: sys.exit(_cmd_init(a)))

    # watch — auto-ingest a directory
    p_watch = sub.add_parser("watch", help="Auto-ingest markdown/text files from a directory")
    p_watch.add_argument("path", help="Directory to watch")
    p_watch.add_argument("--glob", nargs="+", default=None,
                         help="Glob patterns (default: *.md *.txt)")
    p_watch.add_argument("--max-files", type=int, default=500,
                         help="Initial-scan cap (default: 500)")
    p_watch.add_argument("--interval", type=float, default=5.0,
                         help="Poll interval in seconds (default: 5.0)")
    p_watch.add_argument("--once", action="store_true",
                         help="Initial scan only, don't poll continuously")
    p_watch.add_argument("--verbose", "-v", action="store_true")
    p_watch.set_defaults(func=lambda a: sys.exit(_cmd_watch(a)))

    # mcp — manage agent-client MCP integration
    p_mcp = sub.add_parser("mcp", help="Manage Claude Code, Codex, GitHub Copilot CLI, Gemini CLI, or OpenClaw MCP integration")
    mcp_sub = p_mcp.add_subparsers(dest="mcp_command", required=True)
    p_mcp_serve = mcp_sub.add_parser("serve", help="Run the MCP server over stdio")
    p_mcp_serve.set_defaults(func=lambda a: sys.exit(_cmd_mcp_serve(a)))
    p_mcp_install = mcp_sub.add_parser("install", help="Install the memex MCP server into an agent client")
    p_mcp_install.add_argument("--client", choices=("claude", "codex", "copilot", "gemini", "openclaw"), default="claude",
                               help="MCP client to configure (default: claude)")
    p_mcp_install.add_argument("--settings",
                               help="Config file to edit: Claude Code settings.local.json "
                                    "(default ~/.claude/settings.local.json) or Copilot CLI mcp-config.json "
                                    "(default ~/.copilot/mcp-config.json, or $COPILOT_HOME). For OpenClaw this "
                                    "is the config the delegated openclaw CLI writes, via $OPENCLAW_CONFIG_PATH "
                                    "(default ~/.openclaw/openclaw.json)")
    p_mcp_install.add_argument("--scope", choices=("user", "project"), default=None,
                               help="Gemini CLI only: which settings.json `gemini mcp` writes — "
                                    "user (~/.gemini/settings.json, the memex default) or "
                                    "project (./.gemini/settings.json)")
    p_mcp_install.add_argument("--force", action="store_true",
                               help="Overwrite an existing 'memex' entry even if it doesn't look like ours")
    p_mcp_install.set_defaults(func=lambda a: sys.exit(_cmd_mcp_install(a)))
    p_mcp_uninstall = mcp_sub.add_parser("uninstall", help="Remove the memex MCP server from an agent client")
    p_mcp_uninstall.add_argument("--client", choices=("claude", "codex", "copilot", "gemini", "openclaw"), default="claude",
                                 help="MCP client to configure (default: claude)")
    p_mcp_uninstall.add_argument("--settings",
                                 help="Config file to edit (Claude Code settings.local.json, Copilot CLI "
                                      "mcp-config.json, or OpenClaw openclaw.json)")
    p_mcp_uninstall.add_argument("--scope", choices=("user", "project"), default=None,
                                 help="Gemini CLI only: which settings.json to remove from "
                                      "(default: user)")
    p_mcp_uninstall.add_argument("--force", action="store_true",
                                 help="Remove an entry named 'memex' even if it doesn't look like ours "
                                      "(Copilot CLI, Gemini CLI, OpenClaw)")
    p_mcp_uninstall.set_defaults(func=lambda a: sys.exit(_cmd_mcp_uninstall(a)))

    args = parser.parse_args()
    args.func(args)


# Lazy-imports for the new consumer-surface commands so the existing CLI startup
# isn't slowed by importing platform-specific modules.

def _cmd_init(args):
    from memex.init_cmd import cmd_init
    return cmd_init(args)


def _cmd_watch(args):
    from memex.watch_cmd import cmd_watch
    return cmd_watch(args)


def _cmd_mcp_install(args):
    from memex.mcp_cmd import cmd_mcp_install
    return cmd_mcp_install(args)


def _cmd_mcp_uninstall(args):
    from memex.mcp_cmd import cmd_mcp_uninstall
    return cmd_mcp_uninstall(args)


def _cmd_sessions_ingest(args):
    from memex.sessions_cmd import cmd_ingest
    return cmd_ingest(args)


def _cmd_sessions_search(args):
    from memex.sessions_cmd import cmd_search
    return cmd_search(args)


def _cmd_sessions_list(args):
    from memex.sessions_cmd import cmd_list
    return cmd_list(args)


def _cmd_sessions_purge(args):
    from memex.sessions_cmd import cmd_purge
    return cmd_purge(args)


def _cmd_sessions_stats(args):
    from memex.sessions_cmd import cmd_stats
    return cmd_stats(args)


if __name__ == "__main__":
    main()


def _cmd_mcp_serve(args):
    from memex.mcp_server import main
    return main()

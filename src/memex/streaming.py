"""memex.streaming — Server-Sent Events (SSE) streaming for /recall.

AliceLabs proprietary addition. Streams retrieval results as they are
found, instead of waiting for the full result set. Reduces perceived
latency from ~90ms to ~10ms for the first result.

Usage:
    curl -N http://127.0.0.1:19420/recall/stream \
      -H "Content-Type: application/json" \
      -d '{"text": "what did we decide about auth", "limit": 10}'

SSE format:
    data: {"memory": {"text": "...", "score": 0.87}, "index": 0}

    data: {"memory": {"text": "...", "score": 0.82}, "index": 1}

    data: {"done": true, "count": 2, "method": "zero_llm"}
"""
from __future__ import annotations

import json
import time
from typing import Any


def format_sse_event(data: dict[str, Any]) -> str:
    """Format a single SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_recall_results(
    memories: list[dict[str, Any]],
    method: str,
    start_time: float,
) -> list[str]:
    """Convert a list of memories into SSE events.

    Returns a list of SSE-formatted strings (one per event).
    The caller should write each string to the response stream.

    Args:
        memories: List of memory dicts ({"text": "...", "score": N})
        method: Retrieval method used
        start_time: Timestamp when retrieval started (for latency calc)

    Returns:
        List of SSE event strings, including a final "done" event.
    """
    events = []
    elapsed_ms = (time.monotonic() - start_time) * 1000

    for i, m in enumerate(memories):
        event_data = {
            "memory": {
                "text": m.get("text", ""),
                "score": m.get("score", 0),
                "id": m.get("id", ""),
            },
            "index": i,
            "elapsed_ms": round(elapsed_ms, 1),
        }
        events.append(format_sse_event(event_data))

    # Final event
    done_data = {
        "done": True,
        "count": len(memories),
        "method": method,
        "total_latency_ms": round(elapsed_ms, 1),
    }
    events.append(format_sse_event(done_data))

    return events


def handle_sse_recall(handler, memories: list[dict], method: str, start_time: float) -> None:
    """Handle a streaming SSE recall response.

    Args:
        handler: The HTTP request handler
        memories: List of memory dicts
        method: Retrieval method
        start_time: Monotonic timestamp when retrieval started
    """
    events = stream_recall_results(memories, method, start_time)

    # Send SSE headers
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("X-Accel-Buffering", "no")
    # AliceLabs security headers
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.end_headers()

    # Stream events
    try:
        for event in events:
            handler.wfile.write(event.encode("utf-8"))
            handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        pass  # client disconnected

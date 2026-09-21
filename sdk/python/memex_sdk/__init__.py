"""Memex Python SDK — local-first, zero-LLM agent memory.

Official Python client for Memex. Same API as the TypeScript SDK.

Usage:
    from memex_sdk import MemexClient

    client = MemexClient(base_url="http://127.0.0.1:19420")
    client.store("We decided to use JWT with 3600s expiry.")
    result = client.recall("what did we decide about auth")
    for m in result["memories"]:
        print(m["text"])
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional


class MemexError(Exception):
    """Memex API error."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class MemexClient:
    """Client for the Memex agent memory server.

    Args:
        base_url: Server URL (default: http://127.0.0.1:19420)
        api_token: Bearer token for auth (default: from MEMEX_API_TOKEN env)
        timeout: Request timeout in seconds (default: 30)
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:19420",
        api_token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token or os.environ.get("MEMEX_API_TOKEN")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _get(self, path: str) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                error = json.loads(e.read())
                raise MemexError(error.get("error", str(e)), e.code)
            except json.JSONDecodeError:
                raise MemexError(str(e), e.code)
        except urllib.error.URLError as e:
            raise MemexError(f"server unreachable: {e}") from e

    def _post(self, path: str, payload: dict) -> dict[str, Any]:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                error = json.loads(e.read())
                raise MemexError(error.get("error", str(e)), e.code)
            except json.JSONDecodeError:
                raise MemexError(str(e), e.code)
        except urllib.error.URLError as e:
            raise MemexError(f"server unreachable: {e}") from e

    def health(self) -> dict[str, Any]:
        """Check server health. Returns status, count, queued, version."""
        return self._get("/health")

    def store(self, text: str, memory_id: Optional[str] = None) -> dict[str, Any]:
        """Store a memory verbatim. No LLM call.

        Args:
            text: The memory text to store.
            memory_id: Optional memory ID (UUID).

        Returns:
            Store result with id and text.
        """
        payload: dict[str, Any] = {"text": text}
        if memory_id:
            payload["id"] = memory_id
        return self._post("/store", payload)

    def add(self, text: str) -> dict[str, Any]:
        """Add raw text via extraction LLM (calls an LLM).

        Note: This calls an LLM for extraction. Use store() for zero-LLM writes.

        Args:
            text: Raw unstructured text to extract memories from.

        Returns:
            Result with count and extracted memories.
        """
        return self._post("/add", {"text": text})

    def recall(
        self,
        query: str,
        limit: int = 50,
        threshold: Optional[float] = None,
        since: Optional[str] = None,
    ) -> dict[str, Any]:
        """Recall memories for a query. Two-stage retrieval. Zero-LLM default.

        Args:
            query: Natural-language query.
            limit: Max results (default: 50).
            threshold: Score threshold.
            since: ISO 8601 date filter.

        Returns:
            Recall result with memories and method.
        """
        payload: dict[str, Any] = {"text": query, "limit": limit}
        if threshold is not None:
            payload["threshold"] = threshold
        if since:
            payload["since"] = since
        return self._post("/recall", payload)

    def recall_hybrid(
        self,
        query: str,
        tier: str = "zero_llm",
        limit: int = 50,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Hybrid recall: BM25 + dense + RRF with tiered LLM escalation.

        Args:
            query: Natural-language query.
            tier: Retrieval tier — zero_llm | filter | flagship.
            limit: Max results.
            top_k: Candidates for reranker.

        Returns:
            Recall result with memories and method.
        """
        return self._post("/recall_hybrid", {
            "text": query,
            "limit": limit,
            "tier": tier,
            "top_k": top_k,
        })

    def query(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Simple vector query (no filter, no LLM).

        Args:
            query: Search query.
            limit: Max results (default: 5).

        Returns:
            Query result with memories.
        """
        return self._post("/query", {"text": query, "limit": limit})

    def export(self) -> dict[str, Any]:
        """Export all memories for backup. No LLM call.

        Returns:
            Export payload with version, timestamp, memory_count, memories.
        """
        return self._get("/export")

    def stats(self) -> dict[str, Any]:
        """Get server stats including cost comparison vs competitors.

        Returns:
            Stats with store counts, queue depth, and cost comparison.
        """
        return self._get("/stats")


def memex(
    base_url: str = "http://127.0.0.1:19420",
    api_token: Optional[str] = None,
    timeout: int = 30,
) -> MemexClient:
    """Create a MemexClient instance with defaults.

    Usage:
        from memex_sdk import memex
        client = memex()
        client.store("hello")
    """
    return MemexClient(base_url=base_url, api_token=api_token, timeout=timeout)

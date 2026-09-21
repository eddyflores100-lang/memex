"""memex.auth — API token authentication for the HTTP server.

AliceLabs proprietary addition. Provides bearer token authentication
for the memex HTTP API. When MEMEX_API_TOKEN is set, all requests
(except /health and /live) must include a valid Authorization header.

Usage in server.py:
    from memex.auth import check_auth, AUTH_ENABLED
    if not check_auth(self.headers):
        self._json({"error": "unauthorized"}, 401)
        return

Configuration:
    Set MEMEX_API_TOKEN environment variable to enable auth.
    Leave unset for no auth (loopback-only default).

    [auth]
    token = "your-secret-token-here"
    enabled = true
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any

# Endpoints that don't require auth (health checks, liveness)
PUBLIC_ENDPOINTS = {"/health", "/live", "/capabilities"}

# Token cache (avoid re-reading config on every request)
_cached_token: str | None = None
_cached_token_hash: bytes | None = None
_last_check: float = 0.0
_CACHE_TTL = 60.0  # re-read config every 60s


def _get_configured_token() -> str | None:
    """Get the API token from env var or config file."""
    global _cached_token, _cached_token_hash, _last_check

    now = time.monotonic()
    if _cached_token is not None and (now - _last_check) < _CACHE_TTL:
        return _cached_token

    # Check env var first
    token = os.environ.get("MEMEX_API_TOKEN")

    # Check config file
    if not token:
        try:
            from memex.config import load
            cfg = load()
            token = cfg.get("api_token") or cfg.get("auth", {}).get("token")
        except Exception:
            pass

    if token and token != _cached_token:
        _cached_token = token
        _cached_token_hash = hashlib.sha256(token.encode()).digest()

    _last_check = now
    return _cached_token


def auth_enabled() -> bool:
    """Check if auth is enabled."""
    return _get_configured_token() is not None


def check_auth(headers) -> bool:
    """Check if the request has valid authentication.

    Args:
        headers: HTTP request headers (from BaseHTTPRequestHandler)

    Returns:
        True if auth is disabled or token is valid, False otherwise.
    """
    token = _get_configured_token()
    if not token:
        return True  # auth disabled

    # Extract Bearer token from Authorization header
    auth_header = headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    provided_token = auth_header[7:]  # strip "Bearer "

    # Constant-time comparison to prevent timing attacks
    provided_hash = hashlib.sha256(provided_token.encode()).digest()
    expected_hash = _cached_token_hash or hashlib.sha256(token.encode()).digest()

    return hmac.compare_digest(provided_hash, expected_hash)


def generate_token() -> str:
    """Generate a secure random API token."""
    return f"memex_{secrets.token_urlsafe(32)}"


def middleware_check(handler, path: str) -> bool:
    """Middleware that checks auth for a given path.

    Args:
        handler: The HTTP request handler
        path: The request path

    Returns:
        True if the request should proceed, False if it was rejected.
    """
    # Skip auth for public endpoints
    if path in PUBLIC_ENDPOINTS:
        return True

    # Skip auth if not enabled
    if not auth_enabled():
        return True

    # Check auth
    if not check_auth(handler.headers):
        handler._json({
            "error": "unauthorized",
            "message": "MEMEX_API_TOKEN is set. Include 'Authorization: Bearer <token>' header.",
        }, 401)
        return False

    return True

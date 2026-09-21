"""memex.request_validation — harden HTTP request validation.

AliceLabs proprietary addition. Provides:
  - Strict Content-Type validation
  - CORS policy enforcement
  - Request body schema validation
  - Query length limits (prevent DoS via long queries)
  - User ID validation (prevent injection via user_id field)

Usage in server.py:
    from memex.request_validation import validate_request, validate_query_length
    error = validate_request(self)
    if error:
        self._json({"error": error}, 400)
        return
"""
from __future__ import annotations

import os
import re

# Maximum query length (prevents DoS via extremely long queries)
MAX_QUERY_LENGTH = 10_000

# Maximum number of memories per request
MAX_LIMIT = 500

# Allowed Content-Types for POST
ALLOWED_CONTENT_TYPES = {"application/json", "application/json; charset=utf-8"}

# CORS origins (empty = no CORS, loopback only)
# Set MEMEX_CORS_ORIGIN to allow specific origins (e.g., http://localhost:3000)
_CORS_ORIGIN = os.environ.get("MEMEX_CORS_ORIGIN", "")

# User ID validation pattern (alphanumeric + dash + underscore, max 64 chars)
_USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_content_type(headers) -> str | None:
    """Validate that the Content-Type is application/json.

    Returns None if valid, or an error message string.
    """
    ct = headers.get("Content-Type", "")
    if ct not in ALLOWED_CONTENT_TYPES:
        return f"Content-Type must be application/json (got: {ct})"
    return None


def validate_query_length(text: str, max_length: int = MAX_QUERY_LENGTH) -> str | None:
    """Validate that a query is within length limits.

    Returns None if valid, or an error message string.
    """
    if len(text) > max_length:
        return f"Query too long: {len(text)} chars (max {max_length})"
    return None


def validate_limit(limit: int) -> str | None:
    """Validate that a limit value is within bounds."""
    if limit < 1:
        return "limit must be >= 1"
    if limit > MAX_LIMIT:
        return f"limit too high: {limit} (max {MAX_LIMIT})"
    return None


def validate_user_id(user_id: str) -> str | None:
    """Validate user_id format to prevent injection.

    Returns None if valid, or an error message string.
    """
    if not user_id:
        return None  # empty is OK (uses default)
    if not _USER_ID_PATTERN.match(user_id):
        return "invalid user_id: must be alphanumeric, dash, or underscore (max 64 chars)"
    return None


def validate_text_field(text: str, min_length: int = 3, max_length: int = MAX_QUERY_LENGTH) -> str | None:
    """Validate a text field for store/recall operations."""
    if not text:
        return "text field is required"
    text = text.strip()
    if len(text) < min_length:
        return f"text must be at least {min_length} characters"
    if len(text) > max_length:
        return f"text too long: {len(text)} chars (max {max_length})"
    # Check for null bytes (injection attempt)
    if "\x00" in text:
        return "text contains null bytes"
    return None


def get_cors_headers() -> dict[str, str]:
    """Return CORS headers if MEMEX_CORS_ORIGIN is set."""
    if not _CORS_ORIGIN:
        return {}
    return {
        "Access-Control-Allow-Origin": _CORS_ORIGIN,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "3600",
    }


def handle_preflight(handler) -> bool:
    """Handle CORS preflight (OPTIONS) request. Returns True if handled."""
    if handler.command != "OPTIONS":
        return False
    if not _CORS_ORIGIN:
        return False

    handler.send_response(204)
    for k, v in get_cors_headers().items():
        handler.send_header(k, v)
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return True


def sanitize_for_log(text: str, max_len: int = 100) -> str:
    """Sanitize text for logging — truncate and remove control chars."""
    if not text:
        return ""
    # Remove control characters except newline and tab
    sanitized = "".join(c for c in text if c == "\n" or c == "\t" or ord(c) >= 32)
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "..."
    return sanitized

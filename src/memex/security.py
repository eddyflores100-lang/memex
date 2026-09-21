"""memex.security — rate limiting and security headers for the HTTP server.

AliceLabs proprietary addition. Provides:
  - RateLimiter: per-IP request rate limiting (token bucket)
  - SecurityHeaders: middleware that adds standard security headers

Usage in server.py:
    from memex.security import RateLimiter, security_headers
    limiter = RateLimiter(max_requests=60, window_seconds=60)
    # In handler:
    if not limiter.check(self.client_address[0]):
        self._json({"error": "rate limit exceeded"}, 429)
        return
    security_headers(self)
"""
from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from typing import Deque


class RateLimiter:
    """Per-IP rate limiter using sliding window.

    Args:
        max_requests: Maximum requests per window per IP.
        window_seconds: Time window in seconds.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, ip: str) -> bool:
        """Check if the IP is within the rate limit. Returns True if allowed."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Prune old entries
            requests = self._requests[ip]
            while requests and requests[0] < cutoff:
                requests.popleft()

            if len(requests) >= self.max_requests:
                return False

            requests.append(now)
            return True

    def remaining(self, ip: str) -> int:
        """Return remaining requests for the IP in the current window."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            requests = self._requests[ip]
            while requests and requests[0] < cutoff:
                requests.popleft()
            return max(0, self.max_requests - len(requests))

    def reset(self, ip: str | None = None) -> None:
        """Reset rate limit state for an IP (or all IPs if None)."""
        with self._lock:
            if ip:
                self._requests.pop(ip, None)
            else:
                self._requests.clear()


# Default rate limiter: 60 requests per minute per IP
_default_limiter = RateLimiter(max_requests=60, window_seconds=60)


def check_rate_limit(ip: str, max_requests: int = 60, window: int = 60) -> bool:
    """Check rate limit using the default limiter. Returns True if allowed."""
    return _default_limiter.check(ip)


def get_rate_limit_remaining(ip: str) -> int:
    """Get remaining requests for the IP in the current window."""
    return _default_limiter.remaining(ip)


def add_security_headers(handler) -> None:
    """Add standard security headers to the HTTP response.

    Call this BEFORE send_header/end_headers in the handler.
    """
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("X-XSS-Protection", "1; mode=block")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Server", "memex-alicelabs")


def sanitize_log_input(text: str, max_length: int = 200) -> str:
    """Sanitize user input for logging — truncate and remove newlines.

    Prevents log injection (CRLF) and excessive log lines.
    """
    if not text:
        return ""
    # Remove newlines to prevent log injection
    sanitized = text.replace("\n", " ").replace("\r", " ")
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized

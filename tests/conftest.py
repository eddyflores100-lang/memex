"""Shared test configuration for the memex test suite.

Two jobs:
  1. Disable the HTTP per-IP rate limiter for the whole session. The suite
     runs the real in-process HTTP handler and issues hundreds of requests
     from 127.0.0.1 in well under a minute; the production default of
     60 req/min would starve every later test of budget (observed as ~78
     spurious 429 failures across the acceptance suites).
  2. Reset the module-level limiter state around every test so a burst in
     one test cannot poison the next one.
"""
from __future__ import annotations

import os

import pytest

# Tests are not exercising the limiter itself; production deployments keep
# the default unless they set MEMEX_RATE_LIMIT_MAX themselves.
os.environ.setdefault("MEMEX_RATE_LIMIT_MAX", "0")

from memex import security as _security  # noqa: E402  (env must be set first)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    _security._default_limiter.reset()
    yield
    _security._default_limiter.reset()

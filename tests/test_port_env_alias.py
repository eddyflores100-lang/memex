"""MEMEX_PORT must move the server, not just the clients.

`cli`, `mcp_server`, `watch_cmd`, and `augment` all resolve their target port
as MEMEX_PORT first, MEMEX_PORT second. The server resolves its bind port
through `config.load`. When that map knew only MEMEX_PORT, setting
MEMEX_PORT moved every client off a server that stayed on 19420 — the
documented alias produced a split brain instead of an override.
"""

import pytest

from memex.config import load

MISSING = "/nonexistent/path/.cogito.json"


@pytest.fixture(autouse=True)
def _clear_port_env(monkeypatch):
    monkeypatch.delenv("MEMEX_PORT", raising=False)
    monkeypatch.delenv("MEMEX_PORT", raising=False)


def test_server_port_defaults_to_19420():
    assert load(config_path=MISSING)["port"] == 19420


def test_memex_port_overrides_the_server_bind_port(monkeypatch):
    monkeypatch.setenv("MEMEX_PORT", "19477")
    assert load(config_path=MISSING)["port"] == 19477


def test_cogito_port_still_overrides_the_server_bind_port(monkeypatch):
    monkeypatch.setenv("MEMEX_PORT", "19478")
    assert load(config_path=MISSING)["port"] == 19478


def test_memex_port_wins_when_both_are_set(monkeypatch):
    """Same precedence the clients use, so both ends agree on one port."""
    monkeypatch.setenv("MEMEX_PORT", "19478")
    monkeypatch.setenv("MEMEX_PORT", "19477")
    assert load(config_path=MISSING)["port"] == 19477


def test_server_and_mcp_client_resolve_the_same_port(monkeypatch):
    from memex import mcp_server

    monkeypatch.setenv("MEMEX_PORT", "19477")
    assert mcp_server._server_url() == f"http://127.0.0.1:{load(config_path=MISSING)['port']}"

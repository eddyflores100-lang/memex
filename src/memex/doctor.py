"""memex doctor — diagnostic command for prerequisites and runtime health.

Checks:
  1. Python version
  2. Required dependencies (mem0, chromadb, ollama python client)
  3. Ollama server reachability
  4. Embedding model availability
  5. Store path writability
  6. Service config status (launchd/systemd)
  7. Memory count and queue depth
  8. MCP client configs (Claude, Codex, Copilot, Gemini, OpenClaw)

Exit codes:
  0 — all checks passed
  1 — one or more checks failed (with details on stdout)
  2 — could not run checks (e.g., cannot load config)
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from memex import __version__
from memex.config import load


def _check_python_version() -> dict[str, Any]:
    v = sys.version_info
    ok = v >= (3, 10)
    return {
        "check": "python_version",
        "ok": ok,
        "version": f"{v.major}.{v.minor}.{v.micro}",
        "minimum": "3.10",
        "fix": "Install Python 3.10 or newer" if not ok else None,
    }


def _check_dependencies() -> dict[str, Any]:
    missing = []
    for pkg in ("mem0", "chromadb", "ollama"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return {
        "check": "dependencies",
        "ok": not missing,
        "missing": missing,
        "fix": f"pip install {' '.join(missing)}" if missing else None,
    }


def _check_ollama_reachable(ollama_url: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        return {
            "check": "ollama_reachable",
            "ok": True,
            "url": ollama_url,
            "models": models,
        }
    except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
        return {
            "check": "ollama_reachable",
            "ok": False,
            "url": ollama_url,
            "error": str(e),
            "fix": "Start Ollama: `ollama serve` (macOS: `brew install ollama && ollama serve`)",
        }


def _check_embedding_model(ollama_url: str, embed_model: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        models = [m.get("name", "") for m in data.get("models", [])]
        ok = any(embed_model in m for m in models)
        return {
            "check": "embedding_model",
            "ok": ok,
            "model": embed_model,
            "available_models": models,
            "fix": f"Pull the model: `ollama pull {embed_model}`" if not ok else None,
        }
    except Exception as e:
        return {
            "check": "embedding_model",
            "ok": False,
            "model": embed_model,
            "error": str(e),
        }


def _check_store_writable(store_path: str) -> dict[str, Any]:
    p = Path(store_path).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".memex_write_test"
        test_file.write_text("ok")
        test_file.unlink()
        return {
            "check": "store_writable",
            "ok": True,
            "path": str(p),
        }
    except Exception as e:
        return {
            "check": "store_writable",
            "ok": False,
            "path": str(p),
            "error": str(e),
            "fix": f"chmod or chown the directory: {p}",
        }


def _check_service_installed() -> dict[str, Any]:
    if sys.platform == "darwin":
        plist = Path.home() / "Library/LaunchAgents/ai.eddyflores100-lang.memex-server.plist"
        ok = plist.exists()
        return {
            "check": "service_installed",
            "ok": ok,
            "platform": "macOS",
            "plist_path": str(plist),
            "fix": "Run `memex init` to install the launchd service" if not ok else None,
        }
    elif sys.platform.startswith("linux"):
        unit = Path.home() / ".config/systemd/user/memex-server.service"
        ok = unit.exists()
        return {
            "check": "service_installed",
            "ok": ok,
            "platform": "Linux",
            "unit_path": str(unit),
            "fix": "Run `memex init` to install the systemd service" if not ok else None,
        }
    else:
        return {
            "check": "service_installed",
            "ok": False,
            "platform": sys.platform,
            "error": "Platform not supported for service install",
        }


def _check_server_alive(port: int) -> dict[str, Any]:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read())
        return {
            "check": "server_alive",
            "ok": True,
            "port": port,
            "status": data.get("status"),
            "memory_count": data.get("count"),
            "queue_depth": data.get("queued"),
            "version": data.get("version"),
        }
    except Exception as e:
        return {
            "check": "server_alive",
            "ok": False,
            "port": port,
            "error": str(e),
            "fix": f"Start the server: `memex-server` or `memex init` if not installed",
        }


def _check_mcp_clients() -> dict[str, Any]:
    clients = {}
    paths = {
        "claude": Path.home() / ".claude/settings.local.json",
        "codex": Path.home() / ".codex/config.toml",
        "copilot": Path.home() / ".copilot/mcp-config.json",
        "gemini": Path.home() / ".gemini/settings.json",
        "openclaw": Path.home() / ".openclaw/openclaw.json",
    }
    for name, path in paths.items():
        clients[name] = {
            "configured": path.exists(),
            "path": str(path),
        }
    return {
        "check": "mcp_clients",
        "ok": any(c["configured"] for c in clients.values()),
        "clients": clients,
        "fix": "Run `memex mcp install --client <name>` to configure a client" if not any(c["configured"] for c in clients.values()) else None,
    }


def run_doctor() -> int:
    """Run all diagnostic checks. Returns exit code (0 = ok, 1 = issues)."""
    try:
        cfg = load()
    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": f"Could not load config: {e}",
        }, indent=2))
        return 2

    ollama_url = cfg.get("ollama_url", "http://127.0.0.1:11434")
    embed_model = cfg.get("embed_model", "nomic-embed-text")
    store_path = cfg.get("store_path", str(Path.home() / ".cogito/store"))
    port = cfg.get("port", 19420)

    results = [
        _check_python_version(),
        _check_dependencies(),
        _check_ollama_reachable(ollama_url),
        _check_embedding_model(ollama_url, embed_model),
        _check_store_writable(store_path),
        _check_service_installed(),
        _check_server_alive(port),
        _check_mcp_clients(),
    ]

    all_ok = all(r.get("ok", False) for r in results)

    if "--json" in sys.argv:
        print(json.dumps({
            "ok": all_ok,
            "version": __version__,
            "checks": results,
        }, indent=2))
    else:
        print(f"Memex doctor v{__version__}")
        print("=" * 50)
        for r in results:
            status = "OK" if r.get("ok") else "FAIL"
            print(f"  [{status}] {r['check']}")
            if not r.get("ok"):
                for k, v in r.items():
                    if k not in ("check", "ok") and v is not None:
                        print(f"         {k}: {v}")
                if r.get("fix"):
                    print(f"         fix: {r['fix']}")
        print("=" * 50)
        print(f"Overall: {'ALL OK' if all_ok else 'ISSUES FOUND'}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run_doctor())

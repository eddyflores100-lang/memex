"""memex ui — local web UI for browsing memories.

AliceLabs proprietary addition. Starts a simple HTTP server that serves
a single-page app for browsing, searching, and managing memories.

Usage:
    memex ui                    # start UI on port 19421
    memex ui --port 8080        # use custom port
    memex ui --no-browser       # don't open browser automatically

The UI talks to the running memex-server (default :19420) via HTTP.
No external dependencies — pure Python stdlib + inline HTML/JS.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Memex — AliceLabs UI</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; }
.header { background: #161b22; padding: 16px 24px; border-bottom: 1px solid #30363d;
          display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 18px; font-weight: 600; }
.header .badge { background: #da3633; color: white; padding: 2px 8px; border-radius: 4px;
                 font-size: 11px; font-weight: 600; }
.container { display: flex; height: calc(100vh - 57px); }
.sidebar { width: 320px; background: #161b22; border-right: 1px solid #30363d;
           padding: 16px; overflow-y: auto; }
.main { flex: 1; padding: 24px; overflow-y: auto; }
.search-bar { width: 100%; padding: 10px 14px; background: #0d1117; border: 1px solid #30363d;
              border-radius: 6px; color: #c9d1d9; font-size: 14px; margin-bottom: 16px; }
.search-bar:focus { outline: none; border-color: #58a6ff; }
.stats { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.stat { background: #21262d; padding: 12px 16px; border-radius: 6px; border: 1px solid #30363d; }
.stat .label { font-size: 11px; color: #8b949e; text-transform: uppercase; }
.stat .value { font-size: 20px; font-weight: 600; margin-top: 4px; }
.memory-list { display: flex; flex-direction: column; gap: 8px; }
.memory-card { background: #161b22; padding: 14px 16px; border-radius: 6px;
               border: 1px solid #30363d; cursor: pointer; transition: border-color 0.2s; }
.memory-card:hover { border-color: #58a6ff; }
.memory-card .text { font-size: 14px; line-height: 1.5; margin-bottom: 8px;
                     word-break: break-word; }
.memory-card .meta { display: flex; gap: 12px; font-size: 11px; color: #8b949e; }
.memory-card .score { background: #238636; color: white; padding: 2px 6px;
                      border-radius: 3px; font-weight: 600; }
.memory-card .score.low { background: #9e6a03; }
.memory-card .score.medium { background: #1f6feb; }
.empty { text-align: center; padding: 48px; color: #8b949e; }
.actions { display: flex; gap: 8px; margin-bottom: 16px; }
.btn { padding: 8px 16px; background: #238636; color: white; border: none;
       border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; }
.btn:hover { background: #2ea043; }
.btn.secondary { background: #21262d; border: 1px solid #30363d; }
.btn.secondary:hover { background: #30363d; }
.detail { background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; }
.detail h2 { font-size: 14px; margin-bottom: 12px; color: #58a6ff; }
.detail pre { background: #0d1117; padding: 14px; border-radius: 6px; font-size: 13px;
              overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
.detail .meta-row { display: flex; gap: 8px; margin-bottom: 8px; font-size: 12px; }
.detail .meta-key { color: #8b949e; min-width: 100px; }
.detail .meta-val { color: #c9d1d9; }
.loading { text-align: center; padding: 24px; color: #8b949e; }
.error { background: #da3633; color: white; padding: 12px 16px; border-radius: 6px;
         margin-bottom: 16px; font-size: 13px; }
</style>
</head>
<body>
<div class="header">
  <h1>Memex <span class="badge">AliceLabs</span></h1>
  <div id="server-status">Checking...</div>
</div>
<div class="container">
  <div class="sidebar">
    <input type="text" class="search-bar" id="search" placeholder="Search memories..."
           oninput="debounceSearch()">
    <div class="actions">
      <button class="btn" onclick="exportBackup()">Export</button>
      <button class="btn secondary" onclick="refresh()">Refresh</button>
    </div>
    <div id="memory-list" class="memory-list">
      <div class="loading">Loading memories...</div>
    </div>
  </div>
  <div class="main">
    <div class="stats" id="stats"></div>
    <div id="detail-view">
      <div class="empty">Select a memory to view details</div>
    </div>
  </div>
</div>
<script>
const API = window.location.origin;
let allMemories = [];
let searchTimer;

async function api(path, opts = {}) {
  try {
    const resp = await fetch(API + path, opts);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return await resp.json();
  } catch (e) {
    showError(e.message);
    return null;
  }
}

function showError(msg) {
  const el = document.getElementById('memory-list');
  el.innerHTML = '<div class="error">Error: ' + msg + '</div>';
}

async function loadHealth() {
  const h = await api('/proxy/health');
  if (!h) { document.getElementById('server-status').textContent = 'Offline'; return; }
  document.getElementById('server-status').textContent =
    h.status === 'ok' ? 'Online (' + h.count + ' memories)' : 'Degraded';
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="label">Memories</div><div class="value">${h.count}</div></div>
    <div class="stat"><div class="label">Queued</div><div class="value">${h.queued}</div></div>
    <div class="stat"><div class="label">Version</div><div class="value">${h.version}</div></div>
    <div class="stat"><div class="label">Snapshot</div><div class="value">${h.snapshot ? 'Yes' : 'No'}</div></div>
  `;
}

async function loadMemories() {
  const el = document.getElementById('memory-list');
  el.innerHTML = '<div class="loading">Loading...</div>';
  const data = await api('/proxy/query', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: ' ', limit: 100})
  });
  if (!data || !data.memories) { el.innerHTML = '<div class="empty">No memories</div>'; return; }
  allMemories = data.memories;
  renderList(allMemories);
}

function renderList(memories) {
  const el = document.getElementById('memory-list');
  if (!memories.length) { el.innerHTML = '<div class="empty">No memories found</div>'; return; }
  el.innerHTML = memories.map((m, i) => {
    const score = m.score || 0;
    const cls = score > 0.7 ? '' : score > 0.4 ? 'medium' : 'low';
    const text = (m.text || '').substring(0, 120);
    const truncated = m.text && m.text.length > 120 ? '...' : '';
    return `<div class="memory-card" onclick="showDetail(${i})">
      <div class="text">${escapeHtml(text)}${truncated}</div>
      <div class="meta">
        <span class="score ${cls}">${(score * 100).toFixed(0)}%</span>
        <span>${m.id ? m.id.substring(0, 8) : 'no-id'}</span>
      </div>
    </div>`;
  }).join('');
}

function showDetail(i) {
  const m = allMemories[i];
  if (!m) return;
  const detail = document.getElementById('detail-view');
  detail.innerHTML = `<div class="detail">
    <h2>Memory Details</h2>
    <div class="meta-row"><div class="meta-key">ID:</div><div class="meta-val">${m.id || 'N/A'}</div></div>
    <div class="meta-row"><div class="meta-key">Score:</div><div class="meta-val">${m.score || 'N/A'}</div></div>
    <div class="meta-row"><div class="meta-key">Method:</div><div class="meta-val">${m.method || 'N/A'}</div></div>
    <h2 style="margin-top:16px">Full Text</h2>
    <pre>${escapeHtml(m.text || '')}</pre>
  </div>`;
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function debounceSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    const q = document.getElementById('search').value.trim();
    if (!q) { renderList(allMemories); return; }
    const data = await api('/proxy/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: q, limit: 50})
    });
    if (data && data.memories) renderList(data.memories);
  }, 300);
}

async function exportBackup() {
  const data = await api('/proxy/export');
  if (!data) return;
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'memex-backup-' + Date.now() + '.json';
  a.click();
}

function refresh() { loadHealth(); loadMemories(); }

refresh();
</script>
</body>
</html>"""


def _server_url() -> str:
    port = os.environ.get("MEMEX_PORT") or os.environ.get("MEMEX_PORT", "19420")
    return f"http://127.0.0.1:{port}"


class UIHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves the UI and proxies API calls to memex-server."""

    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _proxy_get(self, path: str) -> None:
        """Proxy a GET request to the memex-server."""
        try:
            url = f"{_server_url()}{path}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.URLError as e:
            self._send_json({"error": f"memex-server unreachable: {e}"}, 503)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _proxy_post(self, path: str) -> None:
        """Proxy a POST request to the memex-server."""
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n) if n > 0 else b"{}"
            url = f"{_server_url()}{path}"
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.URLError as e:
            self._send_json({"error": f"memex-server unreachable: {e}"}, 503)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._send_html(_UI_HTML)
        elif self.path == "/proxy/health":
            self._proxy_get("/health")
        elif self.path == "/proxy/export":
            self._proxy_get("/export")
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/proxy/query":
            self._proxy_post("/query")
        elif self.path == "/proxy/recall":
            self._proxy_post("/recall")
        else:
            self._send_json({"error": "not found"}, 404)


def cmd_ui(args) -> int:
    """Start the local web UI."""
    port = args.port
    host = "127.0.0.1"

    # Check if memex-server is running
    try:
        req = urllib.request.Request(f"{_server_url()}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            health = json.loads(resp.read())
        print(f"[memex-ui] Connected to memex-server (v{health.get('version')}, {health.get('count')} memories)")
    except Exception:
        print(f"[memex-ui] Warning: memex-server not reachable at {_server_url()}", file=sys.stderr)
        print("[memex-ui] Start it first: `memex init` or `memex-server`", file=sys.stderr)
        return 1

    server = ThreadingHTTPServer((host, port), UIHandler)
    url = f"http://{host}:{port}"
    print(f"[memex-ui] Listening on {url}")
    print("[memex-ui] Press Ctrl+C to stop")

    if not args.no_browser:
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[memex-ui] Stopped.")
    finally:
        server.server_close()
    return 0


def register_parser(sub) -> None:
    """Register the `memex ui` subcommand."""
    p_ui = sub.add_parser(
        "ui",
        help="Start the local web UI for browsing memories (AliceLabs addition)",
    )
    p_ui.add_argument("--port", type=int, default=19421, help="Port for the UI (default: 19421)")
    p_ui.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    p_ui.set_defaults(func=cmd_ui)

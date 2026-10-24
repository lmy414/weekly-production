# SPDX-License-Identifier: GPL-3.0-only
"""Ephemeral loopback server exposing only bundled UI and selected character images."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urlsplit
import mimetypes

from .common import UI


@contextmanager
def render_server(bundle):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path.startswith("/preview-assets/") and path.endswith(".png"):
                role = Path(path).stem
                role = {"host": "watching", "news": "default"}.get(role, role)
                target = Path(bundle["assets"].get(role, bundle["assets"]["default"]))
            else:
                target = (UI / (path.lstrip("/") or "index.html")).resolve()
                if not target.is_relative_to(UI.resolve()):
                    self.send_error(404)
                    return
            if not target.is_file():
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(target.stat().st_size))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                with target.open("rb") as stream:
                    while data := stream.read(256 * 1024):
                        self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

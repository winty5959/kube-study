import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest


class Heartbeat:
    def __init__(self, timeout_s: int):
        self._timeout = timeout_s
        self._last = time.monotonic()

    def beat(self) -> None:
        self._last = time.monotonic()

    def healthy(self) -> bool:
        return time.monotonic() - self._last < self._timeout


def serve(port: int, heartbeat: Heartbeat) -> ThreadingHTTPServer:
    """Serve /healthz and /metrics on a background thread (PRD 4.2: worker port 8001)."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server API)
            if self.path == "/healthz":
                ok = heartbeat.healthy()
                self._reply(200 if ok else 503, b"ok\n" if ok else b"stalled\n", "text/plain")
            elif self.path == "/metrics":
                self._reply(200, generate_latest(REGISTRY), CONTENT_TYPE_LATEST)
            else:
                self._reply(404, b"not found\n", "text/plain")

        def _reply(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silence per-request access logs from probes
            pass

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

from __future__ import annotations

import json
import logging
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ha_basic_addon")

OPTIONS_PATH = Path("/data/options.json")

start_time = time.time()

def load_options() -> dict[str, object]:
    if not OPTIONS_PATH.exists():
        return {}
    try:
        return json.loads(OPTIONS_PATH.read_text())
    except json.JSONDecodeError:
        logger.warning("Unable to decode options.json, falling back to defaults")
        return {}

OPTIONS = load_options()

HOST = str(OPTIONS.get("host", "0.0.0.0"))
PORT = int(OPTIONS.get("port", 8080))
GREETING = str(OPTIONS.get("greeting", "Hello from HA Basic Add-on!"))

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, object], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/health"):
            payload = {
                "status": "ok",
                "uptime": round(time.time() - start_time, 2),
                "greeting": GREETING,
                "path": self.path,
                "timestamp": time.time(),
            }
            self._send_json(payload)
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

def run() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    logger.info("Starting HA Basic Add-on HTTP service on %s:%s", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run()

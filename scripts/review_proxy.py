"""Small review-only HTTP reverse proxy joining local Web and API ports."""
from __future__ import annotations

import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class ReviewProxy(BaseHTTPRequestHandler):
    web_port = 13000
    api_port = 18000
    blocked = ("/api/admin", "/api/docs", "/api/openapi.json")

    def _forward(self, target_port: int) -> None:
        path = self.path
        if path.startswith("/api") and any(path.startswith(prefix) for prefix in self.blocked):
            self.send_error(404, "Review endpoint unavailable")
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))) if self.command in {"POST", "PUT", "PATCH", "DELETE"} else None
        connection = http.client.HTTPConnection("127.0.0.1", target_port, timeout=30)
        headers = {key: value for key, value in self.headers.items() if key.lower() not in {"host", "connection", "content-length"}}
        headers["Host"] = f"127.0.0.1:{target_port}"
        try:
            connection.request(self.command, path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in {"connection", "transfer-encoding", "content-length", "server", "date"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except OSError:
            self.send_error(502, "Review target unavailable")
        finally:
            connection.close()

    def do_GET(self) -> None:
        self._forward(self.api_port if urlsplit(self.path).path.startswith("/api/") else self.web_port)

    def do_POST(self) -> None:
        self._forward(self.api_port)

    def do_PUT(self) -> None:
        self._forward(self.api_port)

    def do_PATCH(self) -> None:
        self._forward(self.api_port)

    def do_DELETE(self) -> None:
        self._forward(self.api_port)

    def do_OPTIONS(self) -> None:
        self._forward(self.api_port)

    def log_message(self, format: str, *args: object) -> None:
        print(f"review-proxy: {format % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--web-port", type=int, default=13000)
    parser.add_argument("--api-port", type=int, default=18000)
    args = parser.parse_args()
    ReviewProxy.web_port, ReviewProxy.api_port = args.web_port, args.api_port
    with ThreadingHTTPServer((args.host, args.port), ReviewProxy) as server:
        print(f"Review proxy: http://{args.host}:{args.port}", flush=True)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

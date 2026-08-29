"""Static development host for the Luminifera Web product on port 3000."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
WEB_STATIC = ROOT / "apps" / "web" / "static"


class WebHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        request_path = urlparse(path).path
        if request_path in {"", "/", "/index.html"}:
            return str(WEB_STATIC / "index.html")
        if request_path.startswith("/assets/"):
            candidate = WEB_STATIC / request_path.removeprefix("/assets/")
            try:
                candidate.resolve().relative_to(WEB_STATIC.resolve())
            except ValueError:
                return str(WEB_STATIC / "__missing__")
            return str(candidate)
        return str(WEB_STATIC / "__missing__")

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        if code == HTTPStatus.NOT_FOUND:
            message = "Web asset not found"
        super().send_error(code, message, explain)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Luminifera Web static assets.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), WebHandler) as server:
        print(f"Luminifera Web available at http://{args.host}:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

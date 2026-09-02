"""Standalone Web Alpha launcher: API and static Product UI in one process."""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
import json
from http.server import ThreadingHTTPServer
from pathlib import Path

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])).resolve()
os.environ["TEAM2050_PROJECT_ROOT"] = str(BASE)
if getattr(sys, "frozen", False):
    os.environ.setdefault("TEAM2050_RUNTIME_ROOT", str(Path(sys.executable).resolve().parent / "runtime"))
else:
    os.environ.setdefault("TEAM2050_RUNTIME_ROOT", str(BASE))

# PyInstaller's windowed bootloader exposes no standard streams. Uvicorn's
# logging configuration expects writable streams even when the UI is silent.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from services.api.app import app
import services.web_dev_server as web_server
from uvicorn import Config, Server


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    api_port, web_port = free_port(), free_port()
    api_server = Server(Config(app, host="127.0.0.1", port=api_port, log_level="warning"))
    api_thread = threading.Thread(target=api_server.run, name="luminifera-api", daemon=True)
    api_thread.start()
    health = f"http://127.0.0.1:{api_port}/api/health"
    for _ in range(60):
        try:
            with urllib.request.urlopen(health, timeout=1) as response:
                if response.status == 200:
                    break
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    else:
        api_server.should_exit = True
        raise RuntimeError("Luminifera API did not become ready")
    web_server.API_BASE = f"http://127.0.0.1:{api_port}"
    web = ThreadingHTTPServer(("127.0.0.1", web_port), web_server.WebHandler)
    web_thread = threading.Thread(target=web.serve_forever, name="luminifera-web", daemon=True)
    web_thread.start()
    url = f"http://127.0.0.1:{web_port}/app"
    # Do not open a browser until the static host can serve both the product
    # shell and the runtime API binding. This removes the first-load race on
    # fresh Windows machines.
    web_ready = False
    runtime_config = f"http://127.0.0.1:{web_port}/runtime-config.js"
    for _ in range(40):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                shell_ready = response.status == 200
            with urllib.request.urlopen(runtime_config, timeout=1) as response:
                config_ready = response.status == 200 and str(api_port).encode() in response.read()
            if shell_ready and config_ready:
                web_ready = True
                break
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    if not web_ready:
        web.shutdown()
        api_server.should_exit = True
        api_thread.join(timeout=5)
        raise RuntimeError("Luminifera Web did not become ready")
    report_path = os.environ.get("LUMINIFERA_LAUNCHER_REPORT")
    stop_path = os.environ.get("LUMINIFERA_LAUNCHER_STOP")
    if report_path:
        Path(report_path).write_text(json.dumps({"url": url, "api": health, "status": "ready"}), encoding="utf-8")
    print(f"Luminifera Alpha: {url}", flush=True)
    webbrowser.open(url)
    try:
        while api_thread.is_alive():
            if stop_path and Path(stop_path).exists():
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        web.shutdown()
        api_server.should_exit = True
        api_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Luminifera не удалось запустить. Проверьте журнал запуска.", "Luminifera", 0x10)
        except Exception:
            pass
        raise SystemExit(1) from exc

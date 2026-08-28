from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def kill_tree(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        process.kill()


def creation_flags() -> int:
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class LocalModelServer:
    def __init__(self, executable: str, model: str) -> None:
        self.executable = executable
        self.model = model
        self.port = free_port()
        self.process: subprocess.Popen[str] | None = None
        self.log = None

    def start(self, timeout: float) -> None:
        raw_log_path = os.environ.get("TEAM2050_LOCAL_WORKER_LOG", "").strip()
        log_path = Path(raw_log_path) if raw_log_path else None
        self.log = log_path.open("a", encoding="utf-8") if log_path else subprocess.DEVNULL
        self.process = subprocess.Popen(
            [self.executable, "-m", self.model, "--host", "127.0.0.1", "--port", str(self.port),
             "--ctx-size", "512", "--n-predict", "4", "--threads", "8", "--no-webui", "--reasoning", "off"],
            stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log, creationflags=creation_flags(),
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("llama-server exited during startup")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=1) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(0.25)
        raise TimeoutError("llama-server startup timeout")

    def request(self, prompt: str, timeout: float) -> str:
        body = json.dumps({
            "model": "team2050-local", "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8, "temperature": 0, "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload["choices"][0]["message"]["content"])

    def close(self) -> None:
        kill_tree(self.process)
        if self.log not in (None, subprocess.DEVNULL):
            self.log.close()
        self.process = None


def main() -> int:
    server: LocalModelServer | None = None
    try:
        for line in __import__("sys").stdin:
            request = json.loads(line)
            if server is None:
                server = LocalModelServer(str(request["executable"]), str(request["model"]))
                server.start(min(float(request.get("startup_timeout_seconds", 45)), 90.0))
            content = server.request(str(request["prompt"]), min(float(request.get("request_timeout_seconds", 20)), 45.0))
            print(json.dumps({"ok": True, "stdout": content, "stderr": "", "timed_out": False}, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"ok": False, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}", "timed_out": isinstance(exc, TimeoutError)}, ensure_ascii=False), flush=True)
        return 1
    finally:
        if server is not None:
            server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

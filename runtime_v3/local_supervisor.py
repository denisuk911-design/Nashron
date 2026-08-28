from __future__ import annotations

import os
import json
import queue
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalInferenceResult:
    ok: bool
    label: str = ""
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    external_provider_calls: int = 0


class LocalSupervisorRuntime:
    """Level-1 local classifier backed by an optional configured executable."""

    def __init__(self, command: str | None = None, model_path: str | None = None, timeout_seconds: float = 45.0, worker_command: list[str] | None = None) -> None:
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        bundled = root / "vendor" / "local_supervisor"
        self.command = command or os.environ.get("TEAM2050_LOCAL_SUPERVISOR_CMD", "").strip()
        self.executable = Path(self.command) if self.command else bundled / "llama.cpp" / "llama-server.exe"
        self.model_path = Path(model_path or os.environ.get("TEAM2050_LOCAL_SUPERVISOR_MODEL", "") or bundled / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf")
        self.timeout_seconds = timeout_seconds
        self.worker_command = worker_command or self._default_worker_command(root)
        self._worker = None
        self._worker_lock = threading.Lock()

    def decide(self, objective: str) -> str:
        result = self.infer(objective)
        if result.label == "SOCIAL":
            return "SIMPLE"
        if result.label == "WORK":
            return "COMPLEX"
        return result.label

    def infer(self, objective: str) -> LocalInferenceResult:
        if not self.executable.is_file() or not self.model_path.is_file():
            return LocalInferenceResult(False)
        with self._worker_lock:
            try:
                worker = self._ensure_worker()
                request = {"executable": str(self.executable), "model": str(self.model_path), "prompt": self._prompt(objective), "startup_timeout_seconds": self.timeout_seconds, "request_timeout_seconds": self.timeout_seconds}
                worker.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
                worker.stdin.flush()
                responses = queue.Queue()
                threading.Thread(target=lambda: responses.put(worker.stdout.readline()), daemon=True).start()
                raw = responses.get(timeout=self.timeout_seconds + 5)
            except queue.Empty:
                self._reset_worker()
                return LocalInferenceResult(False, timed_out=True)
            except (OSError, BrokenPipeError, AttributeError) as exc:
                self._reset_worker()
                return LocalInferenceResult(False, stderr=str(exc))
            if not raw:
                self._reset_worker()
                return LocalInferenceResult(False)
        try:
            payload = json.loads(raw.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            return LocalInferenceResult(False, stdout=raw)
        stdout = str(payload.get("stdout", ""))
        match = re.search(r"\b(SOCIAL|WORK)\b", stdout.upper())
        return LocalInferenceResult(bool(payload.get("ok")) and match is not None, match.group(1) if match else "", stdout, str(payload.get("stderr", "")))

    def _ensure_worker(self):
        if self._worker is not None and self._worker.poll() is None:
            return self._worker
        self._worker = subprocess.Popen(
            self.worker_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", creationflags=self._creation_flags(),
        )
        return self._worker

    def _reset_worker(self) -> None:
        self._kill_process_tree(self._worker)
        self._worker = None

    def close(self) -> None:
        with self._worker_lock:
            self._reset_worker()

    @staticmethod
    def _default_worker_command(root: Path) -> list[str]:
        if getattr(sys, "frozen", False):
            return [str(Path(sys.executable).with_name("Team2050LocalWorker.exe"))]
        return [sys.executable, "-m", "runtime_v3.local_supervisor_worker"]

    @staticmethod
    def _creation_flags() -> int:
        if os.name != "nt":
            return 0
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)

    @staticmethod
    def _prompt(objective: str) -> str:
        return f"You are a strict classifier. Reply with exactly one word: SOCIAL or WORK. Never explain. Text: {objective}"

    @staticmethod
    def _kill_process_tree(process) -> None:
        if process is None or process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            process.kill()

    def health(self) -> dict[str, object]:
        return {
            "runtime": "llama.cpp",
            "runtime_exists": self.executable.is_file(),
            "model": self.model_path.name,
            "model_exists": self.model_path.is_file(),
            "offline_ready": self.executable.is_file() and self.model_path.is_file(),
        }

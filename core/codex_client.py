from __future__ import annotations

import json
import logging
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

from .models import AuthStatus, CodexResult


class CodexClient:
    def __init__(
        self,
        executable: str = "codex",
        workspace: Path | None = None,
        timeout_seconds: int = 180,
        logger: logging.Logger | None = None,
    ) -> None:
        self.executable = executable
        self.workspace = workspace or Path(tempfile.gettempdir()) / "roman2050_codex_workspace"
        self.timeout_seconds = timeout_seconds
        self.logger = logger or logging.getLogger(__name__)
        self._process: subprocess.Popen[str] | None = None
        self._cancel_requested = False

    @staticmethod
    def _windows_hidden_process_kwargs() -> dict[str, object]:
        if os.name != "nt":
            return {}
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "startupinfo": startupinfo,
        }

    def resolved_executable(self) -> str | None:
        explicit = Path(self.executable)
        if explicit.name != self.executable and explicit.exists():
            return str(explicit)

        bundled = self._bundled_candidates()
        for candidate in bundled:
            if candidate.exists():
                return str(candidate)

        found = shutil.which(self.executable)
        if found:
            return found

        for candidate in self._vscode_extension_candidates():
            if candidate.exists():
                return str(candidate)
        return None

    def _bundled_candidates(self) -> list[Path]:
        bases = [Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])), Path.cwd()]
        return [base / "vendor" / "codex" / "win-x64" / "codex.exe" for base in bases]

    def _vscode_extension_candidates(self) -> list[Path]:
        home = Path.home()
        extension_root = home / ".vscode" / "extensions"
        if not extension_root.exists():
            return []
        candidates = list(extension_root.glob("openai.chatgpt-*/bin/windows-x86_64/codex.exe"))
        candidates.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
        return candidates

    def is_available(self) -> bool:
        return self.resolved_executable() is not None

    def version(self) -> str:
        executable = self.resolved_executable()
        if executable is None:
            return "неизвестно"
        completed = self._run([executable, "--version"], timeout=10)
        if completed.returncode != 0:
            return "неизвестно"
        return self._safe_text(completed.stdout).strip() or "неизвестно"

    def login_status(self) -> AuthStatus:
        if not self.is_available():
            return AuthStatus(False, False, "Codex CLI не найден", None)
        executable = self.resolved_executable()
        if executable is None:
            return AuthStatus(False, False, "Codex CLI не найден", None)
        completed = self._run([executable, "login", "status"], timeout=20)
        output = (self._safe_text(completed.stdout) + "\n" + self._safe_text(completed.stderr)).strip()
        if completed.returncode == 0:
            lowered = output.lower()
            authorized = any(token in lowered for token in ("logged in", "authenticated", "chatgpt", "authorized"))
            message = "Codex: авторизован" if authorized else output or "Статус Codex неизвестен"
            return AuthStatus(True, authorized, message, 0)
        return AuthStatus(True, False, output or "Codex: не авторизован", completed.returncode)

    def start_login(self) -> subprocess.Popen[str]:
        if not self.is_available():
            raise FileNotFoundError("Codex CLI не найден")
        executable = self.resolved_executable()
        if executable is None:
            raise FileNotFoundError("Codex CLI не найден")
        return subprocess.Popen([executable, "login"], text=True, **self._windows_hidden_process_kwargs())

    def logout(self) -> AuthStatus:
        if not self.is_available():
            return AuthStatus(False, False, "Codex CLI не найден", None)
        executable = self.resolved_executable()
        if executable is None:
            return AuthStatus(False, False, "Codex CLI не найден", None)
        completed = self._run([executable, "logout"], timeout=30)
        if completed.returncode == 0:
            return AuthStatus(True, False, "Codex: выполнен выход", 0)
        output = (self._safe_text(completed.stdout) + "\n" + self._safe_text(completed.stderr)).strip()
        return AuthStatus(True, False, output or "Не удалось выйти из Codex", completed.returncode)

    def generate(
        self,
        prompt: str,
        allow_full_access: bool = False,
        on_delta: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> CodexResult:
        if not self.is_available():
            return CodexResult(False, "", None, 0.0, "Codex CLI не найден")
        executable = self.resolved_executable()
        if executable is None:
            return CodexResult(False, "", None, 0.0, "Codex CLI не найден")
        self.workspace = self.workspace.expanduser().resolve(strict=False)
        self.workspace.mkdir(parents=True, exist_ok=True)
        if not self.workspace.is_dir():
            return CodexResult(False, "", None, 0.0, "Рабочая папка Codex недоступна")
        started = time.perf_counter()
        output_path = self.workspace / "last_roman_response.txt"
        if output_path.exists():
            output_path.unlink()

        sandbox = "danger-full-access" if allow_full_access else "read-only"
        command = [
            executable,
            "exec",
            "--cd",
            str(self.workspace),
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            sandbox,
            "--color",
            "never",
            "--output-last-message",
            str(output_path),
            "-",
        ]
        if on_delta is not None:
            command.insert(command.index("--color"), "--json")
        self._cancel_requested = False
        self.logger.info("codex_request_started sandbox=%s", sandbox)
        try:
            if on_delta is None:
                self._process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    **self._windows_hidden_process_kwargs(),
                )
                stdout, stderr = self._process.communicate(prompt, timeout=self.timeout_seconds)
                returncode = self._process.returncode
            else:
                stdout, stderr, returncode = self._communicate_streaming(command, prompt, started, on_delta, on_status)
        except subprocess.TimeoutExpired:
            self.cancel()
            duration = time.perf_counter() - started
            self.logger.error("codex_timeout duration=%.2f", duration)
            return CodexResult(False, "", None, duration, "Codex CLI не ответил вовремя")
        except FileNotFoundError:
            duration = time.perf_counter() - started
            return CodexResult(False, "", None, duration, "Codex CLI не найден")
        finally:
            self._process = None

        duration = time.perf_counter() - started
        if self._cancel_requested:
            self.logger.info("codex_request_cancelled duration=%.2f", duration)
            return CodexResult(False, "", returncode, duration, "Запрос отменен", cancelled=True)

        content = ""
        if output_path.exists():
            content = output_path.read_text(encoding="utf-8", errors="replace").strip()
        if not content:
            content = self._extract_plain_answer(stdout)
        if returncode != 0:
            detail = (self._safe_text(stderr) or self._safe_text(stdout)).strip()
            self.logger.error("codex_nonzero returncode=%s duration=%.2f", returncode, duration)
            return CodexResult(False, "", returncode, duration, detail or "Codex CLI завершился с ошибкой")
        if not content:
            return CodexResult(False, "", returncode, duration, "Codex CLI вернул пустой ответ")
        self.logger.info("codex_request_finished returncode=%s duration=%.2f", returncode, duration)
        return CodexResult(True, content, returncode, duration)

    def _communicate_streaming(
        self,
        command: list[str],
        prompt: str,
        started: float,
        on_delta: Callable[[str], None],
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[str, str, int | None]:
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **self._windows_hidden_process_kwargs(),
        )
        assert self._process.stdin is not None
        self._process.stdin.write(prompt)
        self._process.stdin.close()

        output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        emitted_parts: list[str] = []

        def reader(name: str, stream) -> None:
            try:
                for line in stream:
                    output_queue.put((name, line))
            finally:
                output_queue.put((f"{name}_done", None))

        threads = [
            threading.Thread(target=reader, args=("stdout", self._process.stdout), daemon=True),
            threading.Thread(target=reader, args=("stderr", self._process.stderr), daemon=True),
        ]
        for thread in threads:
            thread.start()

        stdout_done = False
        stderr_done = False
        last_status = ""
        while True:
            if time.perf_counter() - started > self.timeout_seconds:
                raise subprocess.TimeoutExpired(command[0], self.timeout_seconds)
            try:
                name, line = output_queue.get(timeout=0.1)
            except queue.Empty:
                if self._process.poll() is not None and stdout_done and stderr_done:
                    break
                continue
            if name == "stdout_done":
                stdout_done = True
                continue
            if name == "stderr_done":
                stderr_done = True
                continue
            if line is None:
                continue
            if name == "stdout":
                stdout_parts.append(line)
                delta = self._extract_stream_delta(line)
                if delta:
                    self._emit_unique_delta(emitted_parts, delta, on_delta)
                elif on_status is not None:
                    status = self._extract_stream_status(line)
                    if status and status != last_status:
                        last_status = status
                        on_status(status)
            else:
                stderr_parts.append(line)
            if self._process.poll() is not None and stdout_done and stderr_done:
                break

        returncode = self._process.wait(timeout=5)
        return "".join(stdout_parts), "".join(stderr_parts), returncode

    @classmethod
    def _extract_stream_status(cls, line: str) -> str:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return ""
        event_type = str(event.get("type") or event.get("event") or "").lower()
        item = event.get("item") if isinstance(event, dict) else None
        item_type = str(item.get("type") if isinstance(item, dict) else "").lower()
        command_text = cls._extract_command_text(event)
        combined_type = f"{event_type} {item_type}"
        if any(token in combined_type for token in ("apply_patch", "patch")):
            return "изменяю файлы"
        if any(token in combined_type for token in ("exec", "shell", "command", "tool_call", "function_call")):
            return cls._status_from_command(command_text) if command_text else "выполняю команду"
        if command_text:
            return cls._status_from_command(command_text)
        return ""

    @classmethod
    def _extract_command_text(cls, value) -> str:
        if isinstance(value, dict):
            for key in ("command", "cmd", "args"):
                item = value.get(key)
                if isinstance(item, str):
                    return item
                if isinstance(item, list):
                    return " ".join(str(part) for part in item)
            for item in value.values():
                found = cls._extract_command_text(item)
                if found:
                    return found
        if isinstance(value, list):
            for item in value:
                found = cls._extract_command_text(item)
                if found:
                    return found
        return ""

    @staticmethod
    def _status_from_command(command: str) -> str:
        lowered = command.lower()
        if any(token in lowered for token in ("mkdir", "new-item", "созд")):
            return "создаю папки"
        if any(token in lowered for token in ("apply_patch", "patch", "set-content", "out-file", "write_text")):
            return "изменяю файлы"
        if any(token in lowered for token in ("pytest", "test", "quick_validate")):
            return "проверяю результат"
        if any(token in lowered for token in ("rg ", "grep", "findstr", "select-string")):
            return "ищу по проекту"
        if any(token in lowered for token in ("get-content", "type ", " cat ", " gc ", "read_text")):
            return "читаю файлы"
        if any(token in lowered for token in ("curl", "wget", "download")):
            return "скачиваю"
        if any(token in lowered for token in ("copy", "move", "remove", "del ", "rm ")):
            return "обрабатываю файлы"
        return "выполняю команду"

    @staticmethod
    def _emit_unique_delta(parts: list[str], text: str, on_delta: Callable[[str], None]) -> None:
        current = "".join(parts)
        if not text:
            return
        if text.startswith(current):
            delta = text[len(current) :]
        elif current.endswith(text):
            return
        else:
            delta = text
        if delta:
            parts.append(delta)
            on_delta(delta)

    @classmethod
    def _extract_stream_delta(cls, line: str) -> str:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return ""
        event_type = str(event.get("type") or event.get("event") or "").lower()
        item = event.get("item")
        if event_type == "item.completed" and isinstance(item, dict):
            if str(item.get("type") or "").lower() == "agent_message":
                text = item.get("text")
                return text if isinstance(text, str) else ""
        if event_type and not any(token in event_type for token in ("assistant", "agent_message", "message")):
            return ""
        if "user" in event_type or "reasoning" in event_type:
            return ""
        for key in ("delta", "text"):
            value = event.get(key)
            if isinstance(value, str):
                return value
        value = event.get("content")
        if isinstance(value, str):
            return value
        return cls._extract_nested_text(event)

    @classmethod
    def _extract_nested_text(cls, value) -> str:
        if isinstance(value, dict):
            for key in ("delta", "text", "content"):
                item = value.get(key)
                if isinstance(item, str):
                    return item
            for item in value.values():
                found = cls._extract_nested_text(item)
                if found:
                    return found
        if isinstance(value, list):
            for item in value:
                found = cls._extract_nested_text(item)
                if found:
                    return found
        return ""

    def cancel(self) -> None:
        process = self._process
        self._cancel_requested = True
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            self.logger.info("codex_request_cancel_requested")

    def _run(self, command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                **self._windows_hidden_process_kwargs(),
            )
        except FileNotFoundError:
            return subprocess.CompletedProcess(command, 127, "", "Codex CLI не найден")
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(command, 124, exc.stdout or "", exc.stderr or "timeout")

    @staticmethod
    def _safe_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    @staticmethod
    def _extract_plain_answer(stdout: str | None) -> str:
        text = (stdout or "").strip()
        if not text:
            return ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        filtered = [
            line
            for line in lines
            if not line.startswith(("codex", "INFO", "DEBUG"))
            and "tokens used" not in line.lower()
            and "workdir" not in line.lower()
        ]
        return "\n".join(filtered).strip()

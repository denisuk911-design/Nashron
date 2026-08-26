from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .models import CodexResult
from .provider_execution import isolated_provider_environment


class GeminiClient:
    def __init__(
        self,
        executable: str = "gemini",
        workspace: Path | None = None,
        timeout_seconds: int = 180,
        api_key: str | None = None,
        model: str = "gemini-3.1-flash-lite",
        logger: logging.Logger | None = None,
    ) -> None:
        self.executable = executable
        self.workspace = workspace or Path(tempfile.gettempdir()) / "roman2050_gemini_workspace"
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.model = model
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
        return shutil.which(self.executable)

    def is_available(self) -> bool:
        return self.resolved_executable() is not None

    def has_api_key(self) -> bool:
        return bool(self._resolved_api_key())

    def version(self) -> str:
        executable = self.resolved_executable()
        if executable is None:
            return "неизвестно"
        completed = self._run([executable, "--version"], timeout=10)
        if completed.returncode != 0:
            return "неизвестно"
        return self._safe_text(completed.stdout).strip() or "неизвестно"

    def generate(
        self,
        prompt: str,
        allow_full_access: bool = False,
        on_delta=None,
        on_status=None,
    ) -> CodexResult:
        if self._cancel_requested:
            return CodexResult(False, "", None, 0.0, "Запрос Gemini отменен", cancelled=True)
        if not self.is_available():
            return CodexResult(False, "", None, 0.0, "Gemini CLI не найден")
        if not self.has_api_key():
            return CodexResult(False, "", None, 0.0, "GEMINI_API_KEY не задан")
        executable = self.resolved_executable()
        if executable is None:
            return CodexResult(False, "", None, 0.0, "Gemini CLI не найден")
        self.workspace = self.workspace.expanduser().resolve(strict=False)
        self.workspace.mkdir(parents=True, exist_ok=True)
        if not self.workspace.is_dir():
            return CodexResult(False, "", None, 0.0, "Рабочая папка Gemini недоступна")

        started = time.perf_counter()
        command = [executable, "--skip-trust", "-m", self.model, "-p", "", "--output-format", "json"]
        if allow_full_access:
            command.extend(["--approval-mode", "yolo"])
        api_key = self._resolved_api_key()
        env = isolated_provider_environment({"GEMINI_API_KEY": api_key} if api_key else {})

        self.logger.info("gemini_request_started tools=%s", bool(allow_full_access))
        try:
            self._process = subprocess.Popen(
                command,
                cwd=str(self.workspace),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                **self._windows_hidden_process_kwargs(),
            )
            stdout_bytes, stderr_bytes = self._process.communicate(
                input=prompt.encode("utf-8"),
                timeout=self.timeout_seconds,
            )
            stdout = self._decode_output(stdout_bytes)
            stderr = self._decode_output(stderr_bytes)
            returncode = self._process.returncode
        except subprocess.TimeoutExpired:
            self.cancel()
            duration = time.perf_counter() - started
            self.logger.error("gemini_timeout duration=%.2f", duration)
            return CodexResult(False, "", None, duration, "Gemini CLI не ответил вовремя", timed_out=True)
        except FileNotFoundError:
            duration = time.perf_counter() - started
            return CodexResult(False, "", None, duration, "Gemini CLI не найден")
        finally:
            self._process = None

        duration = time.perf_counter() - started
        if self._cancel_requested:
            self.logger.info("gemini_request_cancelled duration=%.2f", duration)
            return CodexResult(False, "", returncode, duration, "Запрос Gemini отменен", cancelled=True)

        content = self._extract_answer(stdout)
        if on_delta is not None and content:
            on_delta(content)
        if returncode != 0:
            detail = self._extract_error(stdout) or self._clean_error(stderr) or self._clean_error(stdout)
            self.logger.error("gemini_nonzero returncode=%s duration=%.2f", returncode, duration)
            return CodexResult(False, "", returncode, duration, detail or "Gemini CLI завершился с ошибкой")
        if not content:
            return CodexResult(False, "", returncode, duration, "Gemini CLI вернул пустой ответ")
        self.logger.info("gemini_request_finished returncode=%s duration=%.2f", returncode, duration)
        return CodexResult(True, content, returncode, duration)

    def cancel(self) -> None:
        process = self._process
        self._cancel_requested = True
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            self.logger.info("gemini_request_cancel_requested")

    def _run(self, command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        api_key = self._resolved_api_key()
        env = isolated_provider_environment({"GEMINI_API_KEY": api_key} if api_key else {})
        try:
            return subprocess.run(
                command,
                capture_output=True,
                timeout=timeout,
                check=False,
                env=env,
                **self._windows_hidden_process_kwargs(),
            )
        except FileNotFoundError:
            return subprocess.CompletedProcess(command, 127, "", "Gemini CLI не найден")
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(command, 124, exc.stdout or "", exc.stderr or "timeout")

    @staticmethod
    def _safe_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return GeminiClient._decode_output(value)
        return value

    @staticmethod
    def _decode_output(value: str | bytes | None) -> str:
        if not value:
            return ""
        if isinstance(value, str):
            return value
        for encoding in ("utf-8-sig", "utf-8", "cp866", "cp1251", "utf-16"):
            try:
                return value.decode(encoding)
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace")

    def _resolved_api_key(self) -> str:
        return (self.api_key or os.environ.get("GEMINI_API_KEY") or self._windows_user_api_key()).strip()

    @staticmethod
    def _windows_user_api_key() -> str:
        if os.name != "nt":
            return ""
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _ = winreg.QueryValueEx(key, "GEMINI_API_KEY")
            return str(value)
        except OSError:
            return ""

    @classmethod
    def _extract_answer(cls, stdout: str | None) -> str:
        text = cls._safe_text(stdout).strip()
        if not text:
            return ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return text
        found = cls._extract_nested_text(payload)
        return found.strip() if found else text

    @classmethod
    def _extract_error(cls, stdout: str | None) -> str:
        text = cls._safe_text(stdout).strip()
        if not text:
            return ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return ""
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return cls._friendly_error(message)
        return ""

    @classmethod
    def _clean_error(cls, value: str | bytes | None) -> str:
        text = cls._safe_text(value).strip()
        if not text:
            return ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        useful = [
            line
            for line in lines
            if not line.lower().startswith("warning:")
            and "full report available" not in line.lower()
            and "at file://" not in line.lower()
        ]
        return cls._friendly_error("\n".join(useful[-4:] if useful else lines[-4:]))

    @staticmethod
    def _friendly_error(message: str) -> str:
        lowered = message.lower()
        if "quota" in lowered or "exhausted" in lowered or "429" in lowered:
            return "Сотрудник не смог ответить: квота Gemini на выбранной модели исчерпана. Попробуйте позже или смените ИИ-движок."
        if "api key" in lowered or "gemini_api_key" in lowered:
            return "Сотрудник не смог ответить: Gemini не авторизован. Проверьте подключение ИИ-движка."
        if "model" in lowered and "not" in lowered:
            return f"Сотрудник не смог ответить: модель Gemini недоступна. Деталь: {message}"
        return message

    @classmethod
    def _extract_nested_text(cls, value) -> str:
        if isinstance(value, dict):
            for key in ("response", "text", "content", "output", "message"):
                item = value.get(key)
                if isinstance(item, str):
                    return item
            for item in value.values():
                found = cls._extract_nested_text(item)
                if found:
                    return found
        if isinstance(value, list):
            return "\n".join(part for part in (cls._extract_nested_text(item) for item in value) if part)
        return ""

import subprocess

from core.codex_client import CodexClient


def test_missing_codex_cli(monkeypatch, tmp_path):
    monkeypatch.setattr("core.codex_client.shutil.which", lambda _name: None)
    monkeypatch.setattr(CodexClient, "_bundled_candidates", lambda _self: [])
    monkeypatch.setattr(CodexClient, "_vscode_extension_candidates", lambda _self: [])
    client = CodexClient(workspace=tmp_path)
    result = client.generate("hello")
    assert not result.ok
    assert result.error == "Codex CLI не найден"


class FakeProcess:
    def __init__(self, returncode=0, stdout="Ответ Романа", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.terminated = False
        self.killed = False

    def communicate(self, _stdin, timeout=None):
        return self.stdout, self.stderr

    def poll(self):
        return None if not self.terminated else self.returncode

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.killed = True
        self.terminated = True


def test_nonzero_return_code(monkeypatch, tmp_path):
    monkeypatch.setattr("core.codex_client.shutil.which", lambda _name: "codex")
    monkeypatch.setattr(
        "core.codex_client.subprocess.Popen",
        lambda *args, **kwargs: FakeProcess(returncode=2, stdout="", stderr="bad"),
    )
    client = CodexClient(workspace=tmp_path)
    result = client.generate("prompt")
    assert not result.ok
    assert result.returncode == 2
    assert "bad" in result.error


def test_timeout(monkeypatch, tmp_path):
    class TimeoutProcess(FakeProcess):
        def communicate(self, _stdin, timeout=None):
            raise subprocess.TimeoutExpired("codex", timeout)

    monkeypatch.setattr("core.codex_client.shutil.which", lambda _name: "codex")
    monkeypatch.setattr("core.codex_client.subprocess.Popen", lambda *args, **kwargs: TimeoutProcess())
    client = CodexClient(workspace=tmp_path, timeout_seconds=1)
    result = client.generate("prompt")
    assert not result.ok
    assert "не ответил вовремя" in result.error


def test_cancel_process(tmp_path):
    client = CodexClient(workspace=tmp_path)
    process = FakeProcess()
    client._process = process
    client.cancel()
    assert process.terminated


def test_full_access_flag_changes_sandbox(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr("core.codex_client.shutil.which", lambda _name: "codex")

    def fake_popen(command, *args, **kwargs):
        captured["command"] = command
        return FakeProcess()

    monkeypatch.setattr("core.codex_client.subprocess.Popen", fake_popen)
    result = CodexClient(workspace=tmp_path).generate("prompt", allow_full_access=True)
    assert result.ok
    sandbox_index = captured["command"].index("--sandbox") + 1
    assert captured["command"][sandbox_index] == "danger-full-access"


def test_resolves_bundled_codex_before_path(monkeypatch, tmp_path):
    bundled = tmp_path / "vendor" / "codex" / "win-x64" / "codex.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_text("fake", encoding="utf-8")
    monkeypatch.setattr("core.codex_client.shutil.which", lambda _name: "path-codex")
    monkeypatch.setattr(CodexClient, "_bundled_candidates", lambda _self: [bundled])
    client = CodexClient(workspace=tmp_path)
    assert client.resolved_executable() == str(bundled)


def test_resolves_vscode_codex_when_path_missing(monkeypatch, tmp_path):
    vscode = tmp_path / "extensions" / "openai.chatgpt-test" / "bin" / "windows-x86_64" / "codex.exe"
    vscode.parent.mkdir(parents=True)
    vscode.write_text("fake", encoding="utf-8")
    monkeypatch.setattr("core.codex_client.shutil.which", lambda _name: None)
    monkeypatch.setattr(CodexClient, "_bundled_candidates", lambda _self: [])
    monkeypatch.setattr(CodexClient, "_vscode_extension_candidates", lambda _self: [vscode])
    client = CodexClient(workspace=tmp_path)
    assert client.resolved_executable() == str(vscode)


def test_extract_stream_delta_from_json_event():
    line = '{"type":"agent_message_delta","delta":"Привет"}'
    assert CodexClient._extract_stream_delta(line) == "Привет"


def test_extract_stream_delta_from_codex_item_completed_event():
    line = '{"type":"item.completed","item":{"type":"agent_message","text":"Финальный ответ"}}'
    assert CodexClient._extract_stream_delta(line) == "Финальный ответ"


def test_extract_stream_delta_ignores_reasoning_event():
    line = '{"type":"reasoning_delta","delta":"hidden"}'
    assert CodexClient._extract_stream_delta(line) == ""


def test_emit_unique_delta_handles_full_message_update():
    chunks = []
    emitted = []
    CodexClient._emit_unique_delta(chunks, "Прив", emitted.append)
    CodexClient._emit_unique_delta(chunks, "Привет", emitted.append)
    assert emitted == ["Прив", "ет"]


def test_extract_stream_status_from_exec_event():
    line = '{"type":"exec_command.begin","cmd":"mkdir skills"}'
    assert CodexClient._extract_stream_status(line) == "создаю папки"


def test_extract_stream_status_from_patch_event():
    line = '{"type":"apply_patch.begin","item":{"text":"update file"}}'
    assert CodexClient._extract_stream_status(line) == "изменяю файлы"

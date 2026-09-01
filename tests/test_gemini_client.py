from core.gemini_client import GeminiClient


def test_missing_gemini_cli(monkeypatch, tmp_path):
    monkeypatch.setattr("core.gemini_client.shutil.which", lambda _name: None)
    client = GeminiClient(workspace=tmp_path, api_key="key")
    result = client.generate("hello")
    assert not result.ok
    assert result.error == "Gemini CLI не найден"


def test_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setattr("core.gemini_client.shutil.which", lambda _name: "gemini")
    monkeypatch.setattr(GeminiClient, "_windows_user_api_key", staticmethod(lambda: ""))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = GeminiClient(workspace=tmp_path)
    result = client.generate("hello")
    assert not result.ok
    assert result.error == "GEMINI_API_KEY не задан"


def test_secure_provider_credential_is_used_when_environment_is_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(GeminiClient, "_windows_user_api_key", staticmethod(lambda: ""))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    client = GeminiClient(workspace=tmp_path, credential_lookup=lambda: "credential-from-store")

    assert client.has_api_key()
    assert client._resolved_api_key() == "credential-from-store"


class FakeProcess:
    def __init__(self, returncode=0, stdout='{"response":"Ответ Петра"}', stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.terminated = False
        self.killed = False
        self.input = None

    def communicate(self, input=None, timeout=None):
        self.input = input
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


def test_cancel_before_generate_does_not_start_gemini(monkeypatch, tmp_path):
    monkeypatch.setattr("core.gemini_client.shutil.which", lambda _name: "gemini")
    monkeypatch.setattr(
        "core.gemini_client.subprocess.Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Gemini process must not start")),
    )
    client = GeminiClient(workspace=tmp_path, api_key="secret")

    client.cancel()
    result = client.generate("prompt")

    assert result.cancelled


def test_generate_uses_gemini_prompt_and_env(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr("core.gemini_client.shutil.which", lambda _name: "gemini")

    def fake_popen(command, *args, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs["env"]
        captured["process"] = FakeProcess()
        return captured["process"]

    monkeypatch.setattr("core.gemini_client.subprocess.Popen", fake_popen)
    result = GeminiClient(workspace=tmp_path, api_key="secret").generate("prompt")
    assert result.ok
    assert result.content == "Ответ Петра"
    assert captured["command"][:5] == ["gemini", "--skip-trust", "-m", "gemini-3.5-flash-lite", "-p"]
    assert captured["command"][5] == ""
    assert captured["process"].input == b"prompt"
    assert captured["env"]["GEMINI_API_KEY"] == "secret"


def test_generate_enables_gemini_actions_when_local_tools_allowed(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr("core.gemini_client.shutil.which", lambda _name: "gemini")

    def fake_popen(command, *args, **kwargs):
        captured["command"] = command
        return FakeProcess()

    monkeypatch.setattr("core.gemini_client.subprocess.Popen", fake_popen)
    result = GeminiClient(workspace=tmp_path, api_key="secret").generate("prompt", allow_full_access=True)

    assert result.ok
    assert "--approval-mode" in captured["command"]
    assert "yolo" in captured["command"]


def test_extract_answer_from_plain_text():
    assert GeminiClient._extract_answer("Простой ответ") == "Простой ответ"


def test_extracts_friendly_quota_error():
    message = '{"error":{"message":"You have exhausted your daily quota on this model."}}'
    assert "квота Gemini" in GeminiClient._extract_error(message)


def test_decodes_windows_oem_output():
    assert GeminiClient._decode_output("Привет".encode("cp866")) == "Привет"

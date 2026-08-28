from runtime_v3.local_supervisor import LocalSupervisorRuntime
import sys


def test_local_supervisor_uses_configured_command(tmp_path):
    runtime = LocalSupervisorRuntime(model_path=str(tmp_path / "missing.gguf"))
    assert runtime.decide("simple") == ""


def test_local_supervisor_timeout_falls_back_without_raising():
    runtime = LocalSupervisorRuntime("definitely-not-installed-team2050-local", timeout_seconds=0.01)
    assert runtime.decide("complex goal") == ""


def test_local_supervisor_health_is_offline_and_explicit(tmp_path):
    health = LocalSupervisorRuntime(model_path=str(tmp_path / "missing.gguf")).health()
    assert health["runtime"] == "llama.cpp"
    assert health["offline_ready"] is False


def test_local_supervisor_inference_is_bounded_when_runtime_is_missing(tmp_path):
    result = LocalSupervisorRuntime(model_path=str(tmp_path / "missing.gguf"), timeout_seconds=0.01).infer("hello")
    assert result.ok is False
    assert result.external_provider_calls == 0


def test_local_supervisor_uses_isolated_worker_ipc(tmp_path):
    executable = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    executable.write_text("worker placeholder")
    model.write_text("model placeholder")
    code = "import json,sys; json.loads(sys.stdin.readline()); print(json.dumps({'ok': True, 'stdout': 'SOCIAL', 'stderr': '', 'timed_out': False}))"
    runtime = LocalSupervisorRuntime(
        str(executable), str(model), timeout_seconds=1,
        worker_command=[sys.executable, "-c", code],
    )
    result = runtime.infer("hello")
    assert result.ok is True
    assert result.label == "SOCIAL"
    assert result.external_provider_calls == 0


def test_local_supervisor_worker_crash_is_a_fallback(tmp_path):
    executable = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    executable.write_text("worker placeholder")
    model.write_text("model placeholder")
    runtime = LocalSupervisorRuntime(
        str(executable), str(model), timeout_seconds=1,
        worker_command=[sys.executable, "-c", "raise SystemExit(7)"],
    )
    result = runtime.infer("hello")
    assert result.ok is False
    assert result.external_provider_calls == 0


def test_local_supervisor_reuses_persistent_worker(tmp_path):
    executable = tmp_path / "llama-cli.exe"
    model = tmp_path / "model.gguf"
    executable.write_text("worker placeholder")
    model.write_text("model placeholder")
    code = "import json,sys; [print(json.dumps({'ok': True, 'stdout': 'WORK', 'stderr': '', 'timed_out': False}), flush=True) for _ in sys.stdin]"
    runtime = LocalSupervisorRuntime(
        str(executable), str(model), timeout_seconds=1,
        worker_command=[sys.executable, "-c", code],
    )
    assert runtime.infer("one").label == "WORK"
    first_worker = runtime._worker
    assert runtime.infer("two").label == "WORK"
    assert runtime._worker is first_worker
    runtime.close()


def test_local_supervisor_malformed_worker_response_is_a_fallback(tmp_path):
    executable = tmp_path / "llama-server.exe"
    model = tmp_path / "model.gguf"
    executable.write_text("worker placeholder")
    model.write_text("model placeholder")
    runtime = LocalSupervisorRuntime(
        str(executable), str(model), timeout_seconds=1,
        worker_command=[sys.executable, "-c", "print('not-json', flush=True)"],
    )
    result = runtime.infer("hello")
    assert result.ok is False
    assert result.external_provider_calls == 0

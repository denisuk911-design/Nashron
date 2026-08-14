import json
import subprocess
import sys

from runtime_v2.provider_adapter import LocalTextFileProviderAdapter
from runtime_v2.vertical_slice import RuntimeV2Service, SQLiteRuntimeV2Repository, parse_create_text_file


def test_parse_real_russian_bounded_create_file_prompt():
    request = parse_create_text_file("создай файл runtime_v2_real.txt точно RUNTIME_V2_REAL_OK")

    assert request is not None
    assert request.filename == "runtime_v2_real.txt"
    assert request.content == "RUNTIME_V2_REAL_OK"


def test_runtime_v2_creates_verifies_and_persists_text_file(tmp_path):
    repository = SQLiteRuntimeV2Repository(tmp_path / "runtime.sqlite3")
    service = RuntimeV2Service(repository, tmp_path)
    adapter = LocalTextFileProviderAdapter()
    request = parse_create_text_file("создай файл runtime_v2_real.txt точно RUNTIME_V2_REAL_OK")
    state = service.create_task(request, "agent-roman", "org-test", adapter.provider_id)

    result = service.execute(state.runtime_task_id, request, adapter)

    assert result.ok
    assert result.content_exact
    assert result.status == "COMPLETE"
    assert result.logical_uri.startswith("artifact://org-test/")
    assert (tmp_path / ".runtime_v2" / "org-test" / state.runtime_task_id / "runtime_v2_real.txt").read_text(encoding="utf-8") == "RUNTIME_V2_REAL_OK"
    with repository.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM runtime_v2_tasks").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM runtime_v2_artifacts").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM runtime_v2_evidence WHERE passed = 1").fetchone()[0] == 1


def test_runtime_v2_repeated_execute_is_idempotent(tmp_path):
    repository = SQLiteRuntimeV2Repository(tmp_path / "runtime.sqlite3")
    service = RuntimeV2Service(repository, tmp_path)
    adapter = LocalTextFileProviderAdapter()
    request = parse_create_text_file("create file runtime_v2_real.txt exactly RUNTIME_V2_REAL_OK")
    state = service.create_task(request, "agent-roman", "org-test", adapter.provider_id)

    first = service.execute(state.runtime_task_id, request, adapter)
    second = service.execute(state.runtime_task_id, request, adapter)

    assert first.ok and second.ok
    assert first.artifact_id == second.artifact_id
    with repository.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM runtime_v2_artifacts").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM runtime_v2_effects WHERE status = 'STATE_COMMITTED'").fetchone()[0] == 1


def test_runtime_v2_recovers_after_effect_commit_crash(tmp_path):
    repository = SQLiteRuntimeV2Repository(tmp_path / "runtime.sqlite3")
    service = RuntimeV2Service(repository, tmp_path)
    adapter = LocalTextFileProviderAdapter()
    request = parse_create_text_file("создай файл runtime_v2_real.txt точно RUNTIME_V2_REAL_OK")
    state = service.create_task(request, "agent-roman", "org-test", adapter.provider_id)

    try:
        service.execute(state.runtime_task_id, request, adapter, crash_after_effect=True)
    except RuntimeError as exc:
        assert str(exc) == "SIMULATED_CRASH_AFTER_EFFECT"
    recovered = service.recover(state.runtime_task_id, request)

    assert recovered.ok
    assert recovered.status == "COMPLETE"
    assert recovered.content_exact


def test_runtime_v2_smoke_script_is_runnable(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/runtime_v2_smoke.py",
            "--workspace",
            str(tmp_path / "workspace"),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr + completed.stdout
    output = json.loads(completed.stdout)
    assert output["ok"] is True
    assert output["content_exact"] is True
    assert output["status"] == "COMPLETE"

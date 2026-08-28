from runtime_v3.local_supervisor import LocalSupervisorRuntime


def test_local_supervisor_uses_configured_command(tmp_path):
    script = tmp_path / "classifier.cmd"
    script.write_text("@echo simple\n", encoding="utf-8")
    assert LocalSupervisorRuntime(str(script)).decide("simple") == "SIMPLE"


def test_local_supervisor_timeout_falls_back_without_raising():
    runtime = LocalSupervisorRuntime("definitely-not-installed-team2050-local", timeout_seconds=0.01)
    assert runtime.decide("complex goal") == ""

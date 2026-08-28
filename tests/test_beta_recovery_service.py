from __future__ import annotations

import json
import zipfile

from core.beta_recovery_service import BetaRecoveryService, SimulatedUpdateCrash


def _bundle(path, version: str):
    path.mkdir()
    (path / "Team2050.exe").write_bytes(version.encode())
    (path / "team2050-release.json").write_text(json.dumps({"version": version}), encoding="utf-8")


def test_recovery_rolls_back_interrupted_update_and_support_bundle_excludes_secrets(tmp_path):
    source = tmp_path / "source"
    install = tmp_path / "install"
    _bundle(source, "new")
    _bundle(install, "old")
    service = BetaRecoveryService(install)

    try:
        service.update(source, "new", simulate_crash=True)
    except SimulatedUpdateCrash:
        pass

    assert service.recover() is True
    assert json.loads((install / "team2050-release.json").read_text(encoding="utf-8"))["version"] == "old"
    bundle = service.create_support_bundle(tmp_path / "profile", tmp_path / "support.zip")
    with zipfile.ZipFile(bundle) as archive:
        report = json.loads(archive.read("support-report.json").decode("utf-8"))
    assert report["secrets_included"] is False
    assert "api keys" in report["excluded"]

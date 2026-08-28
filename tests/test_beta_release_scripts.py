from __future__ import annotations

import json
import subprocess
import sys


def test_prepare_beta_release_writes_versioned_external_profile_manifest(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "Team2050.exe").write_bytes(b"placeholder")
    target = tmp_path / "beta"

    result = subprocess.run(
        [sys.executable, "scripts/prepare_beta_release.py", "--source", str(source), "--target", str(target), "--version", "9.1.0-beta.1"],
        check=False,
    )

    assert result.returncode == 0
    manifest = json.loads((target / "team2050-release.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "9.1.0-beta.1"
    assert manifest["profile_policy"] == "external_localappdata"
    assert manifest["legacy_profile_policy"] == "never_import_Roman2050"

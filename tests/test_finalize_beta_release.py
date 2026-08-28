from __future__ import annotations

import json

from scripts.finalize_beta_release import build, verify


def test_final_beta_package_has_manifest_checksums_and_changelog(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "Team2050.exe").write_bytes(b"binary")
    target, archive = build(source, tmp_path / "target", "1.2.3-beta.4")

    assert verify(target)
    assert archive.is_file()
    manifest = json.loads((target / "team2050-release.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.3-beta.4"
    assert "Team2050.exe" in manifest["files"]
    assert (target / "CHANGELOG.md").is_file()
    assert (target / "INSTALL.txt").is_file()

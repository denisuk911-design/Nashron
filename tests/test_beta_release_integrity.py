import json

from core.beta_release_integrity import sign_manifest, verify_release_dir


def test_tampered_release_is_rejected(tmp_path):
    exe = tmp_path / "Team2050.exe"
    exe.write_bytes(b"release")
    manifest = {"product": "Team2050", "files": {"Team2050.exe": ""}}
    import hashlib
    manifest["files"]["Team2050.exe"] = hashlib.sha256(exe.read_bytes()).hexdigest()
    manifest["signature"] = sign_manifest(manifest)
    path = tmp_path / "team2050-release.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_release_dir(tmp_path)
    exe.write_bytes(b"tampered")
    assert not verify_release_dir(tmp_path)
